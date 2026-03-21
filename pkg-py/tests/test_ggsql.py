"""Tests for ggsql integration helpers."""

import ggsql
import narwhals.stable.v1 as nw
import polars as pl
import pytest
from querychat._datasource import DataFrameSource
from querychat._viz_altair_widget import AltairWidget
from querychat._viz_ggsql import execute_ggsql


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



@pytest.fixture(autouse=True)
def _allow_widget_outside_session(monkeypatch):
    """Allow JupyterChart (an ipywidget) to be constructed without a Shiny session."""
    from ipywidgets.widgets.widget import Widget

    monkeypatch.setattr(Widget, "_widget_construction_callback", lambda _w: None)


class TestAltairWidget:
    @pytest.mark.ggsql
    def test_produces_jupyter_chart(self):
        import altair as alt
        import ggsql

        reader = ggsql.DuckDBReader("duckdb://memory")
        df = pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        reader.register("data", df)
        spec = reader.execute("SELECT * FROM data VISUALISE x, y DRAW point")
        altair_widget = AltairWidget.from_ggsql(spec)
        assert isinstance(altair_widget.widget, alt.JupyterChart)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result
        assert "vega-lite" in result["$schema"]


class TestExecuteGgsql:
    @pytest.mark.ggsql
    def test_full_pipeline(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(ds, "SELECT * FROM test_data VISUALISE x, y DRAW point")
        altair_widget = AltairWidget.from_ggsql(spec)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result

    @pytest.mark.ggsql
    def test_with_filtered_query(self):
        nw_df = nw.from_native(
            pl.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 20, 30, 40, 50]})
        )
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(
            ds, "SELECT * FROM test_data WHERE x > 2 VISUALISE x, y DRAW point"
        )
        assert spec.metadata()["rows"] == 3

    @pytest.mark.ggsql
    def test_spec_has_visual(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2], "y": [3, 4]}))
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(ds, "SELECT * FROM test_data VISUALISE x, y DRAW point")
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_with_pandas_dataframe(self):
        import pandas as pd

        nw_df = nw.from_native(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        spec = execute_ggsql(ds, "SELECT * FROM test_data VISUALISE x, y DRAW point")
        altair_widget = AltairWidget.from_ggsql(spec)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result
