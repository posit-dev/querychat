"""Helpers for ggsql integration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import narwhals.stable.v1 as nw

if TYPE_CHECKING:
    import ggsql
    import polars as pl
    from narwhals.stable.v1.typing import IntoFrame

    from ._datasource import DataSource


def to_polars(data: IntoFrame) -> pl.DataFrame:
    """Convert any narwhals-compatible frame to a polars DataFrame."""
    nw_df = nw.from_native(data)
    if isinstance(nw_df, nw.LazyFrame):
        nw_df = nw_df.collect()
    return nw_df.to_polars()


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
    reader.register("_data", pl_df)
    return reader.execute(f"SELECT * FROM _data {validated.visual()}")


def spec_to_altair(spec: ggsql.Spec) -> ggsql.AltairChart:
    """Render a ggsql Spec to an Altair chart via VegaLiteWriter."""
    import ggsql as _ggsql

    writer = _ggsql.VegaLiteWriter()
    return writer.render_chart(spec, validate=False)


def extract_title(spec: ggsql.Spec) -> str | None:
    """
    Extract the title from a ggsql Spec's rendered Vega-Lite JSON.

    TODO: Replace with ``spec.title()`` once ggsql exposes this natively.
    """
    import ggsql as _ggsql

    writer = _ggsql.VegaLiteWriter()
    vl: dict[str, object] = json.loads(writer.render(spec))
    title = vl.get("title")
    if isinstance(title, str):
        return title
    if isinstance(title, dict):
        return title.get("text")
    return None
