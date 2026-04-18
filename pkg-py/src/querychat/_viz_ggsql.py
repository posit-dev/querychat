"""
Helpers for executing ggsql queries in querychat.

Architecture overview
---------------------
Querychat executes ggsql queries through two possible paths:

1. **Bridge path** (SQLAlchemySource with known dialect) — A
   ``DataSourceReader`` implements ggsql's reader protocol, routing all SQL
   through the real database. ggsql runs its full pipeline (CTEs, stat
   transforms, layer queries) against the real DB. sqlglot transpiles
   ggsql's ANSI-generated SQL to the target dialect. This path supports
   multi-source layers and avoids pulling large result sets into memory.

2. **Fallback path** (all other DataSource types, or bridge failure) — The
   SQL portion (before VISUALISE) runs on the real database via
   ``DataSource.execute_query()``, then the VISUALISE portion replays
   locally against the SQL result using ``ggsql.DuckDBReader``.

The fallback path requires reconstructing a valid ggsql query from the
split ``sql()`` and ``visual()`` parts. See ``execute_two_phase()`` for
details on the two VISUALISE forms (Form A and Form B).

Limitation of fallback path: layer-specific sources
----------------------------------------------------
ggsql supports per-layer data sources (``DRAW line MAPPING … FROM cte``),
but the fallback path can't support them because the SQL result is a single
DataFrame — CTEs don't survive the DataSource boundary. The bridge path
handles this correctly.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ._utils import to_polars

if TYPE_CHECKING:
    import ggsql

    from ._datasource import DataSource

logger = logging.getLogger(__name__)


def execute_ggsql(
    data_source: DataSource,
    query: str,
    validated: ggsql.Validated,
) -> ggsql.Spec:
    """
    Execute a ggsql query, choosing the bridge or fallback path.

    Parameters
    ----------
    data_source
        The querychat DataSource to execute against.
    query
        The original ggsql query string (needed for the bridge path).
    validated
        A pre-validated ggsql query (from ``ggsql.validate()``).

    Returns
    -------
    ggsql.Spec
        The writer-independent plot specification.

    """
    from ._datasource import SQLAlchemySource
    from ._datasource_reader import SQLGLOT_DIALECTS, DataSourceReader

    if isinstance(data_source, SQLAlchemySource):
        sa_dialect_name = data_source._engine.dialect.name
        dialect = SQLGLOT_DIALECTS.get(sa_dialect_name)
        if dialect is None:
            logger.warning(
                "Unknown SQLAlchemy dialect %r — falling back to two-phase execution. "
                "You can register it via: "
                "from querychat._datasource_reader import register_sqlglot_dialect",
                sa_dialect_name,
            )
        if dialect is not None:
            try:
                with DataSourceReader(data_source._engine, dialect) as reader:
                    import ggsql as _ggsql

                    return _ggsql.execute(query, reader)
            except Exception:
                logger.debug(
                    "DataSourceReader bridge failed, falling back to two-phase",
                    exc_info=True,
                )

    return execute_two_phase(data_source, validated)


def execute_two_phase(
    data_source: DataSource,
    validated: ggsql.Validated,
) -> ggsql.Spec:
    """
    Execute a ggsql query using the two-phase approach (fallback path).

    Phase 1: execute SQL on the real database.
    Phase 2: replay the VISUALISE portion locally in DuckDB.
    """
    from ggsql import DuckDBReader

    visual = validated.visual()
    if has_layer_level_source(visual):
        raise ValueError(
            "Layer-specific sources are not currently supported in querychat visual "
            "queries. Rewrite the query so that all layers come from the final SQL "
            "result."
        )

    pl_df = to_polars(data_source.execute_query(validated.sql()))
    # Snowflake (and some other backends) uppercase unquoted identifiers,
    # but the LLM writes lowercase aliases in the VISUALISE clause.
    # DuckDB is case-insensitive, so lowercasing here lets both match.
    pl_df.columns = [c.lower() for c in pl_df.columns]

    reader = DuckDBReader("duckdb://memory")
    table = extract_visualise_table(visual)

    if table is not None:
        name = table[1:-1] if table.startswith('"') and table.endswith('"') else table
        reader.register(name, pl_df)
        return reader.execute(visual)
    else:
        reader.register("_data", pl_df)
        return reader.execute(f"SELECT * FROM _data {visual}")


def extract_visualise_table(visual: str) -> str | None:
    """
    Extract the table name from ``VISUALISE … FROM <table>`` if present.

    This handles Form B queries where the visual string contains an explicit
    source (e.g., ``VISUALISE FROM sales DRAW …``). We need the table name
    to register the DataFrame under the correct name in local DuckDB.

    Only looks at the portion before the first DRAW clause, since FROM after
    DRAW belongs to layer-level MAPPING (a different concern).

    The ggsql Python bindings don't expose the parsed VISUALISE source, so
    we use a regex. This is fragile in theory (could match FROM inside a
    string literal or comment), but safe in practice because LLM-generated
    VISUALISE clauses are simple and well-structured.
    """
    draw_pos = re.search(r"\bDRAW\b", visual, re.IGNORECASE)
    vis_clause = visual[: draw_pos.start()] if draw_pos else visual
    m = re.search(r'\bFROM\s+("[^"]+?"|\S+)', vis_clause, re.IGNORECASE)
    return m.group(1) if m else None


def has_layer_level_source(visual: str) -> bool:
    """
    Return ``True`` when a DRAW clause defines its own ``FROM <source>``.

    ggsql supports per-layer data sources::

        WITH summary AS (…)
        SELECT * FROM raw_data
        VISUALISE …
        DRAW point                                    -- from global SQL result
        DRAW line MAPPING region AS x, … FROM summary -- from CTE

    Querychat can't support this because we only have the single DataFrame
    from executing validated.sql() on the real database. The CTE was
    evaluated server-side and its result isn't available locally. We detect
    this pattern upfront and raise a clear error rather than letting ggsql
    fail with a confusing "table not found".

    The regex splits the visual string on clause boundaries, then checks
    each DRAW clause for ``MAPPING … FROM <source>``.
    """
    clauses = re.split(
        r"(?=\b(?:DRAW|SCALE|PROJECT|FACET|PLACE|LABEL|THEME)\b)",
        visual,
        flags=re.IGNORECASE,
    )
    for clause in clauses:
        if not re.match(r"^\s*DRAW\b", clause, re.IGNORECASE):
            continue
        if re.search(
            r'\bMAPPING\b[\s\S]*?\bFROM\s+("[^"]+?"|\S+)',
            clause,
            re.IGNORECASE,
        ):
            return True
    return False
