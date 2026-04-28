"""Tests for visualization tool functions."""

import importlib.util

import narwhals.stable.v1 as nw
import polars as pl
import pytest
from querychat._datasource import DataFrameSource
from querychat.tools import tool_visualize
from querychat.types import VisualizeData, VisualizeResult


class TestVizDependencyCheck:
    def test_missing_ggsql_raises_helpful_error(self, monkeypatch):
        """Requesting viz tools without ggsql installed should fail early."""
        real_find_spec = importlib.util.find_spec

        def mock_find_spec(name, *args, **kwargs):
            if name == "ggsql":
                return None
            return real_find_spec(name, *args, **kwargs)

        monkeypatch.setattr(importlib.util, "find_spec", mock_find_spec)

        from querychat._querychat_base import normalize_tools

        with pytest.raises(ImportError, match="pip install querychat\\[viz\\]"):
            normalize_tools(("visualize",), default=None)

    def test_no_error_without_viz_tools(self):
        """Non-viz tool configs should not check for ggsql."""
        from querychat._querychat_base import normalize_tools

        # Should not raise
        normalize_tools(("update", "query"), default=None)
        normalize_tools(None, default=None)

    def test_check_deps_false_skips_check(self, monkeypatch):
        """check_deps=False should skip the dependency check."""
        monkeypatch.setattr(
            importlib.util, "find_spec", lambda name, *a, **kw: None
        )

        from querychat._querychat_base import normalize_tools

        # Should not raise even though find_spec returns None for everything
        result = normalize_tools(("visualize",), default=None, check_deps=False)
        assert result == ("visualize",)


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {
            "x": [1, 2, 3, 4, 5],
            "y": [10, 20, 15, 25, 30],
            "category": ["A", "B", "A", "B", "A"],
        }
    )


@pytest.fixture
def data_source(sample_df):
    nw_df = nw.from_native(sample_df)
    return DataFrameSource(nw_df, "test_data")


class TestToolVisualize:
    def test_creates_tool(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeData):
            callback_data.update(data)

        tool = tool_visualize(data_source, update_fn)
        assert tool.name == "querychat_visualize"

    @pytest.mark.ggsql
    def test_tool_executes_sql_and_renders(self, data_source, monkeypatch):
        callback_data = {}

        def update_fn(data: VisualizeData):
            callback_data.update(data)

        from unittest.mock import MagicMock

        from ipywidgets.widgets.widget import Widget

        monkeypatch.setattr("shinywidgets.register_widget", lambda _widget_id, _chart: None)
        monkeypatch.setattr(
            "shinywidgets.output_widget", lambda _widget_id, **_kwargs: MagicMock()
        )
        # Must be AFTER shinywidgets patches above (importing shinywidgets resets this)
        monkeypatch.setattr(Widget, "_widget_construction_callback", lambda _w: None)

        tool = tool_visualize(data_source, update_fn)
        impl = tool.func

        result = impl(
            ggsql="SELECT x, y FROM test_data WHERE x > 2 VISUALISE x, y DRAW point",
            title="Filtered Scatter",
        )

        assert "ggsql" in callback_data
        assert "title" in callback_data
        assert callback_data["title"] == "Filtered Scatter"

        assert isinstance(result, VisualizeResult)
        display = result.extra["display"]
        assert display.full_screen is True
        assert display.open is True

    @pytest.mark.ggsql
    def test_tool_handles_query_without_visualise(self, data_source):
        callback_data = {}

        def update_fn(data: VisualizeData):
            callback_data.update(data)

        tool = tool_visualize(data_source, update_fn)
        impl = tool.func

        result = impl(ggsql="SELECT x, y FROM test_data", title="No Viz")

        assert result.error is not None
        assert "VISUALISE" in str(result.error)


class TestVisualizeResultContent:
    @pytest.mark.ggsql
    def test_result_value_contains_image(self, data_source, monkeypatch):
        from unittest.mock import MagicMock

        from ipywidgets.widgets.widget import Widget

        monkeypatch.setattr("shinywidgets.register_widget", lambda _id, _w: None)
        monkeypatch.setattr(
            "shinywidgets.output_widget", lambda _id, **_kw: MagicMock()
        )
        monkeypatch.setattr(Widget, "_widget_construction_callback", lambda _w: None)

        callback_data = {}

        def update_fn(data: VisualizeData):
            callback_data.update(data)

        tool = tool_visualize(data_source, update_fn)
        result = tool.func(
            ggsql="SELECT x, y FROM test_data VISUALISE x, y DRAW point",
            title="Test Chart",
        )

        assert isinstance(result, VisualizeResult)
        # value should be a list with [str, image content]
        assert isinstance(result.value, list)
        assert len(result.value) == 2
        assert isinstance(result.value[0], str)
        assert getattr(result.value[1], "content_type", None) == "image_inline"
        assert result.value[1].image_content_type == "image/png"
        # model_format must be "as_is" so chatlas passes the list as
        # multimodal content (not stringified) to the LLM provider
        assert result.model_format == "as_is"

    @pytest.mark.ggsql
    def test_result_text_is_minimal(self, data_source, monkeypatch):
        from unittest.mock import MagicMock

        from ipywidgets.widgets.widget import Widget

        monkeypatch.setattr("shinywidgets.register_widget", lambda _id, _w: None)
        monkeypatch.setattr(
            "shinywidgets.output_widget", lambda _id, **_kw: MagicMock()
        )
        monkeypatch.setattr(Widget, "_widget_construction_callback", lambda _w: None)

        tool = tool_visualize(data_source, lambda _: None)
        result = tool.func(
            ggsql="SELECT x, y FROM test_data VISUALISE x, y DRAW point",
            title="Test Chart",
        )

        text_part = result.value[0]
        assert text_part == "Chart displayed with title 'Test Chart'."
        assert "Test Chart" in text_part

    @pytest.mark.ggsql
    def test_png_failure_falls_back_to_text_only(self, data_source, monkeypatch):
        from unittest.mock import MagicMock

        from ipywidgets.widgets.widget import Widget

        monkeypatch.setattr("shinywidgets.register_widget", lambda _id, _w: None)
        monkeypatch.setattr(
            "shinywidgets.output_widget", lambda _id, **_kw: MagicMock()
        )
        monkeypatch.setattr(Widget, "_widget_construction_callback", lambda _w: None)

        def explode(_chart):
            raise RuntimeError("vl-convert failed")

        monkeypatch.setattr("querychat._viz_tools.render_chart_to_png", explode)

        tool = tool_visualize(data_source, lambda _: None)
        result = tool.func(
            ggsql="SELECT x, y FROM test_data VISUALISE x, y DRAW point",
            title="Test Chart",
        )

        # Should still succeed, just text-only
        assert isinstance(result, VisualizeResult)
        assert isinstance(result.value, str)
        assert result.error is None


class TestRenderChartToPng:
    @pytest.mark.ggsql
    def test_simple_chart_returns_bytes(self):
        import altair as alt

        chart = alt.Chart({"values": [{"x": 1, "y": 2}]}).mark_point().encode(
            x="x:Q", y="y:Q"
        )
        from querychat._viz_tools import render_chart_to_png

        result = render_chart_to_png(chart)
        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes

    @pytest.mark.ggsql
    def test_compound_chart_returns_bytes(self):
        import altair as alt

        chart = (
            alt.Chart({"values": [{"x": 1, "y": 2, "c": "A"}]})
            .mark_point()
            .encode(x="x:Q", y="y:Q")
            .facet("c:N")
        )
        from querychat._viz_tools import render_chart_to_png

        result = render_chart_to_png(chart)
        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"
