"""
Snowflake-specific utilities for semantic view discovery.

This module provides functions for discovering Snowflake Semantic Views,
supporting both SQLAlchemy engines and Ibis backends via isinstance() checks.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import sqlalchemy

if TYPE_CHECKING:
    from ibis.backends.sql import SQLBackend

logger = logging.getLogger(__name__)


@dataclass
class SemanticViewInfo:
    """Metadata for a Snowflake Semantic View."""

    name: str
    """Fully qualified name (database.schema.view_name)."""

    ddl: str
    """The DDL definition from GET_DDL()."""


def execute_raw_sql(
    query: str,
    backend: sqlalchemy.Engine | SQLBackend,
) -> list[dict[str, Any]]:
    """Execute raw SQL and return results as list of row dicts."""
    if isinstance(backend, sqlalchemy.Engine):
        with backend.connect() as conn:
            result = conn.execute(sqlalchemy.text(query))
            keys = list(result.keys())
            return [dict(zip(keys, row, strict=False)) for row in result.fetchall()]
    else:
        result_table = backend.sql(query)
        df = result_table.execute()
        return df.to_dict(orient="records")  # type: ignore[return-value]


def discover_semantic_views(
    backend: sqlalchemy.Engine | SQLBackend,
) -> list[SemanticViewInfo]:
    """Discover semantic views in the current schema."""
    if os.environ.get("QUERYCHAT_DISABLE_SEMANTIC_VIEWS"):
        return []

    rows = execute_raw_sql("SHOW SEMANTIC VIEWS", backend)

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
        ddl = get_semantic_view_ddl(backend, fq_name)
        if ddl:
            views.append(SemanticViewInfo(name=fq_name, ddl=ddl))

    return views


def get_semantic_view_ddl(
    backend: sqlalchemy.Engine | SQLBackend,
    fq_name: str,
) -> str | None:
    """Get DDL for a semantic view by fully qualified name."""
    safe_name = fq_name.replace("'", "''")
    rows = execute_raw_sql(f"SELECT GET_DDL('SEMANTIC_VIEW', '{safe_name}')", backend)
    if rows:
        return str(next(iter(rows[0].values())))
    return None


def format_semantic_views_section(semantic_views: list[SemanticViewInfo]) -> str:
    """Format the semantic views section for schema output."""
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
