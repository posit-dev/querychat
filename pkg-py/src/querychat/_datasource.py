from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, cast

import duckdb
import narwhals.stable.v1 as nw
from narwhals.stable.v1.typing import IntoDataFrameT, IntoFrameT
from sqlalchemy import inspect, text
from sqlalchemy.sql import sqltypes

from ._df_compat import read_sql
from ._snowflake import (
    discover_semantic_views,
    format_semantic_views,
)
from ._utils import as_narwhals, check_query

if TYPE_CHECKING:
    import ibis
    import polars as pl
    from ibis.backends.sql import SQLBackend
    from ibis.expr.datatypes import DataType as IbisDataType
    from narwhals.dtypes import DType
    from sqlalchemy.engine import Connection, Engine


class MissingColumnsError(ValueError):
    """Raised when a query result is missing required columns."""


@dataclass
class ColumnMeta:
    """Metadata for a single column in a schema."""

    name: str
    """Column name."""

    sql_type: str
    """SQL type name (e.g., 'INTEGER', 'TEXT', 'DATE')."""

    kind: Literal["numeric", "text", "date", "other"]
    """Column category for determining what stats to collect."""

    min_val: Any = None
    """Minimum value for numeric/date columns."""

    max_val: Any = None
    """Maximum value for numeric/date columns."""

    categories: list[str] = field(default_factory=list)
    """Unique values for text columns below the categorical threshold."""


def format_schema(table_name: str, columns: list[ColumnMeta]) -> str:
    """Format column metadata into schema string."""
    lines = [f"Table: {table_name}", "Columns:"]

    for col in columns:
        lines.append(f"- {col.name} ({col.sql_type})")

        if col.kind in ("numeric", "date") and col.min_val is not None and col.max_val is not None:
            lines.append(f"  Range: {col.min_val} to {col.max_val}")
        elif col.categories:
            cats = ", ".join(f"'{v}'" for v in col.categories)
            lines.append(f"  Categorical values: {cats}")

    return "\n".join(lines)


class DataSource(ABC, Generic[IntoFrameT]):
    """
    An abstract class defining the interface for data sources used by QueryChat.

    This class is generic over the DataFrame type returned by execute_query,
    test_query, and get_data methods.

    Attributes
    ----------
    table_name
        Name of the table to be used in SQL queries.

    """

    table_name: str

    @abstractmethod
    def get_db_type(self) -> str:
        """Name for the database behind the SQL execution."""
        ...

    @abstractmethod
    def get_schema(self, *, categorical_threshold: int) -> str:
        """
        Return schema information about the table as a string.

        Parameters
        ----------
        categorical_threshold
            Maximum number of unique values for a text column to be considered
            categorical

        Returns
        -------
        :
            A string containing the schema information in a format suitable for
            prompting an LLM about the data structure

        """
        ...

    @abstractmethod
    def execute_query(self, query: str) -> IntoFrameT:
        """
        Execute SQL query and return results.

        Parameters
        ----------
        query
            SQL query to execute

        Returns
        -------
        :
            Query results

        """
        ...

    @abstractmethod
    def test_query(
        self, query: str, *, require_all_columns: bool = False
    ) -> IntoFrameT:
        """
        Test SQL query by fetching only one row.

        Parameters
        ----------
        query
            SQL query to test
        require_all_columns
            If True, validates that result includes all original table columns.
            Additional computed columns are allowed.

        Returns
        -------
        :
            Query results with at most one row

        Raises
        ------
        MissingColumnsError
            If require_all_columns is True and result is missing required columns

        """
        ...

    @abstractmethod
    def get_data(self) -> IntoFrameT:
        """
        Return the unfiltered data.

        Returns
        -------
        :
            The complete dataset

        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up resources associated with the data source.

        This method should clean up any connections or resources used by the
        data source.

        Returns
        -------
        None

        """

    def get_semantic_views_description(self) -> str:
        """Get the complete semantic views section for the prompt."""
        return ""


