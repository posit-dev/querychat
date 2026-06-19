"""QueryExecutor abstraction for cross-table query execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import duckdb
import narwhals.stable.v1 as nw

from ._datasource import (
    ColumnMeta,
    MissingColumnsError,
    duckdb_column_meta,
    duckdb_column_stats,
    format_schema,
    duckdb_lock_down,
)
from ._utils import check_query

if TYPE_CHECKING:
    from ._datasource import DataFrameSource, DataSource, PolarsLazySource


class QueryExecutor(ABC):
    """Thin abstraction that tools use for query execution and validation."""

    @abstractmethod
    def execute_query(self, query: str) -> Any: ...

    @abstractmethod
    def test_query(
        self, query: str, *, table_name: str, require_all_columns: bool = False
    ) -> None: ...

    @abstractmethod
    def get_db_type(self) -> str: ...

    @abstractmethod
    def cleanup(self) -> None: ...

    @abstractmethod
    def get_column_metas(self, table_name: str) -> list[ColumnMeta]: ...

    @abstractmethod
    def populate_column_stats(
        self, table_name: str, columns: list[ColumnMeta], categorical_threshold: int
    ) -> None: ...

    def get_schema(self, table_name: str, categorical_threshold: int) -> str:
        metas = self.get_column_metas(table_name)
        self.populate_column_stats(table_name, metas, categorical_threshold)
        return format_schema(table_name, metas)


class DuckDBExecutor(QueryExecutor):
    """Shared DuckDB connection for multi-table DataFrameSource queries."""

    def __init__(self, sources: dict[str, DataFrameSource]):
        self._df_lib = get_shared_dataframe_backend(sources)
        self._conn = duckdb.connect(database=":memory:")

        for name, source in sources.items():
            self._conn.register(name, source.get_data())

        # Cache column names per table before lockdown
        self._table_columns: dict[str, list[str]] = {}
        for name in sources:
            result = self._conn.execute(f'SELECT * FROM "{name}" LIMIT 0')
            self._table_columns[name] = [desc[0] for desc in result.description]

        duckdb_lock_down(self._conn)

    def execute_query(self, query: str) -> Any:
        check_query(query)
        result = self._conn.execute(query)
        return self._convert_result(result)

    def _convert_result(self, result: duckdb.DuckDBPyConnection) -> Any:
        if self._df_lib == "polars":
            return result.pl()
        elif self._df_lib == "pandas":
            return result.df()
        elif self._df_lib == "pyarrow":
            return result.fetch_arrow_table()
        else:
            raise ValueError(
                f"Unsupported DataFrame backend: '{self._df_lib}'. "
                "Supported backends are: polars, pandas, pyarrow"
            )

    def test_query(
        self, query: str, *, table_name: str, require_all_columns: bool = False
    ) -> None:
        check_query(query)
        result = self._conn.execute(f"{query} LIMIT 1")

        if require_all_columns:
            result_columns = {desc[0] for desc in result.description}
            expected = set(self._table_columns[table_name])
            missing = expected - result_columns
            if missing:
                missing_list = ", ".join(f"'{c}'" for c in sorted(missing))
                original_list = ", ".join(
                    f"'{c}'" for c in self._table_columns[table_name]
                )
                raise MissingColumnsError(
                    f"Query result missing required columns: {missing_list}. "
                    f"The query must return all original table columns. "
                    f"Original columns: {original_list}"
                )

    def get_db_type(self) -> str:
        return "DuckDB"

    def cleanup(self) -> None:
        if self._conn:
            self._conn.close()

    def get_column_metas(self, table_name: str) -> list[ColumnMeta]:
        result = self._conn.execute(f'SELECT * FROM "{table_name}" LIMIT 0')
        return [duckdb_column_meta(desc[0], desc[1]) for desc in result.description]

    def populate_column_stats(
        self, table_name: str, columns: list[ColumnMeta], categorical_threshold: int
    ) -> None:
        duckdb_column_stats(self._conn, table_name, columns, categorical_threshold)


class PolarsSQLExecutor(QueryExecutor):
    """Shared Polars SQLContext for multi-table PolarsLazySource queries."""

    def __init__(self, sources: dict[str, PolarsLazySource]):
        import polars as pl

        frames = {name: source.get_data() for name, source in sources.items()}
        self._ctx = pl.SQLContext(frames)
        self._sources = sources  # stored for schema delegation

        self._table_columns: dict[str, list[str]] = {}
        for name, source in sources.items():
            self._table_columns[name] = list(source.get_data().collect_schema().keys())

    def execute_query(self, query: str) -> Any:
        check_query(query)
        return self._ctx.execute(query)

    def test_query(
        self, query: str, *, table_name: str, require_all_columns: bool = False
    ) -> None:
        check_query(query)
        test_lf = self._ctx.execute(f"SELECT * FROM ({query}) AS subquery LIMIT 1")
        test_lf.collect()

        if require_all_columns:
            full_lf = self._ctx.execute(query)
            result_columns = set(full_lf.collect_schema().keys())
            expected = set(self._table_columns[table_name])
            missing = expected - result_columns
            if missing:
                missing_list = ", ".join(f"'{c}'" for c in sorted(missing))
                original_list = ", ".join(
                    f"'{c}'" for c in self._table_columns[table_name]
                )
                raise MissingColumnsError(
                    f"Query result missing required columns: {missing_list}. "
                    f"The query must return all original table columns. "
                    f"Original columns: {original_list}"
                )

    def get_db_type(self) -> str:
        return "Polars"

    def cleanup(self) -> None:
        pass

    def get_column_metas(self, table_name: str) -> list[ColumnMeta]:
        return self._sources[table_name].get_column_metas()

    def populate_column_stats(
        self, table_name: str, columns: list[ColumnMeta], categorical_threshold: int
    ) -> None:
        self._sources[table_name].populate_column_stats(columns, categorical_threshold)


class DataSourceExecutor(QueryExecutor):
    """
    Wraps existing DataSource(s) for backends that already share a connection.

    Used for single-table mode (any source type) and multi-table SQLAlchemy/Ibis
    where all sources share the same database backend.
    """

    def __init__(self, data_sources: dict[str, DataSource]):
        validate_source_group_compatibility(data_sources)
        self._data_sources = data_sources
        self._primary = next(iter(data_sources.values()))

    def execute_query(self, query: str) -> Any:
        return self._primary.execute_query(query)

    def test_query(
        self, query: str, *, table_name: str, require_all_columns: bool = False
    ) -> None:
        self._data_sources[table_name].test_query(
            query, require_all_columns=require_all_columns
        )

    def get_db_type(self) -> str:
        return self._primary.get_db_type()

    def cleanup(self) -> None:
        pass

    def get_column_metas(self, table_name: str) -> list[ColumnMeta]:
        return self._data_sources[table_name].get_column_metas()

    def populate_column_stats(
        self, table_name: str, columns: list[ColumnMeta], categorical_threshold: int
    ) -> None:
        self._data_sources[table_name].populate_column_stats(columns, categorical_threshold)


def get_shared_dataframe_backend(sources: dict[str, DataFrameSource]) -> str:
    """Return the shared backend name, rejecting mixed DataFrameSource backends."""
    source_items = iter(sources.items())
    _, first_source = next(source_items)
    shared_lib = get_dataframe_backend_name(first_source)

    for name, source in source_items:
        source_lib = get_dataframe_backend_name(source)
        if source_lib != shared_lib:
            raise ValueError(
                f"Cannot add table '{name}': all DataFrameSources must use "
                f"the same DataFrame backend. "
                f"Existing tables use {shared_lib}, new table uses {source_lib}."
            )

    return shared_lib


def validate_source_group_compatibility(data_sources: dict[str, DataSource]) -> None:
    """Validate that a group of sources satisfies shared executor constraints."""
    existing: dict[str, DataSource] = {}
    for name, source in data_sources.items():
        check_source_compatibility(existing, source, name)
        existing[name] = source


def check_source_compatibility(
    existing: dict[str, DataSource],
    new_source: DataSource,
    new_name: str,
) -> None:
    """Validate that a new source is compatible with existing sources."""
    if not existing:
        return

    from ._datasource import (
        DataFrameSource,
        IbisSource,
        SQLAlchemySource,
    )

    first_source = next(iter(existing.values()))

    if type(new_source) is not type(first_source):
        raise ValueError(
            f"Cannot add {type(new_source).__name__} table '{new_name}': "
            f"all tables must be the same type. "
            f"Existing tables use {type(first_source).__name__}."
        )

    if isinstance(new_source, DataFrameSource) and isinstance(
        first_source, DataFrameSource
    ):
        new_lib = get_dataframe_backend_name(new_source)
        existing_lib = get_dataframe_backend_name(first_source)
        if new_lib != existing_lib:
            raise ValueError(
                f"Cannot add table '{new_name}': all DataFrameSources must use "
                f"the same DataFrame backend. "
                f"Existing tables use {existing_lib}, new table uses {new_lib}."
            )

    if (
        isinstance(new_source, SQLAlchemySource)
        and isinstance(first_source, SQLAlchemySource)
        and new_source.engine is not first_source.engine
    ):
        raise ValueError(
            f"Cannot add table '{new_name}': all SQLAlchemy tables must "
            f"share the same Engine instance."
        )

    if (
        isinstance(new_source, IbisSource)
        and isinstance(first_source, IbisSource)
        and new_source.backend is not first_source.backend
    ):
        raise ValueError(
            f"Cannot add table '{new_name}': all Ibis tables must "
            f"share the same backend instance."
        )


def get_dataframe_backend_name(source: DataFrameSource) -> str:
    """Return the native eager dataframe backend name for a DataFrameSource."""
    return nw.get_native_namespace(
        nw.from_native(source.get_data(), eager_only=True)
    ).__name__
