from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import duckdb
import narwhals.stable.v1 as nw
from sqlalchemy import inspect, text
from sqlalchemy.sql import sqltypes

from ._df_compat import duckdb_result_to_nw, read_sql
from ._utils import check_query

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


class MissingColumnsError(ValueError):
    """Raised when a query result is missing required columns."""


class DataSource(ABC):
    """
    An abstract class defining the interface for data sources used by QueryChat.

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
            Query results as a narwhals DataFrame

        """
        ...

    @abstractmethod
    def test_query(
        self, query: str, *, require_all_columns: bool = False
    ) -> nw.DataFrame:
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
            Query results as a narwhals DataFrame with at most one row

        Raises
        ------
        MissingColumnsError
            If require_all_columns is True and result is missing required columns

        """
        ...

    @abstractmethod
    def get_data(self) -> nw.DataFrame:
        """
        Return the unfiltered data as a DataFrame.

        Returns
        -------
        :
            The complete dataset as a narwhals DataFrame

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


class DataFrameSource(DataSource):
    """A DataSource implementation that wraps a DataFrame using DuckDB."""

    _df: nw.DataFrame

    def __init__(self, df: nw.DataFrame, table_name: str):
        """
        Initialize with a DataFrame.

        Parameters
        ----------
        df
            The DataFrame to wrap (pandas, polars, or any narwhals-compatible frame)
        table_name
            Name of the table in SQL queries

        """
        self._df = nw.from_native(df) if not isinstance(df, nw.DataFrame) else df
        self.table_name = table_name

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
                sql_type = "TIMESTAMP"
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
            elif sql_type in ["INTEGER", "FLOAT", "DATE", "TIMESTAMP"]:
                rng = self._df[column].min(), self._df[column].max()
                if rng[0] is None and rng[1] is None:
                    column_info.append("  Range: NULL to NULL")
                else:
                    column_info.append(f"  Range: {rng[0]} to {rng[1]}")

            schema.extend(column_info)

        return "\n".join(schema)

    def execute_query(self, query: str) -> nw.DataFrame:
        """
        Execute query using DuckDB.

        Uses polars if available, otherwise falls back to pandas.

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
        return duckdb_result_to_nw(self._conn.execute(query))

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
        result = duckdb_result_to_nw(self._conn.execute(f"{query} LIMIT 1"))

        if require_all_columns:
            result_columns = set(result.columns)
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

        return result

    def get_data(self) -> nw.DataFrame:
        """
        Return the unfiltered data as a DataFrame.

        Returns
        -------
        :
            The complete dataset as a narwhals DataFrame

        """
        return self._df

    def cleanup(self) -> None:
        """
        Close the DuckDB connection.

        Returns
        -------
        None

        """
        if self._conn:
            self._conn.close()


class SQLAlchemySource(DataSource):
    """
    A DataSource implementation that supports multiple SQL databases via
    SQLAlchemy.

    Supports various databases including PostgreSQL, MySQL, SQLite, Snowflake,
    and Databricks.
    """

    def __init__(self, engine: Engine, table_name: str):
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

        Uses polars if available, otherwise falls back to pandas.

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
            The complete dataset as a narwhals DataFrame

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
