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

    pl_df = to_polars(data_source.execute_query(validated.sql()))

    reader = DuckDBReader("duckdb://memory")
    visual = validated.visual()
    table = extract_visualise_table(visual)

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


def extract_visualise_table(visual: str) -> str | None:
    """
    Extract the table name from ``VISUALISE ... FROM <table>`` if present.

    This regex reimplements part of ggsql's parser because the Python bindings
    don't expose the parsed table name. Internally, ggsql stores it as
    ``Plot.source: Option<DataSource>`` (see ``ggsql/src/plot/types.rs``).
    If ggsql ever exposes a ``source_table()`` or ``visual_table()`` method
    on ``Validated`` or ``Spec``, this function should be replaced.
    """
    # Only look at the VISUALISE clause (before the first DRAW) to avoid
    # matching layer-level FROM (e.g., DRAW bar MAPPING ... FROM summary).
    draw_pos = re.search(r"\bDRAW\b", visual, re.IGNORECASE)
    vis_clause = visual[: draw_pos.start()] if draw_pos else visual
    # Matches double-quoted or bare identifiers (the only forms ggsql supports).
    m = re.search(r'\bFROM\s+("[^"]+?"|\S+)', vis_clause, re.IGNORECASE)
    return m.group(1) if m else None
