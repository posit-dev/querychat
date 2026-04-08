"""Helpers for ggsql integration."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ._utils import to_polars

if TYPE_CHECKING:
    import ggsql

    from ._datasource import DataSource


def execute_ggsql(data_source: DataSource, validated: ggsql.Validated) -> ggsql.Spec:
    """
    Execute a pre-validated ggsql query against a DataSource, returning a Spec.

    Executes the SQL portion through DataSource (preserving database pushdown),
    then feeds the result into a ggsql DuckDBReader to produce a Spec.

    Parameters
    ----------
    data_source
        The querychat DataSource to execute the SQL portion against.
    validated
        A pre-validated ggsql query (from ``ggsql.validate()``).

    Returns
    -------
    ggsql.Spec
        The writer-independent plot specification.

    """
    from ggsql import DuckDBReader

    visual = validated.visual()
    if has_layer_level_source(visual):
        # Short term, querychat only supports visual layers that can be replayed
        # from one final SQL result. Long term, the cleaner fix is likely to use
        # ggsql's native remote-reader execution path (for example via ODBC-backed
        # Readers) instead of reconstructing multi-relation scope here.
        raise ValueError(
            "Layer-specific sources are not currently supported in querychat visual "
            "queries. Rewrite the query so that all layers come from the final SQL "
            "result."
        )

    pl_df = to_polars(data_source.execute_query(validated.sql()))

    reader = DuckDBReader("duckdb://memory")
    table = validated_source_table(validated)

    if table is not None:
        # VISUALISE [mappings] FROM <table> — register data under the
        # referenced table name and execute the visual part directly.
        name = table[1:-1] if table.startswith('"') and table.endswith('"') else table
        reader.register(name, pl_df)
        return reader.execute(visual)
    else:
        # SELECT ... VISUALISE — no FROM in VISUALISE clause, so register
        # under a synthetic name and prepend a SELECT.
        reader.register("_data", pl_df)
        return reader.execute(f"SELECT * FROM _data {visual}")


def validated_source_table(validated: ggsql.Validated) -> str | None:
    """
    Return the top-level ``VISUALISE ... FROM <table>`` source table.

    Prefer ggsql's structured ``Validated.source_table()`` API when available.
    Fall back to parsing the visual clause while querychat still supports older
    ggsql Python bindings that do not expose that method yet.
    """
    source_table = getattr(validated, "source_table", None)
    if callable(source_table):
        return source_table()
    return extract_visualise_table(validated.visual())


def extract_visualise_table(visual: str) -> str | None:
    """
    Extract the table name from ``VISUALISE ... FROM <table>`` if present.

    This is a compatibility fallback for older ggsql Python bindings that do
    not yet expose ``Validated.source_table()``.
    """
    draw_pos = re.search(r"\bDRAW\b", visual, re.IGNORECASE)
    vis_clause = visual[: draw_pos.start()] if draw_pos else visual
    m = re.search(r'\bFROM\s+("[^"]+?"|\S+)', vis_clause, re.IGNORECASE)
    return m.group(1) if m else None


def has_layer_level_source(visual: str) -> bool:
    """
    Return ``True`` when a DRAW clause defines its own ``FROM <source>``.

    Querychat currently replays the VISUALISE portion against a single local
    relation, so layer-specific sources cannot be preserved reliably.
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
