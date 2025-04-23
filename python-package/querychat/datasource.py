from __future__ import annotations

from typing import ClassVar, Protocol

import duckdb
import narwhals as nw
import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql import sqltypes


class DataSource(Protocol):
    db_engine: ClassVar[str]

    def get_schema(self) -> str:
        """Return schema information about the table as a string.

        Returns:
            A string containing the schema information in a format suitable for
            prompting an LLM about the data structure
        """
        ...

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query to execute

        Returns:
            Query results as a pandas DataFrame
        """
        ...

    def get_data(self) -> pd.DataFrame:
        """Return the unfiltered data as a DataFrame.

        Returns:
            The complete dataset as a pandas DataFrame
        """
        ...


class DataFrameSource:
    """A DataSource implementation that wraps a pandas DataFrame using DuckDB."""

    db_engine: ClassVar[str] = "DuckDB"

    def __init__(self, df: pd.DataFrame, table_name: str):
        """Initialize with a pandas DataFrame.

        Args:
            df: The DataFrame to wrap
            table_name: Name of the table in SQL queries
        """
        self._conn = duckdb.connect(database=":memory:")
        self._df = df
        self._table_name = table_name
        self._conn.register(table_name, df)

    def get_schema(self, categorical_threshold: int = 10) -> str:
        """Generate schema information from DataFrame.

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
        """Execute query using DuckDB.

        Args:
            query: SQL query to execute

        Returns:
            Query results as pandas DataFrame
        """
        return self._conn.execute(query).df()

    def get_data(self) -> pd.DataFrame:
        """Return the unfiltered data as a DataFrame.

        Returns:
            The complete dataset as a pandas DataFrame
        """
        return self._df.copy()


class SQLAlchemySource:
    """A DataSource implementation that supports multiple SQL databases via SQLAlchemy.

    Supports various databases including PostgreSQL, MySQL, SQLite, Snowflake, and Databricks.
    """

    db_engine: ClassVar[str] = "SQLAlchemy"

    def __init__(self, engine: Engine, table_name: str):
        """Initialize with a SQLAlchemy engine.

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

    def get_schema(self) -> str:
        """Generate schema information from database table.

        Returns:
            String describing the schema
        """
        inspector = inspect(self._engine)
        columns = inspector.get_columns(self._table_name)

        schema = [f"Table: {self._table_name}", "Columns:"]

        for col in columns:
            # Get SQL type name
            sql_type = self._get_sql_type_name(col["type"])
            column_info = [f"- {col['name']} ({sql_type})"]

            # For numeric columns, try to get range
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
                    # sqltypes.Interval,
                ),
            ):
                try:
                    query = text(
                        f"SELECT MIN({col['name']}), MAX({col['name']}) FROM {self._table_name}"
                    )
                    with self._get_connection() as conn:
                        result = conn.execute(query).fetchone()
                        if result and result[0] is not None and result[1] is not None:
                            column_info.append(f"  Range: {result[0]} to {result[1]}")
                except Exception:
                    pass  # Skip range info if query fails

            # For string/text columns, check if categorical
            elif isinstance(
                col["type"], (sqltypes.String, sqltypes.Text, sqltypes.Enum)
            ):
                try:
                    count_query = text(
                        f"SELECT COUNT(DISTINCT {col['name']}) FROM {self._table_name}"
                    )
                    with self._get_connection() as conn:
                        distinct_count = conn.execute(count_query).scalar()
                        if distinct_count and distinct_count <= 10:
                            values_query = text(
                                f"SELECT DISTINCT {col['name']} FROM {self._table_name} "
                                f"WHERE {col['name']} IS NOT NULL"
                            )
                            values = [
                                str(row[0])
                                for row in conn.execute(values_query).fetchall()
                            ]
                            values_str = ", ".join([f"'{v}'" for v in values])
                            column_info.append(f"  Categorical values: {values_str}")
                except Exception:
                    pass  # Skip categorical info if query fails

            schema.extend(column_info)

        return "\n".join(schema)

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query to execute

        Returns:
            Query results as pandas DataFrame
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(text(query), conn)

    def get_data(self) -> pd.DataFrame:
        """Return the unfiltered data as a DataFrame.

        Returns:
            The complete dataset as a pandas DataFrame
        """
        return self.execute_query(f"SELECT * FROM {self._table_name}")

    def _get_sql_type_name(self, type_: sqltypes.TypeEngine) -> str:
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