class DataFrameSource(DataSource[IntoDataFrameT]):
    """A DataSource implementation that wraps a DataFrame using DuckDB."""

    _df: nw.DataFrame
    _df_lib: str

    def __init__(self, df: nw.DataFrame, table_name: str):
        """
        Initialize with a DataFrame.

        Parameters
        ----------
        df
            A narwhals DataFrame
        table_name
            Name of the table in SQL queries

        """
        self._df = df
        self.table_name = table_name

        # Track the native backend for returning results in the same format
        native_namespace = nw.get_native_namespace(df)
        self._df_lib = native_namespace.__name__

        self._conn = duckdb.connect(database=":memory:")
        self._conn.register(table_name, self._df.to_native())
        self._conn.execute("""
-- extensions: lock down supply chain + auto behaviors
SET allow_community_extensions = false;
SET allow_unsigned_extensions = false;
SET autoinstall_known_extensions = false;
SET autoload_known_extensions = false;

-- external I/O: block file/database/network access from SQL
SET enable_external_access = false;
SET disabled_filesystems = 'LocalFileSystem';

-- freeze configuration so user SQL can't relax anything
SET lock_configuration = true;
        """)

        # Store original column names for validation
        self._colnames = list(self._df.columns)

    def get_db_type(self) -> str:
        """
        Get the database type.

        Returns
        -------
        :
            The string "DuckDB"

        """
        return "DuckDB"

    def get_schema(self, *, categorical_threshold: int) -> str:
        """
        Generate schema information from DataFrame.

        Parameters
        ----------
        categorical_threshold
            Maximum number of unique values for a text column to be considered
            categorical

        Returns
        -------
        :
            String describing the schema

        """
        columns = [
            self._make_column_meta(col, self._df[col].dtype) for col in self._df.columns
        ]
        self._add_column_stats(columns, self._df, categorical_threshold)
        return format_schema(self.table_name, columns)

    @staticmethod
    def _make_column_meta(name: str, dtype: DType) -> ColumnMeta:
        """Create ColumnMeta from a narwhals dtype."""
        kind: Literal["numeric", "text", "date", "other"]
        if dtype.is_integer():
            kind = "numeric"
            sql_type = "INTEGER"
        elif dtype.is_float():
            kind = "numeric"
            sql_type = "FLOAT"
        elif dtype == nw.Boolean:
            kind = "other"
            sql_type = "BOOLEAN"
        elif dtype == nw.Datetime:
            kind = "date"
            sql_type = "TIME"
        elif dtype == nw.Date:
            kind = "date"
            sql_type = "DATE"
        else:
            kind = "text"
            sql_type = "TEXT"

        return ColumnMeta(name=name, sql_type=sql_type, kind=kind)

    @staticmethod
    def _add_column_stats(
        columns: list[ColumnMeta],
        df: nw.DataFrame,
        categorical_threshold: int,
    ) -> None:
        """Add min/max/categories to column metadata."""
        for col in columns:
            if col.kind in ("numeric", "date"):
                col.min_val = df[col.name].min()
                col.max_val = df[col.name].max()
            elif col.kind == "text":
                unique_values = df[col.name].drop_nulls().unique()
                if unique_values.len() <= categorical_threshold:
                    col.categories = unique_values.to_list()

    def execute_query(self, query: str) -> IntoDataFrameT:
        """
        Execute query using DuckDB.

        Returns results in the same format as the input DataFrame (polars or pandas).

        Parameters
        ----------
        query
            SQL query to execute

        Returns
        -------
        :
            Query results as native DataFrame (polars or pandas, matching input)

        Raises
        ------
        UnsafeQueryError
            If the query starts with a disallowed SQL operation

        """
        check_query(query)
        result = self._conn.execute(query)
        return self._convert_result(result)

    def _convert_result(self, result: duckdb.DuckDBPyConnection) -> IntoDataFrameT:
        """
        Convert DuckDB result to the appropriate native DataFrame type.

        The returned type matches the input DataFrame's library (polars, pandas, or
        pyarrow). The cast is safe because we detect the library at init time and
        return results in the same format.
        """
        native_df: Any
        if self._df_lib == "polars":
            native_df = result.pl()
        elif self._df_lib == "pandas":
            native_df = result.df()
        elif self._df_lib == "pyarrow":
            native_df = result.fetch_arrow_table()
        else:
            raise ValueError(
                f"Unsupported DataFrame backend: '{self._df_lib}'. "
                "Supported backends are: polars, pandas, pyarrow"
            )
        return cast("IntoDataFrameT", native_df)

    def test_query(
        self, query: str, *, require_all_columns: bool = False
    ) -> IntoDataFrameT:
        """
        Test query by fetching only one row.

        Parameters
        ----------
        query
            SQL query to test
        require_all_columns
            If True, validates that result includes all original table columns

        Returns
        -------
        :
            Query results with at most one row

        Raises
        ------
        UnsafeQueryError
            If the query starts with a disallowed SQL operation
        MissingColumnsError
            If require_all_columns is True and result is missing required columns

        """
        check_query(query)
        result = self._conn.execute(f"{query} LIMIT 1")
        native_result = self._convert_result(result)

        if require_all_columns:
            wrapped = nw.from_native(native_result)
            result_columns = set(wrapped.columns)
            original_columns_set = set(self._colnames)
            missing_columns = original_columns_set - result_columns

            if missing_columns:
                missing_list = ", ".join(f"'{col}'" for col in sorted(missing_columns))
                original_list = ", ".join(f"'{col}'" for col in self._colnames)
                raise MissingColumnsError(
                    f"Query result missing required columns: {missing_list}. "
                    f"The query must return all original table columns. "
                    f"Original columns: {original_list}"
                )

        return native_result

    def get_data(self) -> IntoDataFrameT:
        """
        Return the unfiltered data as a DataFrame.

        Returns
        -------
        :
            The complete dataset as native DataFrame (polars or pandas, matching input)

        """
        return self._df.to_native()

    def cleanup(self) -> None:
        """
        Close the DuckDB connection.

        Returns
        -------
        None

        """
        if self._conn:
            self._conn.close()


