"""QueryExecutor abstraction for cross-table query execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

import duckdb
import narwhals.stable.v1 as nw

from ._datasource import (
    ColumnMeta,
    MissingColumnsError,
    duckdb_column_meta,
    duckdb_column_stats,
    duckdb_lock_down,
    format_schema,
    quote_identifier,
)
from ._utils import check_query

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ._datasource import DataFrameSource, DataSource, PolarsLazySource
    from ._pin_source import PinSource


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

    def get_column_details(
        self, table_name: str, categorical_threshold: int
    ) -> list[ColumnMeta]:
        metas = self.get_column_metas(table_name)
        self.populate_column_stats(table_name, metas, categorical_threshold)
        return metas

    def get_schema(self, table_name: str, categorical_threshold: int) -> str:
        return format_schema(
            table_name, self.get_column_details(table_name, categorical_threshold)
        )

    @staticmethod
    def _validate_missing_columns(
        result_columns: set[str], expected_columns: list[str]
    ) -> None:
        missing = set(expected_columns) - result_columns
        if missing:
            missing_list = ", ".join(f"'{c}'" for c in sorted(missing))
            original_list = ", ".join(f"'{c}'" for c in expected_columns)
            raise MissingColumnsError(
                f"Query result missing required columns: {missing_list}. "
                f"The query must return all original table columns. "
                f"Original columns: {original_list}"
            )


class DuckDBExecutor(QueryExecutor):
    """
    Shared DuckDB connection for multi-table DataFrameSource/PinSource queries.

    Every source materializes its table into one connection (data frames via
    ``register()``, pins via their file-based materialization), then the
    connection is locked down once.
    """

    def __init__(self, sources: dict[str, DataFrameSource | PinSource]):
        self._df_lib = get_shared_duckdb_result_backend(sources)
        self._conn = duckdb.connect(database=":memory:")
        try:
            for name, source in sources.items():
                source.register_into(self._conn, name)

            # Cache column names per table before lockdown
            self._table_columns: dict[str, list[str]] = {}
            for name in sources:
                result = self._conn.execute(
                    f"SELECT * FROM {quote_identifier(name)} LIMIT 0"
                )
                self._table_columns[name] = [desc[0] for desc in result.description]

            duckdb_lock_down(self._conn)
        except Exception:
            self._conn.close()
            raise

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
            self._validate_missing_columns(
                result_columns, self._table_columns[table_name]
            )

    def get_db_type(self) -> str:
        return "DuckDB"

    def cleanup(self) -> None:
        if self._conn:
            self._conn.close()

    def get_column_metas(self, table_name: str) -> list[ColumnMeta]:
        result = self._conn.execute(
            f"SELECT * FROM {quote_identifier(table_name)} LIMIT 0"
        )
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
            self._validate_missing_columns(
                result_columns, self._table_columns[table_name]
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
        self._data_sources[table_name].populate_column_stats(
            columns, categorical_threshold
        )


def get_shared_duckdb_result_backend(
    sources: dict[str, DataFrameSource | PinSource],
) -> str:
    """
    Pick the result DataFrame backend for a shared DuckDB executor.

    DataFrameSources determine the backend (and must agree with each other);
    pins have no native backend of their own, so an all-pin group follows
    PinSource's own convention: polars when available, pandas otherwise.
    """
    from ._datasource import DataFrameSource

    shared_lib: str | None = None
    for name, source in sources.items():
        if not isinstance(source, DataFrameSource):
            continue
        source_lib = get_dataframe_backend_name(source)
        if shared_lib is None:
            shared_lib = source_lib
        elif source_lib != shared_lib:
            raise ValueError(
                f"Cannot add table '{name}': all DataFrameSources must use "
                f"the same DataFrame backend. "
                f"Existing tables use {shared_lib}, new table uses {source_lib}."
            )

    if shared_lib is not None:
        return shared_lib

    from ._pin_source import _has_polars

    return "polars" if _has_polars() else "pandas"


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
    from ._pin_source import PinSource

    first_source = next(iter(existing.values()))

    duckdb_family = (DataFrameSource, PinSource)
    new_is_duckdb = isinstance(new_source, duckdb_family)
    first_is_duckdb = isinstance(first_source, duckdb_family)

    # DataFrameSources and PinSources may mix freely: both materialize their
    # tables into a shared DuckDBExecutor connection.
    if new_is_duckdb and first_is_duckdb:
        if isinstance(new_source, DataFrameSource):
            new_lib = get_dataframe_backend_name(new_source)
            for source in existing.values():
                if not isinstance(source, DataFrameSource):
                    continue
                existing_lib = get_dataframe_backend_name(source)
                if new_lib != existing_lib:
                    raise ValueError(
                        f"Cannot add table '{new_name}': all DataFrameSources "
                        f"must use the same DataFrame backend. "
                        f"Existing tables use {existing_lib}, new table uses {new_lib}."
                    )
        return

    if new_is_duckdb != first_is_duckdb:
        raise ValueError(
            f"Cannot add {type(new_source).__name__} table '{new_name}': "
            f"{type(first_source).__name__} tables can only be combined with "
            "other tables of the same type. Pins and data frames may be "
            "combined with each other, but not with database-backed sources."
        )

    if type(new_source) is not type(first_source):
        raise ValueError(
            f"Cannot add {type(new_source).__name__} table '{new_name}': "
            f"all tables must be the same type. "
            f"Existing tables use {type(first_source).__name__}."
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


def build_query_executor(sources: Mapping[str, DataSource]) -> QueryExecutor:
    """Pick the executor for a compatible group of sources."""
    from ._datasource import DataFrameSource, PolarsLazySource
    from ._pin_source import PinSource

    # After validation, every source has the same type as the first one,
    # or the whole group is in the DuckDB family (DataFrameSource/PinSource).
    validate_source_group_compatibility(dict(sources))

    if len(sources) == 1:
        return DataSourceExecutor(dict(sources))

    first_source = next(iter(sources.values()))

    if isinstance(first_source, (DataFrameSource, PinSource)):
        return DuckDBExecutor(
            cast("dict[str, DataFrameSource | PinSource]", dict(sources))
        )
    if isinstance(first_source, PolarsLazySource):
        return PolarsSQLExecutor(cast("dict[str, PolarsLazySource]", dict(sources)))

    return DataSourceExecutor(dict(sources))
