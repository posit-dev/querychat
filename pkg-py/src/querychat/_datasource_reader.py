"""DataSourceReader bridge: routes ggsql's reader protocol through a real database."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

import polars as pl
import sqlglot
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger(__name__)

SQLGLOT_DIALECTS: dict[str, str] = {
    # Built-in SQLAlchemy dialects
    "postgresql": "postgres",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "mssql": "tsql",
    "oracle": "oracle",
    # Third-party SQLAlchemy dialects (dialect name verified via engine.dialect.name)
    "duckdb": "duckdb",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
    "redshift": "redshift",
    "trino": "trino",
    "databricks": "databricks",
    "clickhousedb": "clickhouse",  # clickhouse-connect
    "clickhouse": "clickhouse",  # clickhouse-sqlalchemy
    "awsathena": "athena",  # PyAthena
    "teradatasql": "teradata",  # teradatasqlalchemy
    "exasol": "exasol",
    "doris": "doris",
    "singlestoredb": "singlestore",
    "risingwave": "risingwave",
    "druid": "druid",
    "hive": "hive",  # PyHive; also covers Spark via hive://
    "presto": "presto",
}


def register_sqlglot_dialect(sqlalchemy_name: str, sqlglot_name: str) -> None:
    """
    Register a custom SQLAlchemy dialect name to sqlglot dialect mapping.

    Use this if your database's SQLAlchemy driver reports a ``dialect.name``
    that isn't in the built-in mapping.

    Parameters
    ----------
    sqlalchemy_name
        The value of ``engine.dialect.name`` for your database.
    sqlglot_name
        The corresponding sqlglot dialect identifier (see
        ``sqlglot.dialects.dialect.Dialect.classes`` for valid names).

    """
    SQLGLOT_DIALECTS[sqlalchemy_name] = sqlglot_name


def transpile_sql(sql: str, dialect: str) -> str:
    """Transpile generic SQL to a target dialect using sqlglot."""
    results = sqlglot.transpile(sql, read="", write=dialect)
    return results[0]


class DataSourceReader:
    """
    ggsql reader protocol implementation that routes SQL through a real database.

    Implements execute_sql(), register(), and unregister() as expected by
    ggsql's PyReaderBridge.
    """

    def __init__(self, engine: Engine, dialect: str):
        self._engine = engine
        self._dialect = dialect
        self._conn: Connection | None = None
        self._registered: list[str] = []

    def __enter__(self):
        self._conn = self._engine.connect()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool:
        if self._conn is not None:
            try:
                for name in self._registered:
                    with contextlib.suppress(Exception):
                        self._conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
                self._conn.commit()
            finally:
                self._conn.close()
                self._conn = None
        self._registered.clear()
        return False

    def execute_sql(self, sql: str) -> pl.DataFrame:
        if self._conn is None:
            raise RuntimeError("DataSourceReader must be used as a context manager")
        transpiled = transpile_sql(sql, self._dialect)
        result = self._conn.execute(text(transpiled))
        rows = result.fetchall()
        columns = list(result.keys())
        if not rows:
            return pl.DataFrame(schema=dict.fromkeys(columns, pl.Utf8))
        data = {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        return pl.DataFrame(data)

    def register(self, name: str, df: pl.DataFrame, replace: bool = True) -> None:  # noqa: FBT001, FBT002
        if self._conn is None:
            raise RuntimeError("DataSourceReader must be used as a context manager")
        if replace:
            self._conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
            if name in self._registered:
                self._registered.remove(name)

        col_defs = ", ".join(
            f"{col} {polars_to_sql_type(dtype)}"
            for col, dtype in zip(df.columns, df.dtypes, strict=True)
        )
        create_sql = f"CREATE TEMPORARY TABLE {name} ({col_defs})"
        transpiled_create = transpile_sql(create_sql, self._dialect)
        self._conn.execute(text(transpiled_create))
        self._registered.append(name)

        if len(df) > 0:
            placeholders = ", ".join(f":{col}" for col in df.columns)
            insert_sql = f"INSERT INTO {name} VALUES ({placeholders})"
            rows = df.to_dicts()
            self._conn.execute(text(insert_sql), rows)

        self._conn.commit()

    def unregister(self, name: str) -> None:
        if self._conn is None:
            raise RuntimeError("DataSourceReader must be used as a context manager")
        self._conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
        self._conn.commit()
        if name in self._registered:
            self._registered.remove(name)


def polars_to_sql_type(dtype: pl.DataType) -> str:
    """Map polars dtypes to generic SQL types for CREATE TABLE."""
    if dtype.is_integer():
        return "INTEGER"
    if dtype.is_float():
        return "REAL"
    if dtype == pl.Boolean:
        return "BOOLEAN"
    if dtype == pl.Date:
        return "DATE"
    if dtype in (pl.Datetime, pl.Duration):
        return "TIMESTAMP"
    return "TEXT"
