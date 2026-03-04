"""Tests for ggsql integration helpers."""

import ggsql
import polars as pl
from conftest import ggsql_render_works
from querychat.tools import _extract_title as extract_title


class TestGgsqlValidate:
    """Tests for ggsql.validate() usage (split SQL and VISUALISE)."""

    def test_splits_query_with_visualise(self):
        query = "SELECT x, y FROM data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        assert validated.sql() == "SELECT x, y FROM data"
        assert validated.visual() == "VISUALISE x, y DRAW point"
        assert validated.has_visual()

    def test_returns_empty_viz_without_visualise(self):
        query = "SELECT x, y FROM data"
        validated = ggsql.validate(query)
        assert validated.sql() == "SELECT x, y FROM data"
        assert validated.visual() == ""
        assert not validated.has_visual()

    def test_handles_complex_query(self):
        query = """
        SELECT date, SUM(revenue) as total
        FROM sales
        GROUP BY date
        VISUALISE date AS x, total AS y
        DRAW line
        LABEL title => 'Revenue Over Time'
        """
        validated = ggsql.validate(query)
        assert "SELECT date, SUM(revenue)" in validated.sql()
        assert "GROUP BY date" in validated.sql()
        assert "VISUALISE date AS x" in validated.visual()
        assert "LABEL title" in validated.visual()


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
