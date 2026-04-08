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

    import ggsql
    from querychat import _viz_tools

    mock_raw_chart = MagicMock()
    mock_vl_writer = MagicMock()
    mock_vl_writer.render_chart.return_value = mock_raw_chart
    monkeypatch.setattr(ggsql, "VegaLiteWriter", lambda: mock_vl_writer)
    monkeypatch.setattr(
        _viz_tools, "_extract_column_names", lambda _chart: ["x", "y"]
    )
    monkeypatch.setattr(
        _viz_tools, "render_chart_to_png", lambda _chart: b"\x89PNG\r\n\x1a\n"
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


class TestVizPreloadMarkup:
    def test_preload_markup_has_no_inline_script(self):
        from querychat._viz_utils import PRELOAD_WIDGET_ID, preload_viz_deps_ui

        rendered = TagList(preload_viz_deps_ui()).render()
        preload_dep = next(
            dep for dep in rendered["dependencies"] if dep.name == "querychat-viz-preload"
        )

        assert PRELOAD_WIDGET_ID in rendered["html"]
        assert "querychat-viz-preload" in rendered["html"]
        assert "hidden" in rendered["html"]
        assert "<script" not in rendered["html"]
        assert preload_dep.script == [{"src": "js/viz-preload.js"}]
