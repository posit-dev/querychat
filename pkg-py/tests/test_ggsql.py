"""Tests for ggsql integration helpers."""

import ggsql
import polars as pl
import pytest
from querychat._ggsql import extract_title


def _ggsql_render_works() -> bool:
    """Check if ggsql.render_altair() is functional (build can be broken in some envs)."""
    try:
        import ggsql

        df = pl.DataFrame({"x": [1, 2], "y": [3, 4]})
        result = ggsql.render_altair(df, "VISUALISE x, y DRAW point")
        spec = result.to_dict()
        return "$schema" in spec
    except (ValueError, ImportError):
        return False


ggsql_render_works = pytest.mark.skipif(
    not _ggsql_render_works(),
    reason="ggsql.render_altair() not functional (build environment issue)",
)


class TestGgsqlSplitQuery:
    """Tests for ggsql.split_query() usage."""

    def test_splits_query_with_visualise(self):
        query = "SELECT x, y FROM data VISUALISE x, y DRAW point"
        sql, viz = ggsql.split_query(query)
        assert sql == "SELECT x, y FROM data"
        assert viz == "VISUALISE x, y DRAW point"

    def test_returns_empty_viz_without_visualise(self):
        query = "SELECT x, y FROM data"
        sql, viz = ggsql.split_query(query)
        assert sql == "SELECT x, y FROM data"
        assert viz == ""

    def test_handles_complex_query(self):
        query = """
        SELECT date, SUM(revenue) as total
        FROM sales
        GROUP BY date
        VISUALISE date AS x, total AS y
        DRAW line
        LABEL title => 'Revenue Over Time'
        """
        sql, viz = ggsql.split_query(query)
        assert "SELECT date, SUM(revenue)" in sql
        assert "GROUP BY date" in sql
        assert "VISUALISE date AS x" in viz
        assert "LABEL title" in viz


class TestGgsqlRenderAltair:
    @ggsql_render_works
    def test_renders_simple_scatter(self):
        import ggsql

        df = pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        viz_spec = "VISUALISE x, y DRAW point"
        chart = ggsql.render_altair(df, viz_spec)
        result = chart.to_dict()
        assert "$schema" in result
        assert "vega-lite" in result["$schema"]
        assert "layer" in result

    @ggsql_render_works
    def test_returns_altair_chart(self):
        import altair as alt
        import ggsql

        df = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        viz_spec = "VISUALISE a AS x, b AS y DRAW line"
        chart = ggsql.render_altair(df, viz_spec)
        # ggsql returns LayerChart or other chart types
        assert isinstance(chart, (alt.Chart, alt.LayerChart, alt.FacetChart))
        result = chart.to_dict()
        assert result["$schema"] == "https://vega.github.io/schema/vega-lite/v6.json"

    @ggsql_render_works
    def test_renders_pandas_dataframe(self):
        import ggsql
        import pandas as pd

        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        viz_spec = "VISUALISE x, y DRAW point"
        chart = ggsql.render_altair(df, viz_spec)
        result = chart.to_dict()
        assert "$schema" in result
        assert "vega-lite" in result["$schema"]
        assert "layer" in result


class TestExtractTitle:
    def test_extracts_title_from_label(self):
        viz_spec = "VISUALISE x, y DRAW point LABEL title => 'My Chart'"
        title = extract_title(viz_spec)
        assert title == "My Chart"

    def test_returns_none_without_title(self):
        viz_spec = "VISUALISE x, y DRAW point"
        title = extract_title(viz_spec)
        assert title is None

    def test_extracts_title_with_double_quotes(self):
        viz_spec = 'VISUALISE x, y DRAW point LABEL title => "Double Quoted"'
        title = extract_title(viz_spec)
        assert title == "Double Quoted"
