from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol

import duckdb
import narwhals as nw
import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.sql import sqltypes

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


class DataSource(Protocol):
    db_engine: ClassVar[str]

    def get_schema(self, *, categorical_threshold) -> str:
        """
        Return schema information about the table as a string.

        Args:
            categorical_threshold: Maximum number of unique values for a text
                column to be considered categorical

        Returns:
            A string containing the schema information in a format suitable for
            prompting an LLM about the data structure

        """
        ...

    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query to execute

        Returns:
            Query results as a pandas DataFrame

        """
        ...

    def get_data(self) -> pd.DataFrame:
        """
        Return the unfiltered data as a DataFrame.

        Returns:
            The complete dataset as a pandas DataFrame

        """
        ...


class DataFrameSource:
    """A DataSource implementation that wraps a pandas DataFrame using DuckDB."""

    db_engine: ClassVar[str] = "DuckDB"

    def __init__(self, df: pd.DataFrame, table_name: str):
        """
        Initialize with a pandas DataFrame.

        Args:
            df: The DataFrame to wrap
            table_name: Name of the table in SQL queries

        """
        self._conn = duckdb.connect(database=":memory:")
        self._df = df
        self._table_name = table_name
        self._conn.register(table_name, df)

    def get_schema(self, *, categorical_threshold: int) -> str:
        """
        Generate schema information from DataFrame.

        Args:
            table_name: Name to use for the table in schema description
            categorical_threshold: Maximum number of unique values for a text column
                                to be considered categorical

        Returns:
            String describing the schema

        """
        ndf = nw.from_native(self._df)

        schema = [f"Table: {self._table_name}", "Columns:"]

        for column in ndf.columns:
            # Map pandas dtypes to SQL-like types
            dtype = ndf[column].dtype
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

            # For TEXT columns, check if they're categorical
            if sql_type == "TEXT":
                unique_values = ndf[column].drop_nulls().unique()
                if unique_values.len() <= categorical_threshold:
                    categories = unique_values.to_list()
                    categories_str = ", ".join([f"'{c}'" for c in categories])
                    column_info.append(f"  Categorical values: {categories_str}")

            # For numeric columns, include range
            elif sql_type in ["INTEGER", "FLOAT", "DATE", "TIME"]:
                rng = ndf[column].min(), ndf[column].max()
                if rng[0] is None and rng[1] is None:
                    column_info.append("  Range: NULL to NULL")
                else:
                    column_info.append(f"  Range: {rng[0]} to {rng[1]}")

            schema.extend(column_info)

        return "\n".join(schema)

    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute query using DuckDB.

        Args:
            query: SQL query to execute

        Returns:
            Query results as pandas DataFrame

        """
        return self._conn.execute(query).df()

    def get_data(self) -> pd.DataFrame:
        """
        Return the unfiltered data as a DataFrame.

        Returns:
            The complete dataset as a pandas DataFrame

        """
        return self._df.copy()


class SQLAlchemySource:
    """
    A DataSource implementation that supports multiple SQL databases via SQLAlchemy.

    Supports various databases including PostgreSQL, MySQL, SQLite, Snowflake, and Databricks.
    """

    db_engine: ClassVar[str] = "SQLAlchemy"

    def __init__(self, engine: Engine, table_name: str):
        """
        Initialize with a SQLAlchemy engine.

        Args:
            engine: SQLAlchemy engine
            table_name: Name of the table to query

        """
        self._engine = engine
        self._table_name = table_name

        # Validate table exists
        inspector = inspect(self._engine)
        if not inspector.has_table(table_name):
            raise ValueError(f"Table '{table_name}' not found in database")

    def get_schema(self, *, categorical_threshold: int) -> str:  # noqa: PLR0912
        """
        Generate schema information from database table.

        Returns:
            String describing the schema

        """
        inspector = inspect(self._engine)
        columns = inspector.get_columns(self._table_name)

        schema = [f"Table: {self._table_name}", "Columns:"]

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
                    f"SELECT {', '.join(select_parts)} FROM {self._table_name}",
                )
                with self._get_connection() as conn:
                    result = conn.execute(stats_query).fetchone()
                    if result:
                        # Convert result to dict for easier access
                        column_stats = dict(zip(result._fields, result))
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
                    f"FROM {self._table_name} WHERE {col_name} IS NOT NULL "
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

    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query to execute

        Returns:
            Query results as pandas DataFrame

        """
        with self._get_connection() as conn:
            return pd.read_sql_query(text(query), conn)

    def get_data(self) -> pd.DataFrame:
        """
        Return the unfiltered data as a DataFrame.

        Returns:
            The complete dataset as a pandas DataFrame

        """
        return self.execute_query(f"SELECT * FROM {self._table_name}")

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