class SQLAlchemySource(DataSource[nw.DataFrame]):
    """
    A DataSource implementation that supports multiple SQL databases via
    SQLAlchemy.

    Supports various databases including PostgreSQL, MySQL, SQLite, Snowflake,
    and Databricks.
    """

    def __init__(
        self,
        engine: Engine,
        table_name: str,
    ):
        """
        Initialize with a SQLAlchemy engine.

        Parameters
        ----------
        engine
            SQLAlchemy engine
        table_name
            Name of the table to query

        """
        self._engine = engine
        self.table_name = table_name

        # Validate table exists
        inspector = inspect(self._engine)
        if not inspector.has_table(table_name):
            raise ValueError(f"Table '{table_name}' not found in database")

        # Store column info for schema generation
        self._columns_info = inspector.get_columns(table_name)
        self._colnames = [col["name"] for col in self._columns_info]

    def get_db_type(self) -> str:
        """
        Get the database type.

        Returns the specific database type (e.g., POSTGRESQL, MYSQL, SQLITE) by
        inspecting the SQLAlchemy engine. Removes " SQL" suffix if present.
        """
        return self._engine.dialect.name.upper().replace(" SQL", "")

    def get_schema(self, *, categorical_threshold: int) -> str:
        """
        Generate schema information from database table.

        Parameters
        ----------
        categorical_threshold
            Maximum number of unique values for a text column to be considered
            categorical

        Returns
        -------
        :
            String describing the schema

        """
        columns = [
            self._make_column_meta(col["name"], col["type"])
            for col in self._columns_info
        ]
        self._add_column_stats(columns, categorical_threshold)
        return format_schema(self.table_name, columns)

    def get_semantic_views_description(self) -> str:
        """Get the complete semantic views section for the prompt."""
        if self._engine.dialect.name.lower() != "snowflake":
            return ""
        views = discover_semantic_views(self._engine)
        return format_semantic_views(views)

    @staticmethod
    def _make_column_meta(name: str, sa_type: sqltypes.TypeEngine) -> ColumnMeta:
        """Create ColumnMeta from SQLAlchemy type."""
        kind: Literal["numeric", "text", "date", "other"]

        if isinstance(sa_type, (sqltypes.Integer, sqltypes.BigInteger, sqltypes.SmallInteger)):
            kind = "numeric"
            sql_type = "INTEGER"
        elif isinstance(sa_type, sqltypes.Float):
            kind = "numeric"
            sql_type = "FLOAT"
        elif isinstance(sa_type, sqltypes.Numeric):
            kind = "numeric"
            sql_type = "NUMERIC"
        elif isinstance(sa_type, (sqltypes.String, sqltypes.Text, sqltypes.Enum)):
            kind = "text"
            sql_type = "TEXT"
        elif isinstance(sa_type, sqltypes.Date):
            kind = "date"
            sql_type = "DATE"
        elif isinstance(sa_type, sqltypes.DateTime):
            kind = "date"
            sql_type = "TIMESTAMP"
        elif isinstance(sa_type, sqltypes.Time):
            kind = "date"
            sql_type = "TIME"
        elif isinstance(sa_type, sqltypes.Boolean):
            kind = "other"
            sql_type = "BOOLEAN"
        else:
            kind = "other"
            sql_type = sa_type.__class__.__name__.upper()

        return ColumnMeta(name=name, sql_type=sql_type, kind=kind)

    def _add_column_stats(
        self,
        columns: list[ColumnMeta],
        categorical_threshold: int,
    ) -> None:
        """Add min/max/categories to column metadata using SQL queries."""
        # Build aggregate expressions for stats query
        select_parts = []
        for col in columns:
            if col.kind in ("numeric", "date"):
                select_parts.append(f"MIN({col.name}) as {col.name}__min")
                select_parts.append(f"MAX({col.name}) as {col.name}__max")
            elif col.kind == "text":
                select_parts.append(f"COUNT(DISTINCT {col.name}) as {col.name}__nunique")

        if not select_parts:
            return

        # Execute stats query
        stats = {}
        try:
            stats_query = text(f"SELECT {', '.join(select_parts)} FROM {self.table_name}")
            with self._get_connection() as conn:
                result = conn.execute(stats_query).fetchone()
                if result:
                    stats = dict(zip(result._fields, result, strict=False))
        except Exception:
            return  # Fall back to no statistics if query fails

        # Populate min/max for numeric/date columns
        for col in columns:
            if col.kind in ("numeric", "date"):
                col.min_val = stats.get(f"{col.name}__min")
                col.max_val = stats.get(f"{col.name}__max")

        # Find text columns that qualify as categorical
        categorical_cols = [
            col for col in columns
            if col.kind == "text"
            and (nunique := stats.get(f"{col.name}__nunique"))
            and nunique <= categorical_threshold
        ]

        if not categorical_cols:
            return

        # Fetch categorical values in a single UNION query
        self._fetch_categorical_values(categorical_cols)

    def _fetch_categorical_values(self, columns: list[ColumnMeta]) -> None:
        """Fetch unique values for categorical columns."""
        union_parts = [
            f"SELECT '{col.name}' as col_name, {col.name} as value "
            f"FROM {self.table_name} WHERE {col.name} IS NOT NULL "
            f"GROUP BY {col.name}"
            for col in columns
        ]

        try:
            query = text(" UNION ALL ".join(union_parts))
            with self._get_connection() as conn:
                results = conn.execute(query).fetchall()

                # Group values by column
                values_by_col: dict[str, list[str]] = {}
                for col_name, value in results:
                    values_by_col.setdefault(col_name, []).append(str(value))

                # Assign to columns
                for col in columns:
                    if col.name in values_by_col:
                        col.categories = sorted(set(values_by_col[col.name]))
        except Exception:  # noqa: S110
            pass  # Skip categorical values if query fails

    def execute_query(self, query: str) -> nw.DataFrame:
        """
        Execute SQL query and return results as DataFrame.

        Parameters
        ----------
        query
            SQL query to execute

        Returns
        -------
        :
            Query results as narwhals DataFrame

        Raises
        ------
        UnsafeQueryError
            If the query starts with a disallowed SQL operation

        """
        check_query(query)
        with self._get_connection() as conn:
            return read_sql(text(query), conn)

    def test_query(
        self, query: str, *, require_all_columns: bool = False
    ) -> nw.DataFrame:
        """
        Test query by fetching only one row.

        Parameters
        ----------
        query
            SQL query to test
        require_all_columns
            If True, validates that result includes all original table columns

        Returns
        -------
        :
            Query results with at most one row

        Raises
        ------
        UnsafeQueryError
            If the query starts with a disallowed SQL operation
        MissingColumnsError
            If require_all_columns is True and result is missing required columns

        """
        check_query(query)
        with self._get_connection() as conn:
            # Use read_sql with limit to get at most one row
            limit_query = f"SELECT * FROM ({query}) AS subquery LIMIT 1"
            try:
                result = read_sql(text(limit_query), conn)
            except Exception:
                # If LIMIT syntax doesn't work, fall back to regular read and take first row
                result = read_sql(text(query), conn).head(1)

            if require_all_columns:
                result_columns = set(result.columns)
                original_columns_set = set(self._colnames)
                missing_columns = original_columns_set - result_columns

                if missing_columns:
                    missing_list = ", ".join(
                        f"'{col}'" for col in sorted(missing_columns)
                    )
                    original_list = ", ".join(f"'{col}'" for col in self._colnames)
                    raise MissingColumnsError(
                        f"Query result missing required columns: {missing_list}. "
                        f"The query must return all original table columns. "
                        f"Original columns: {original_list}"
                    )

            return result

    def get_data(self) -> nw.DataFrame:
        """
        Return the unfiltered data as a DataFrame.

        Returns
        -------
        :
            The complete dataset as narwhals DataFrame

        """
        return self.execute_query(f"SELECT * FROM {self.table_name}")

    def _get_connection(self) -> Connection:
        """Get a connection to use for queries."""
        return self._engine.connect()

    def cleanup(self) -> None:
        """
        Dispose of the SQLAlchemy engine.

        Returns
        -------
        None

        """
        if self._engine:
            self._engine.dispose()


