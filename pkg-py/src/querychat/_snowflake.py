"""
Snowflake-specific utilities for semantic view discovery.

This module provides functions for discovering Snowflake Semantic Views,
supporting both SQLAlchemy engines and Ibis backends through a type parameter.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from ibis.backends.sql import SQLBackend
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)

BackendType = Literal["sqlalchemy", "ibis"]


@dataclass
class SemanticViewInfo:
    """Metadata for a Snowflake Semantic View."""

    name: str
    """Fully qualified name (database.schema.view_name)."""

    ddl: str
    """The DDL definition from GET_DDL()."""


def execute_raw_sql(
    query: str,
    backend: Engine | SQLBackend,
    backend_type: BackendType,
) -> list[dict[str, Any]]:
    """
    Execute raw SQL and return results as list of row dicts.

    Parameters
    ----------
    query
        SQL query to execute
    backend
        SQLAlchemy Engine or Ibis SQLBackend
    backend_type
        Type of backend: "sqlalchemy" or "ibis"

    Returns
    -------
    list[dict[str, Any]]
        Query results as list of row dictionaries

    """
    if backend_type == "sqlalchemy":
        from sqlalchemy import text

        with backend.connect() as conn:  # type: ignore[union-attr]
            result = conn.execute(text(query))
            keys = list(result.keys())
            return [dict(zip(keys, row, strict=False)) for row in result.fetchall()]
    else:
        # Ibis backend
        result_table = backend.sql(query)  # type: ignore[union-attr]
        df = result_table.execute()
        return df.to_dict(orient="records")  # type: ignore[return-value]


def discover_semantic_views(
    backend: Engine | SQLBackend,
    backend_type: BackendType,
) -> list[SemanticViewInfo]:
    """
    Discover semantic views in the current schema.

    Parameters
    ----------
    backend
        SQLAlchemy Engine or Ibis SQLBackend
    backend_type
        Type of backend: "sqlalchemy" or "ibis"

    Returns
    -------
    list[SemanticViewInfo]
        List of semantic views with their DDL definitions

    """
    # Check env var for early exit
    if os.environ.get("QUERYCHAT_DISABLE_SEMANTIC_VIEWS"):
        return []

    rows = execute_raw_sql("SHOW SEMANTIC VIEWS", backend, backend_type)

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
        ddl = get_semantic_view_ddl(backend, backend_type, fq_name)
        if ddl:
            views.append(SemanticViewInfo(name=fq_name, ddl=ddl))

    return views


def get_semantic_view_ddl(
    backend: Engine | SQLBackend,
    backend_type: BackendType,
    fq_name: str,
) -> str | None:
    """
    Get DDL for a semantic view.

    Parameters
    ----------
    backend
        SQLAlchemy Engine or Ibis SQLBackend
    backend_type
        Type of backend: "sqlalchemy" or "ibis"
    fq_name
        Fully qualified name (database.schema.view_name)

    Returns
    -------
    str | None
        The DDL text, or None if retrieval failed

    """
    # Escape single quotes to prevent SQL injection
    safe_name = fq_name.replace("'", "''")
    rows = execute_raw_sql(
        f"SELECT GET_DDL('SEMANTIC_VIEW', '{safe_name}')", backend, backend_type
    )
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
