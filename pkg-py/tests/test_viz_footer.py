"""
Tests for visualization footer (Save dropdown, Show Query).

The footer HTML (containing Save dropdown and Show Query toggle) is built by
_build_viz_footer() and passed as the `footer` parameter to ToolResultDisplay.
shinychat renders this in the card footer area.
"""

from unittest.mock import MagicMock

import narwhals.stable.v1 as nw
import polars as pl
import pytest
from htmltools import TagList, tags
from querychat._datasource import DataFrameSource
from querychat.types import VisualizeQueryResult

FOOTER_SENTINEL = tags.div(
    {"class": "querychat-footer-buttons"},
    tags.div(
        {"class": "querychat-footer-left"},
        tags.button({"class": "querychat-show-query-btn"}, "Show Query"),
    ),
    tags.div(
        {"class": "querychat-footer-right"},
        tags.div(
            {"class": "querychat-save-dropdown"},
            tags.button({"class": "querychat-save-btn"}, "Save"),
        ),
    ),
)


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {"x": [1, 2, 3, 4, 5], "y": [10, 20, 15, 25, 30]}
    )


@pytest.fixture
def data_source(sample_df):
    nw_df = nw.from_native(sample_df)
    return DataFrameSource(nw_df, "test_data")


def _mock_output_widget(widget_id, **kwargs):
    return tags.div(id=widget_id)


@pytest.fixture(autouse=True)
def _patch_deps(monkeypatch):
    monkeypatch.setattr(
        "shinywidgets.register_widget", lambda _widget_id, _chart: None
    )
    monkeypatch.setattr("shinywidgets.output_widget", _mock_output_widget)

    mock_spec = MagicMock()
    mock_spec.metadata.return_value = {"rows": 5, "columns": ["x", "y"]}
    mock_chart = MagicMock()
    mock_chart.properties.return_value = mock_chart

    mock_altair_widget = MagicMock()
    mock_altair_widget.widget = mock_chart
    mock_altair_widget.widget_id = "querychat_viz_test1234"
    mock_altair_widget.is_compound = False

    monkeypatch.setattr(
        "querychat._viz_ggsql.execute_ggsql", lambda _ds, _q: mock_spec
    )
    monkeypatch.setattr(
        "querychat._viz_altair_widget.AltairWidget.from_ggsql",
        staticmethod(lambda _spec: mock_altair_widget),
    )
    monkeypatch.setattr(
        "querychat._viz_tools.build_viz_footer",
        lambda _ggsql, _title, _wid: TagList(FOOTER_SENTINEL),
    )


def _make_viz_result(data_source):
    """Create a VisualizeQueryResult for testing."""
    from querychat.tools import tool_visualize_query

    tool = tool_visualize_query(data_source, lambda _d: None)
    return tool.func(
        ggsql="SELECT x, y FROM test_data VISUALISE x, y DRAW point",
        title="Test Chart",
    )


def _render_footer(display) -> str:
    """Render the footer field of a ToolResultDisplay to an HTML string."""
    rendered = TagList(display.footer).render()
    return rendered["html"]


class TestVizFooter:
    @pytest.mark.ggsql
    def test_save_dropdown_present_in_footer(self, data_source):
        """The save dropdown HTML must be present in the display footer."""
        result = _make_viz_result(data_source)

        assert isinstance(result, VisualizeQueryResult)
        display = result.extra["display"]
        footer_html = _render_footer(display)

        assert "querychat-save-dropdown" in footer_html

    @pytest.mark.ggsql
    def test_show_query_button_present_in_footer(self, data_source):
        """The Show Query toggle must be present in the display footer."""
        result = _make_viz_result(data_source)

        assert isinstance(result, VisualizeQueryResult)
        display = result.extra["display"]
        footer_html = _render_footer(display)

        assert "querychat-show-query-btn" in footer_html


class TestVizJsNoShadowDOM:
    """Verify viz.js doesn't contain dead Shadow DOM workarounds."""

    def test_no_shadow_dom_references(self):
        """viz.js should not reference composedPath, shadowRoot, or deepTarget."""
        from pathlib import Path

        js_path = (
            Path(__file__).parent.parent
            / "src"
            / "querychat"
            / "static"
            / "js"
            / "viz.js"
        )
        js_code = js_path.read_text()

        for pattern in ["composedPath", "shadowRoot", "deepTarget"]:
            assert pattern not in js_code, (
                f"viz.js still references '{pattern}' — shinychat uses light DOM, "
                "so Shadow DOM workarounds should be removed."
            )


class TestVizFooterIcons:
    """Verify Bootstrap icons used in viz footer are defined in _icons.py."""

    def test_download_icon_exists(self):
        from querychat._icons import bs_icon

        html = str(bs_icon("download"))
        assert "svg" in html
        assert "bi-download" in html

    def test_chevron_down_icon_exists(self):
        from querychat._icons import bs_icon

        html = str(bs_icon("chevron-down"))
        assert "svg" in html
        assert "bi-chevron-down" in html

    def test_cls_parameter_injects_class(self):
        from querychat._icons import bs_icon

        html = str(bs_icon("download", cls="querychat-icon"))
        assert "querychat-icon" in html


class TestVizJsUseMutationObserver:
    """Verify viz.js uses MutationObserver instead of setInterval for vega export."""

    def test_uses_mutation_observer(self):
        """TriggerVegaAction should use MutationObserver to watch href changes."""
        from pathlib import Path

        js_path = (
            Path(__file__).parent.parent
            / "src"
            / "querychat"
            / "static"
            / "js"
            / "viz.js"
        )
        js_code = js_path.read_text()

        assert "MutationObserver" in js_code, (
            "viz.js should use MutationObserver to detect when vega-embed "
            "updates the href, instead of polling with setInterval."
        )
        assert "setInterval" not in js_code, (
            "viz.js should not use setInterval for polling — "
            "use MutationObserver instead."
        )