class PolarsLazySource(DataSource["pl.LazyFrame"]):
    """
    A DataSource implementation for Polars LazyFrames.

    Keeps data lazy throughout the query pipeline. Results from execute_query()
    are LazyFrames that can be chained with additional operations before
    collecting.
    """

    table_name: str

    def __init__(self, lf: nw.LazyFrame, table_name: str):
        """
        Initialize with a narwhals LazyFrame wrapping a Polars LazyFrame.

        Parameters
        ----------
        lf
            A narwhals LazyFrame (wrapping a Polars LazyFrame)
        table_name
            Name of the table in SQL queries

        """
        import polars as pl

        self.table_name = table_name

        # Get native Polars LazyFrame for SQLContext
        self._lf: pl.LazyFrame = lf.to_native()
        if not isinstance(self._lf, pl.LazyFrame):
            raise TypeError(f"Expected Polars LazyFrame, got {type(self._lf).__name__}")

        self._ctx = pl.SQLContext({table_name: self._lf})

        # Cache schema (no data collection needed)
        self._schema = self._lf.collect_schema()
        self._colnames = list(self._schema.keys())

    def get_db_type(self) -> str:
        """Get the database type."""
        return "Polars"

    def get_schema(self, *, categorical_threshold: int) -> str:
        """Generate schema information from LazyFrame using lazy aggregates."""
        # Build column metadata (classification happens here)
        columns = [
            self._make_column_meta(name, dtype) for name, dtype in self._schema.items()
        ]

        # Add stats to the metadata and format schema string
        self._add_column_stats(columns, self._lf, categorical_threshold)
        return format_schema(self.table_name, columns)

    def execute_query(self, query: str) -> pl.LazyFrame:
        """
        Execute SQL query and return results as LazyFrame.

        Parameters
        ----------
        query
            SQL query to execute

        Returns
        -------
        :
            Query results as a native Polars LazyFrame

        """
        check_query(query)
        return self._ctx.execute(query)

    def test_query(
        self, query: str, *, require_all_columns: bool = False
    ) -> pl.LazyFrame:
        """
        Test SQL query validity by executing and validating.

        Parameters
        ----------
        query
            SQL query to test
        require_all_columns
            If True, validates that result includes all original table columns

        Returns
        -------
        :
            Query results as a Polars LazyFrame

        """
        check_query(query)

        lf = self._ctx.execute(query)

        # Collect one row to catch runtime errors (e.g., division by zero)
        test_lf = self._ctx.execute(f"SELECT * FROM ({query}) AS subquery LIMIT 1")
        collected = test_lf.collect()

        if require_all_columns:
            result_columns = set(collected.columns)
            missing = set(self._colnames) - result_columns
            if missing:
                missing_list = ", ".join(f"'{c}'" for c in sorted(missing))
                original_list = ", ".join(f"'{c}'" for c in self._colnames)
                raise MissingColumnsError(
                    f"Query result missing required columns: {missing_list}. "
                    f"The query must return all original table columns. "
                    f"Original columns: {original_list}"
                )

        # Return the original LazyFrame (not the collected test result)
        return lf

    def get_data(self) -> pl.LazyFrame:
        """
        Return the unfiltered data as a LazyFrame.

        Returns
        -------
        :
            The original native Polars LazyFrame

        """
        return self._lf

    def cleanup(self) -> None:
        """Clean up resources (no-op for Polars)."""

    @staticmethod
    def _make_column_meta(name: str, dtype: pl.DataType) -> ColumnMeta:
        import polars as pl

        if dtype.is_numeric():
            kind = "numeric"
            sql_type = "INTEGER" if dtype.is_integer() else "FLOAT"
        elif dtype == pl.String:
            kind = "text"
            sql_type = "TEXT"
        elif dtype == pl.Date:
            kind = "date"
            sql_type = "DATE"
        elif dtype == pl.Datetime:
            kind = "date"
            sql_type = "TIMESTAMP"
        elif dtype == pl.Boolean:
            kind = "other"
            sql_type = "BOOLEAN"
        elif dtype == pl.Time:
            kind = "other"
            sql_type = "TIME"
        else:
            kind = "other"
            sql_type = "TEXT"

        return ColumnMeta(name=name, sql_type=sql_type, kind=kind)

    @staticmethod
    def _add_column_stats(
        columns: list[ColumnMeta],
        lf: pl.LazyFrame,
        categorical_threshold: int,
    ) -> None:
        import polars as pl

        # Build aggregation expressions based on column kinds
        agg_exprs: list[pl.Expr] = []
        for col in columns:
            if col.kind in ("numeric", "date"):
                agg_exprs.append(pl.col(col.name).min().alias(f"{col.name}__min"))
                agg_exprs.append(pl.col(col.name).max().alias(f"{col.name}__max"))
            elif col.kind == "text":
                agg_exprs.append(
                    pl.col(col.name).n_unique().alias(f"{col.name}__nunique")
                )

        if not agg_exprs:
            return

        # First scan: collect all aggregate statistics
        stats = lf.select(agg_exprs).collect().row(0, named=True)

        # Add min/max for numeric/date columns
        for col in columns:
            if col.kind in ("numeric", "date"):
                col.min_val = stats.get(f"{col.name}__min")
                col.max_val = stats.get(f"{col.name}__max")

        # Find text columns that qualify as categorical
        categorical_cols = [
            col for col in columns
            if col.kind == "text"
            and (nunique := stats.get(f"{col.name}__nunique"))
            and nunique <= categorical_threshold
        ]

        if not categorical_cols:
            return

        # Second scan: batch collect unique values for all categorical columns
        unique_exprs = [
            pl.col(col.name).drop_nulls().unique().implode().alias(col.name)
            for col in categorical_cols
        ]
        unique_row = lf.select(unique_exprs).collect().row(0, named=True)

        for col in categorical_cols:
            col.categories = unique_row[col.name]


