"""Tests for ggsql integration helpers."""

import ggsql
import narwhals.stable.v1 as nw
import polars as pl
from conftest import ggsql_render_works
from querychat._datasource import DataFrameSource
from querychat._ggsql import execute_ggsql, extract_title, spec_to_altair


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


class TestExtractTitle:
    @ggsql_render_works
    def test_extracts_title_from_spec(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2], "y": [3, 4]}))
        ds = DataFrameSource(nw_df, "data")
        spec = execute_ggsql(
            ds, "SELECT * FROM data VISUALISE x, y DRAW point LABEL title => 'My Chart'"
        )
        assert extract_title(spec) == "My Chart"

    @ggsql_render_works
    def test_returns_none_without_title(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2], "y": [3, 4]}))
        ds = DataFrameSource(nw_df, "data")
        spec = execute_ggsql(ds, "SELECT * FROM data VISUALISE x, y DRAW point")
        assert extract_title(spec) is None


class TestSpecToAltair:
    @ggsql_render_works
    def test_produces_altair_chart(self):
        import altair as alt
        import ggsql

        reader = ggsql.DuckDBReader("duckdb://memory")
        df = pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        reader.register("data", df)
        spec = reader.execute("SELECT * FROM data VISUALISE x, y DRAW point")
        chart = spec_to_altair(spec)
        assert isinstance(chart, (alt.Chart, alt.LayerChart, alt.FacetChart))
        result = chart.to_dict()
        assert "$schema" in result
        assert "vega-lite" in result["$schema"]


class TestExecuteGgsql:
    @ggsql_render_works
    def test_full_pipeline(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(ds, "SELECT * FROM test_data VISUALISE x, y DRAW point")
        chart = spec_to_altair(spec)
        result = chart.to_dict()
        assert "$schema" in result

    @ggsql_render_works
    def test_with_filtered_query(self):
        nw_df = nw.from_native(
            pl.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 20, 30, 40, 50]})
        )
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(
            ds, "SELECT * FROM test_data WHERE x > 2 VISUALISE x, y DRAW point"
        )
        assert spec.metadata()["rows"] == 3

    @ggsql_render_works
    def test_spec_has_visual(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2], "y": [3, 4]}))
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(ds, "SELECT * FROM test_data VISUALISE x, y DRAW point")
        assert "VISUALISE" in spec.visual()

    @ggsql_render_works
    def test_with_pandas_dataframe(self):
        import pandas as pd

        nw_df = nw.from_native(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(ds, "SELECT * FROM test_data VISUALISE x, y DRAW point")
        chart = spec_to_altair(spec)
        result = chart.to_dict()
        assert "$schema" in result
