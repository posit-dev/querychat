from __future__ import annotations

from typing import Protocol
import pandas as pd
import duckdb
import sqlite3
import narwhals as nw


class DataSource(Protocol):
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


class SQLiteSource:
    """A DataSource implementation that wraps a SQLite connection."""

    def __init__(self, conn: sqlite3.Connection, table_name: str):
        """Initialize with a SQLite connection.

        Args:
            conn: SQLite database connection
        """
        self._conn = conn
        self._table_name = table_name

    def get_schema(self) -> str:
        """Generate schema information from SQLite table.

        Returns:
            String describing the schema
        """
        # Get column info
        cursor = self._conn.execute(f"PRAGMA table_info({self._table_name})")
        columns = cursor.fetchall()

        schema = [f"Table: {self._table_name}", "Columns:"]

        for col in columns:
            # col format: (cid, name, type, notnull, dflt_value, pk)
            column_info = [f"- {col[1]} ({col[2].upper()})"]

            # For numeric columns, try to get range
            if col[2].upper() in ["INTEGER", "FLOAT", "REAL", "NUMERIC"]:
                try:
                    cursor = self._conn.execute(
                        f"SELECT MIN({col[1]}), MAX({col[1]}) FROM {self._table_name}"
                    )
                    min_val, max_val = cursor.fetchone()
                    if min_val is not None and max_val is not None:
                        column_info.append(f"  Range: {min_val} to {max_val}")
                except sqlite3.Error:
                    pass  # Skip range info if query fails

            # For text columns, check if categorical (limited distinct values)
            elif col[2].upper() == "TEXT":
                try:
                    cursor = self._conn.execute(
                        f"SELECT COUNT(DISTINCT {col[1]}) FROM {self._table_name}"
                    )
                    distinct_count = cursor.fetchone()[0]
                    if distinct_count <= 10:  # Use fixed threshold for simplicity
                        cursor = self._conn.execute(
                            f"SELECT DISTINCT {col[1]} FROM {self._table_name} "
                            f"WHERE {col[1]} IS NOT NULL"
                        )
                        values = [str(row[0]) for row in cursor.fetchall()]
                        values_str = ", ".join([f"'{v}'" for v in values])
                        column_info.append(f"  Categorical values: {values_str}")
                except sqlite3.Error:
                    pass  # Skip categorical info if query fails

            schema.extend(column_info)

        return "\n".join(schema)

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute query using SQLite.

        Args:
            query: SQL query to execute

        Returns:
            Query results as pandas DataFrame
        """
        return pd.read_sql_query(query, self._conn)

    def get_data(self) -> pd.DataFrame:
        """Return the unfiltered data as a DataFrame.

        Returns:
            The complete dataset as a pandas DataFrame
        """
        return pd.read_sql_query(f"SELECT * FROM {self._table_name}", self._conn)
