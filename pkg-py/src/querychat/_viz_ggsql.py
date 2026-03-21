"""Helpers for ggsql integration."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ._utils import to_polars

if TYPE_CHECKING:
    import ggsql

    from ._datasource import DataSource


def execute_ggsql(data_source: DataSource, query: str) -> ggsql.Spec:
    """
    Execute a full ggsql query against a DataSource, returning a Spec.

    Uses ggsql.validate() to split SQL from VISUALISE, executes the SQL
    through DataSource (preserving database pushdown), then feeds the result
    into a ggsql DuckDBReader to produce a Spec.

    Parameters
    ----------
    data_source
        The querychat DataSource to execute the SQL portion against.
    query
        A full ggsql query (SQL + VISUALISE).

    Returns
    -------
    ggsql.Spec
        The writer-independent plot specification.

    """
    import ggsql as _ggsql

    validated = _ggsql.validate(query)
    pl_df = to_polars(data_source.execute_query(validated.sql()))

    reader = _ggsql.DuckDBReader("duckdb://memory")
    visual = validated.visual()
    table = extract_visualise_table(visual)

    if table is not None:
        # VISUALISE [mappings] FROM <table> — register data under the
        # referenced table name and execute the visual part directly.
        reader.register(table.strip('"'), pl_df)
        return reader.execute(visual)
    else:
        # SELECT ... VISUALISE — no FROM in VISUALISE clause, so register
        # under a synthetic name and prepend a SELECT.
        reader.register("_data", pl_df)
        return reader.execute(f"SELECT * FROM _data {visual}")


def extract_visualise_table(visual: str) -> str | None:
    """Extract the table name from ``VISUALISE ... FROM <table>`` if present."""
    # Only look at the VISUALISE clause (before the first DRAW) to avoid
    # matching layer-level FROM (e.g., DRAW bar MAPPING ... FROM summary).
    draw_pos = re.search(r"\bDRAW\b", visual, re.IGNORECASE)
    vis_clause = visual[: draw_pos.start()] if draw_pos else visual
    # Matches double-quoted or bare identifiers (the only forms ggsql supports).
    m = re.search(r'\bFROM\s+("[^"]+?"|\S+)', vis_clause, re.IGNORECASE)
    return m.group(1) if m else None
