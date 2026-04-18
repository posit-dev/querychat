"""Tests for ggsql integration helpers."""

import ggsql
import narwhals.stable.v1 as nw
import polars as pl
import pytest
from querychat._datasource import DataFrameSource
from querychat._viz_altair_widget import AltairWidget
from querychat._viz_ggsql import (
    execute_ggsql,
    extract_visualise_table,
    has_layer_level_source,
)


class TestExtractVisualiseTable:
    """Tests for extract_visualise_table() parsing."""

    def test_bare_identifier(self):
        assert extract_visualise_table("VISUALISE x, y FROM mytable DRAW point") == "mytable"

    def test_quoted_identifier(self):
        assert (
            extract_visualise_table('VISUALISE x FROM "my table" DRAW point')
            == '"my table"'
        )

    def test_no_from_returns_none(self):
        assert extract_visualise_table("VISUALISE x, y DRAW point") is None

    def test_ignores_draw_level_from(self):
        visual = "VISUALISE x, y DRAW bar MAPPING z AS fill FROM summary"
        assert extract_visualise_table(visual) is None


class TestHasLayerLevelSource:
    def test_detects_draw_level_from(self):
        visual = "VISUALISE x, y DRAW bar MAPPING z AS fill FROM summary"
        assert has_layer_level_source(visual)

    def test_ignores_visualise_from(self):
        visual = "VISUALISE x, y FROM sales DRAW point MAPPING z AS color"
        assert not has_layer_level_source(visual)

    def test_ignores_scale_from(self):
        visual = "VISUALISE x, y DRAW point MAPPING z AS color SCALE x FROM [0, 10]"
        assert not has_layer_level_source(visual)


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
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = execute_ggsql(ds, query, ggsql.validate(query))
        altair_widget = AltairWidget.from_ggsql(spec)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result

    @pytest.mark.ggsql
    def test_with_filtered_query(self):
        nw_df = nw.from_native(
            pl.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 20, 30, 40, 50]})
        )
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data WHERE x > 2 VISUALISE x, y DRAW point"
        spec = execute_ggsql(ds, query, ggsql.validate(query))
        assert spec.metadata()["rows"] == 3

    @pytest.mark.ggsql
    def test_spec_has_visual(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2], "y": [3, 4]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = execute_ggsql(ds, query, ggsql.validate(query))
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_visualise_from_path(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "VISUALISE x, y FROM test_data DRAW point"
        spec = execute_ggsql(ds, query, ggsql.validate(query))
        assert spec.metadata()["rows"] == 3
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_with_pandas_dataframe(self):
        import pandas as pd

        nw_df = nw.from_native(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = execute_ggsql(ds, query, ggsql.validate(query))
        altair_widget = AltairWidget.from_ggsql(spec)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result

    @pytest.mark.ggsql
    def test_rejects_layer_level_from_sources_with_clear_error(self):
        nw_df = nw.from_native(
            pl.DataFrame(
                {
                    "date": ["2024-01", "2024-01", "2024-02", "2024-02"],
                    "region": ["north", "south", "north", "south"],
                    "amount": [10, 20, 30, 40],
                }
            )
        )
        ds = DataFrameSource(nw_df, "sales")
        query = """
        WITH summary AS (
            SELECT region, SUM(amount) AS total
            FROM sales
            GROUP BY region
        )
        SELECT *
        FROM sales
        VISUALISE date AS x, amount AS y
        DRAW line
        DRAW bar MAPPING region AS x, total AS y FROM summary
        """

        with pytest.raises(
            ValueError,
            match="Layer-specific sources are not currently supported",
        ):
            execute_ggsql(ds, query, ggsql.validate(query))

    @pytest.mark.ggsql
    def test_supports_single_relation_raw_plus_summary_overlay(self):
        nw_df = nw.from_native(
            pl.DataFrame(
                {
                    "x": [1, 1, 2, 2],
                    "y": [10, 20, 30, 40],
                    "category": ["a", "b", "a", "b"],
                }
            )
        )
        ds = DataFrameSource(nw_df, "sales")
        query = """
        WITH raw AS (
            SELECT
                x,
                y,
                category,
                'raw' AS layer_type
            FROM sales
        ),
        summary AS (
            SELECT
                x,
                AVG(y) AS y,
                category,
                'summary' AS layer_type
            FROM sales
            GROUP BY x, category
        ),
        combined AS (
            SELECT * FROM raw
            UNION ALL
            SELECT * FROM summary
        )
        SELECT *
        FROM combined
        VISUALISE x AS x, y AS y
        DRAW point MAPPING category AS color FILTER layer_type = 'raw'
        DRAW line MAPPING category AS color FILTER layer_type = 'summary'
        """

        spec = execute_ggsql(ds, query, ggsql.validate(query))
        assert spec.metadata()["rows"] == 4
        assert "VISUALISE" in spec.visual()
