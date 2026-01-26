"""
Snowflake-specific utilities for semantic view discovery.

This module provides a backend-agnostic interface for discovering Snowflake
Semantic Views. It uses a Protocol pattern to abstract SQL execution, allowing
the same discovery logic to work with both SQLAlchemy engines and Ibis backends.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ibis.backends.sql import SQLBackend
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


@dataclass
class SemanticViewInfo:
    """Metadata for a Snowflake Semantic View."""

    name: str
    """Fully qualified name (database.schema.view_name)."""

    ddl: str
    """The DDL definition from GET_DDL()."""


class RawSQLExecutor(Protocol):
    """
    Protocol for executing raw SQL queries.

    This abstraction allows semantic view discovery to work with different
    database backends (SQLAlchemy, Ibis) without knowing the specific API.
    """

    def execute_raw_sql(self, query: str) -> list[dict[str, Any]]:
        """Execute raw SQL and return results as list of row dicts."""
        ...


class SQLAlchemyExecutor:
    """Raw SQL executor for SQLAlchemy engines."""

    def __init__(self, engine: Engine):
        from sqlalchemy import text

        self._engine = engine
        self._text = text

    def execute_raw_sql(self, query: str) -> list[dict[str, Any]]:
        """Execute raw SQL and return results as list of row dicts."""
        with self._engine.connect() as conn:
            result = conn.execute(self._text(query))
            keys = list(result.keys())
            return [dict(zip(keys, row, strict=False)) for row in result.fetchall()]


class SQLAlchemyConnectionExecutor:
    """
    Raw SQL executor for an active SQLAlchemy connection.

    Unlike SQLAlchemyExecutor, this uses an existing connection rather than
    creating a new one. Useful when you need to execute multiple queries
    within the same connection/transaction.
    """

    def __init__(self, conn: Connection):
        from sqlalchemy import text

        self._conn = conn
        self._text = text

    def execute_raw_sql(self, query: str) -> list[dict[str, Any]]:
        """Execute raw SQL and return results as list of row dicts."""
        result = self._conn.execute(self._text(query))
        keys = list(result.keys())
        return [dict(zip(keys, row, strict=False)) for row in result.fetchall()]


class IbisExecutor:
    """Raw SQL executor for Ibis backends."""

    def __init__(self, backend: SQLBackend):
        self._backend = backend

    def execute_raw_sql(self, query: str) -> list[dict[str, Any]]:
        """Execute raw SQL and return results as list of row dicts."""
        # Use backend.sql() to create an ibis table from raw SQL, then execute
        result_table = self._backend.sql(query)
        df = result_table.execute()
        # execute() returns a pandas DataFrame
        return df.to_dict(orient="records")  # type: ignore[call-overload]


def discover_semantic_views(executor: RawSQLExecutor) -> list[SemanticViewInfo]:
    """
    Discover semantic views using any SQL executor.

    Parameters
    ----------
    executor
        An object implementing the RawSQLExecutor protocol

    Returns
    -------
    list[SemanticViewInfo]
        List of semantic views with their DDL definitions

    """
    rows = executor.execute_raw_sql("SHOW SEMANTIC VIEWS")

    if not rows:
        logger.debug("No semantic views found in current schema")
        return []

    views: list[SemanticViewInfo] = []
    for row in rows:
        db = row.get("database_name")
        schema = row.get("schema_name")
        name = row.get("name")

        if not name:
            continue

        fq_name = f"{db}.{schema}.{name}"
        ddl = get_semantic_view_ddl(executor, fq_name)
        if ddl:
            views.append(SemanticViewInfo(name=fq_name, ddl=ddl))

    return views


def get_semantic_view_ddl(executor: RawSQLExecutor, fq_name: str) -> str | None:
    """
    Get DDL for a semantic view.

    Parameters
    ----------
    executor
        An object implementing the RawSQLExecutor protocol
    fq_name
        Fully qualified name (database.schema.view_name)

    Returns
    -------
    str | None
        The DDL text, or None if retrieval failed

    """
    # Escape single quotes to prevent SQL injection
    safe_name = fq_name.replace("'", "''")
    rows = executor.execute_raw_sql(f"SELECT GET_DDL('SEMANTIC_VIEW', '{safe_name}')")
    if rows:
        return str(next(iter(rows[0].values())))
    return None


def format_semantic_views_section(semantic_views: list[SemanticViewInfo]) -> str:
    """
    Format the semantic views section for schema output.

    Parameters
    ----------
    semantic_views
        List of semantic view metadata

    Returns
    -------
    str
        Formatted markdown section describing the semantic views

    """
    lines = [
        "## Snowflake Semantic Views",
        "",
        "This database has Semantic Views available. Semantic Views provide a curated ",
        "layer over raw data with pre-defined metrics, dimensions, and relationships. ",
        "They encode business logic and calculation rules that ensure consistent, ",
        "accurate results.",
        "",
        "**IMPORTANT**: When a Semantic View covers the data you need, prefer it over ",
        "raw table queries to benefit from certified metric definitions.",
        "",
    ]

    for sv in semantic_views:
        lines.append(f"### Semantic View: `{sv.name}`")
        lines.append("")
        lines.append("```sql")
        lines.append(sv.ddl)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


class SemanticViewMixin:
    """
    Mixin providing semantic view support for get_schema().

    This mixin adds semantic view discovery and schema formatting to DataSource
    subclasses. Classes using this mixin must initialize `_semantic_views` in
    their constructor.

    Attributes
    ----------
    _semantic_views : list[SemanticViewInfo]
        List of discovered semantic views (set by subclass)

    """

    _semantic_views: list[SemanticViewInfo]

    def _get_schema_with_semantic_views(self, base_schema: str) -> str:
        """
        Append semantic view section to base schema if views exist.

        Parameters
        ----------
        base_schema
            The base schema string from the parent class

        Returns
        -------
        str
            Schema with semantic views section appended (if any exist)

        """
        if not self._semantic_views:
            return base_schema
        return f"{base_schema}\n\n{format_semantic_views_section(self._semantic_views)}"

    @property
    def has_semantic_views(self) -> bool:
        """Check if semantic views are available."""
        return len(self._semantic_views) > 0

    @property
    def semantic_views(self) -> list[SemanticViewInfo]:
        """Get the list of discovered semantic views."""
        return self._semantic_views