class IbisSource(DataSource["ibis.Table"]):
    """
    A DataSource implementation for Ibis Tables.

    Keeps queries lazy - results from execute_query() are Ibis Tables
    that can be chained with additional operations before collecting.
    """

    _table: ibis.Table
    _backend: SQLBackend
    table_name: str

    def __init__(self, table: ibis.Table, table_name: str):
        from ibis.backends.sql import SQLBackend

        self._table = table
        self.table_name = table_name
        self._schema = table.schema()

        backend = table.get_backend()
        if not isinstance(backend, SQLBackend):
            raise TypeError(
                f"Expected SQL backend, got {type(backend).__name__}. "
                "IbisSource only supports SQL backends."
            )
        self._backend = backend

        colnames = self._schema.names
        if not isinstance(colnames, (tuple, list)):
            raise TypeError(
                f"Expected schema names to be a tuple or list, got {type(colnames).__name__}"
            )
        self._colnames = list(colnames)

    def get_db_type(self) -> str:
        return self._backend.name

    def get_schema(self, *, categorical_threshold: int) -> str:
        columns = [
            self._make_column_meta(name, dtype) for name, dtype in self._schema.items()
        ]
        self._add_column_stats(columns, self._table, categorical_threshold)
        return format_schema(self.table_name, columns)

    def get_semantic_views_description(self) -> str:
        """Get the complete semantic views section for the prompt."""
        if self._backend.name.lower() != "snowflake":
            return ""
        views = discover_semantic_views(self._backend)
        return format_semantic_views(views)

    @staticmethod
    def _make_column_meta(name: str, dtype: IbisDataType) -> ColumnMeta:
        """Create ColumnMeta from an ibis dtype."""
        kind: Literal["numeric", "text", "date", "other"]
        if dtype.is_numeric():
            kind = "numeric"
            sql_type = "INTEGER" if dtype.is_integer() else "FLOAT"
        elif dtype.is_string():
            kind = "text"
            sql_type = "TEXT"
        elif dtype.is_date():
            kind = "date"
            sql_type = "DATE"
        elif dtype.is_timestamp():
            kind = "date"
            sql_type = "TIMESTAMP"
        elif dtype.is_boolean():
            kind = "other"
            sql_type = "BOOLEAN"
        elif dtype.is_time():
            kind = "other"
            sql_type = "TIME"
        else:
            kind = "other"
            sql_type = "TEXT"

        return ColumnMeta(name=name, sql_type=sql_type, kind=kind)

    @staticmethod
    def _add_column_stats(
        columns: list[ColumnMeta],
        table: ibis.Table,
        categorical_threshold: int,
    ) -> None:
        """Add min/max/categories to column metadata using ibis aggregates."""
        agg_exprs = []
        for col in columns:
            if col.kind in ("numeric", "date"):
                agg_exprs.append(table[col.name].min().name(f"{col.name}__min"))
                agg_exprs.append(table[col.name].max().name(f"{col.name}__max"))
            elif col.kind == "text":
                agg_exprs.append(table[col.name].nunique().name(f"{col.name}__nunique"))

        if not agg_exprs:
            return

        stats_nw = as_narwhals(table.aggregate(agg_exprs).execute())
        # Some backends return empty results for aggregations on empty tables
        if stats_nw.shape[0] == 0:
            return
        stats = dict(zip(stats_nw.columns, stats_nw.row(0), strict=True))

        for col in columns:
            if col.kind in ("numeric", "date"):
                col.min_val = stats.get(f"{col.name}__min")
                col.max_val = stats.get(f"{col.name}__max")

        categorical_cols = [
            col for col in columns
            if col.kind == "text"
            and (nunique := stats.get(f"{col.name}__nunique"))
            and nunique <= categorical_threshold
        ]

        if not categorical_cols:
            return

        # Batch all categorical value queries into a single UNION query
        import ibis

        subqueries: list[ibis.Table] = []
        for col in categorical_cols:
            subq = (
                table.select(
                    ibis.literal(col.name).name("_col_name"),
                    table[col.name].cast("string").name("_value"),
                )
                .filter(table[col.name].notnull())
                .distinct()
            )
            subqueries.append(subq)

        combined = ibis.union(*subqueries)

        result_nw = as_narwhals(combined.execute())
        for col in categorical_cols:
            col_values = (
                result_nw.filter(nw.col("_col_name") == col.name)
                .get_column("_value")
                .to_list()
            )
            col.categories = col_values

    def execute_query(self, query: str) -> ibis.Table:
        """
        Execute SQL query and return results as an Ibis Table (lazy).

        Parameters
        ----------
        query
            SQL query to execute

        Returns
        -------
        :
            Query results as an Ibis Table

        Raises
        ------
        UnsafeQueryError
            If the query starts with a disallowed SQL operation

        """
        check_query(query)
        return self._backend.sql(query)

    def test_query(
        self, query: str, *, require_all_columns: bool = False
    ) -> ibis.Table:
        """
        Test SQL query validity by executing and validating.

        Parameters
        ----------
        query
            SQL query to test
        require_all_columns
            If True, validates that result includes all original table columns

        Returns
        -------
        :
            Query results as an Ibis Table

        Raises
        ------
        UnsafeQueryError
            If the query starts with a disallowed SQL operation
        MissingColumnsError
            If require_all_columns is True and result is missing required columns

        """
        check_query(query)

        result = self._backend.sql(query)

        # Collect one row to validate and catch runtime errors
        collected = result.limit(1).execute()

        if require_all_columns:
            result_columns = set(as_narwhals(collected).columns)
            missing = set(self._colnames) - result_columns
            if missing:
                missing_list = ", ".join(f"'{c}'" for c in sorted(missing))
                original_list = ", ".join(f"'{c}'" for c in self._colnames)
                raise MissingColumnsError(
                    f"Query result missing required columns: {missing_list}. "
                    f"The query must return all original table columns. "
                    f"Original columns: {original_list}"
                )

        return result

    def get_data(self) -> ibis.Table:
        return self._table

    def cleanup(self) -> None:
        """
        Clean up resources (no-op for Ibis).

        The Ibis backend connection is owned by the caller and should be
        closed by calling `backend.disconnect()` when appropriate.
        """
