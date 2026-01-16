from __future__ import annotations

__all__ = [
    "ColumnMeta",
    "DataFrameSource",
    "DataSource",
    "MissingColumnsError",
    "PolarsLazySource",
    "SQLAlchemySource",
]

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, cast

import duckdb
import narwhals.stable.v1 as nw
from narwhals.stable.v1.typing import IntoDataFrameT, IntoFrameT
from sqlalchemy import inspect, text
from sqlalchemy.sql import sqltypes

from ._df_compat import read_sql
from ._utils import check_query

if TYPE_CHECKING:
    import polars as pl
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
        schema = [f"Table: {self.table_name}", "Columns:"]

        for column in self._df.columns:
            dtype = self._df[column].dtype
            if dtype.is_integer():
                sql_type = "INTEGER"
            elif dtype.is_float():
                sql_type = "FLOAT"
            elif dtype == nw.Boolean:
                sql_type = "BOOLEAN"
            elif dtype == nw.Datetime:
                sql_type = "TIME"
            elif dtype == nw.Date:
                sql_type = "DATE"
            else:
                sql_type = "TEXT"

            column_info = [f"- {column} ({sql_type})"]

            if sql_type == "TEXT":
                unique_values = self._df[column].drop_nulls().unique()
                if unique_values.len() <= categorical_threshold:
                    categories = unique_values.to_list()
                    categories_str = ", ".join([f"'{c}'" for c in categories])
                    column_info.append(f"  Categorical values: {categories_str}")
            elif sql_type in ["INTEGER", "FLOAT", "DATE", "TIME"]:
                rng = self._df[column].min(), self._df[column].max()
                if rng[0] is None and rng[1] is None:
                    column_info.append("  Range: NULL to NULL")
                else:
                    column_info.append(f"  Range: {rng[0]} to {rng[1]}")

            schema.extend(column_info)

        return "\n".join(schema)

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

        # Store original column names for validation
        columns_info = inspector.get_columns(table_name)
        self._colnames = [col["name"] for col in columns_info]

    def get_db_type(self) -> str:
        """
        Get the database type.

        Returns the specific database type (e.g., POSTGRESQL, MYSQL, SQLITE) by
        inspecting the SQLAlchemy engine. Removes " SQL" suffix if present.
        """
        return self._engine.dialect.name.upper().replace(" SQL", "")

    def get_schema(self, *, categorical_threshold: int) -> str:  # noqa: PLR0912
        """
        Generate schema information from database table.

        Returns:
            String describing the schema

        """
        inspector = inspect(self._engine)
        columns = inspector.get_columns(self.table_name)

        schema = [f"Table: {self.table_name}", "Columns:"]

        # Build a single query to get all column statistics
        select_parts = []
        numeric_columns = []
        text_columns = []

        for col in columns:
            col_name = col["name"]

            # Check if column is numeric
            if isinstance(
                col["type"],
                (
                    sqltypes.Integer,
                    sqltypes.Numeric,
                    sqltypes.Float,
                    sqltypes.Date,
                    sqltypes.Time,
                    sqltypes.DateTime,
                    sqltypes.BigInteger,
                    sqltypes.SmallInteger,
                ),
            ):
                numeric_columns.append(col_name)
                select_parts.extend(
                    [
                        f"MIN({col_name}) as {col_name}__min",
                        f"MAX({col_name}) as {col_name}__max",
                    ],
                )

            # Check if column is text/string
            elif isinstance(
                col["type"],
                (sqltypes.String, sqltypes.Text, sqltypes.Enum),
            ):
                text_columns.append(col_name)
                select_parts.append(
                    f"COUNT(DISTINCT {col_name}) as {col_name}__distinct_count",
                )

        # Execute single query to get all statistics
        column_stats = {}
        if select_parts:
            try:
                stats_query = text(
                    f"SELECT {', '.join(select_parts)} FROM {self.table_name}",
                )
                with self._get_connection() as conn:
                    result = conn.execute(stats_query).fetchone()
                    if result:
                        # Convert result to dict for easier access
                        column_stats = dict(zip(result._fields, result, strict=False))
            except Exception:  # noqa: S110
                pass  # Fall back to no statistics if query fails

        # Get categorical values for text columns that are below threshold
        categorical_values = {}
        text_cols_to_query = []
        for col_name in text_columns:
            distinct_count_key = f"{col_name}__distinct_count"
            if (
                distinct_count_key in column_stats
                and column_stats[distinct_count_key]
                and column_stats[distinct_count_key] <= categorical_threshold
            ):
                text_cols_to_query.append(col_name)

        # Get categorical values in a single query if needed
        if text_cols_to_query:
            try:
                # Build UNION query for all categorical columns
                union_parts = [
                    f"SELECT '{col_name}' as column_name, {col_name} as value "
                    f"FROM {self.table_name} WHERE {col_name} IS NOT NULL "
                    f"GROUP BY {col_name}"
                    for col_name in text_cols_to_query
                ]

                if union_parts:
                    categorical_query = text(" UNION ALL ".join(union_parts))
                    with self._get_connection() as conn:
                        results = conn.execute(categorical_query).fetchall()
                        for row in results:
                            col_name, value = row
                            if col_name not in categorical_values:
                                categorical_values[col_name] = []
                            categorical_values[col_name].append(str(value))
            except Exception:  # noqa: S110
                pass  # Skip categorical values if query fails

        # Build schema description using collected statistics
        for col in columns:
            col_name = col["name"]
            sql_type = self._get_sql_type_name(col["type"])
            column_info = [f"- {col_name} ({sql_type})"]

            # Add range info for numeric columns
            if col_name in numeric_columns:
                min_key = f"{col_name}__min"
                max_key = f"{col_name}__max"
                if (
                    min_key in column_stats
                    and max_key in column_stats
                    and column_stats[min_key] is not None
                    and column_stats[max_key] is not None
                ):
                    column_info.append(
                        f"  Range: {column_stats[min_key]} to {column_stats[max_key]}",
                    )

            # Add categorical values for text columns
            elif col_name in categorical_values:
                values = categorical_values[col_name]
                # Remove duplicates and sort
                unique_values = sorted(set(values))
                values_str = ", ".join([f"'{v}'" for v in unique_values])
                column_info.append(f"  Categorical values: {values_str}")

            schema.extend(column_info)

        return "\n".join(schema)

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

    def _get_sql_type_name(self, type_: sqltypes.TypeEngine) -> str:  # noqa: PLR0911
        """Convert SQLAlchemy type to SQL type name."""
        if isinstance(type_, sqltypes.Integer):
            return "INTEGER"
        elif isinstance(type_, sqltypes.Float):
            return "FLOAT"
        elif isinstance(type_, sqltypes.Numeric):
            return "NUMERIC"
        elif isinstance(type_, sqltypes.Boolean):
            return "BOOLEAN"
        elif isinstance(type_, sqltypes.DateTime):
            return "TIMESTAMP"
        elif isinstance(type_, sqltypes.Date):
            return "DATE"
        elif isinstance(type_, sqltypes.Time):
            return "TIME"
        elif isinstance(type_, (sqltypes.String, sqltypes.Text)):
            return "TEXT"
        else:
            return type_.__class__.__name__.upper()

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
        return self._format_schema(self.table_name, columns)

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
            col
            for col in columns
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

    @staticmethod
    def _format_schema(table_name: str, columns: list[ColumnMeta]) -> str:
        """Format column metadata into schema string."""
        lines = [f"Table: {table_name}", "Columns:"]

        for col in columns:
            lines.append(f"- {col.name} ({col.sql_type})")

            if col.kind in ("numeric", "date"):
                lines.append(f"  Range: {col.min_val} to {col.max_val}")
            elif col.categories:
                cats = ", ".join(f"'{v}'" for v in col.categories)
                lines.append(f"  Categorical values: {cats}")

        return "\n".join(lines)
