"""Tests for ggsql integration helpers."""

import ggsql
import narwhals.stable.v1 as nw
import polars as pl
import pytest
from querychat._datasource import DataFrameSource
from querychat._viz_altair_widget import AltairWidget
from querychat._viz_ggsql import caching_reader, execute_ggsql


class TestGgsqlValidate:
    """Tests for ggsql.validate() usage (split SQL and VISUALISE)."""

    def test_accepts_from_before_visualise(self):
        query = "FROM data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        assert validated.valid()
        assert validated.has_visual()
        assert validated.sql() == "SELECT * FROM data"
        assert validated.visual() == "VISUALISE x, y DRAW point"

    def test_accepts_from_before_visualise_for_test_data(self):
        query = "FROM test_data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        assert validated.valid()
        assert validated.has_visual()
        assert validated.sql() == "SELECT * FROM test_data"
        assert validated.visual() == "VISUALISE x, y DRAW point"

    def test_reports_upstream_error_for_expression_in_visualise(self):
        query = (
            "SELECT CAST(x AS DOUBLE) AS x2 "
            "FROM data "
            "VISUALISE CAST(x2 AS DOUBLE) AS x "
            "DRAW point"
        )
        validated = ggsql.validate(query)
        assert not validated.valid()
        messages = [error["message"] for error in validated.errors()]
        assert any(
            "VISUALISE clause was not recognized" in message
            and "column names only" in message
            for message in messages
        )

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
        spec = execute_ggsql(caching_reader(ds), query)
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
        spec = execute_ggsql(caching_reader(ds), query)
        assert spec.metadata()["rows"] == 3

    @pytest.mark.ggsql
    def test_spec_has_visual(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2], "y": [3, 4]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = execute_ggsql(caching_reader(ds), query)
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_visualise_from_path(self):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "VISUALISE x, y FROM test_data DRAW point"
        spec = execute_ggsql(caching_reader(ds), query)
        assert spec.metadata()["rows"] == 3
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_with_pandas_dataframe(self):
        import pandas as pd

        nw_df = nw.from_native(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        spec = execute_ggsql(caching_reader(ds), query)
        altair_widget = AltairWidget.from_ggsql(spec)
        result = altair_widget.widget.chart.to_dict()
        assert "$schema" in result

    @pytest.mark.ggsql
    def test_supports_uppercase_column_references_without_renaming(self):
        nw_df = nw.from_native(
            pl.DataFrame(
                {
                    "ROOM_TYPE": ["Entire home", "Private room"],
                    "listings": [10, 20],
                }
            )
        )
        ds = DataFrameSource(nw_df, "upper_table")
        query = (
            "SELECT ROOM_TYPE, listings FROM upper_table "
            "VISUALISE ROOM_TYPE AS x, listings AS y "
            "DRAW bar"
        )
        spec = execute_ggsql(caching_reader(ds), query)
        assert "VISUALISE" in spec.visual()

    @pytest.mark.ggsql
    def test_supports_layer_level_from_sources(self):
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

        # Previously raised "Layer-specific sources are not currently
        # supported"; CachingReader stages each layer source through its
        # cache, so the query now runs end to end.
        spec = execute_ggsql(caching_reader(ds), query)
        assert spec is not None
        assert "VISUALISE" in spec.visual()

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

        spec = execute_ggsql(caching_reader(ds), query)
        assert spec.metadata()["rows"] == 4
        assert "VISUALISE" in spec.visual()


class TestCachingBehavior:
    """CachingReader shares memoized source reads across viz executions."""

    @pytest.mark.ggsql
    def test_identical_queries_share_source_reads(self, monkeypatch):
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")

        calls = 0
        original = ds.execute_query

        def counting(query):
            nonlocal calls
            calls += 1
            return original(query)

        monkeypatch.setattr(ds, "execute_query", counting)

        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        reader = caching_reader(ds)
        execute_ggsql(reader, query)
        execute_ggsql(reader, query)
        assert calls == 1

    @pytest.mark.ggsql
    def test_independent_readers_do_not_share_memo(self, monkeypatch):
        """Readers own their caches; nothing is shared implicitly."""
        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")

        calls = 0
        original = ds.execute_query

        def counting(query):
            nonlocal calls
            calls += 1
            return original(query)

        monkeypatch.setattr(ds, "execute_query", counting)

        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        execute_ggsql(caching_reader(ds), query)
        execute_ggsql(caching_reader(ds), query)
        assert calls == 2
