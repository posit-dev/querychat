from __future__ import annotations

from querychat._dashboard_palette import PaletteItem
from querychat._dashboard_ui import dashboard_drawer_ui, palette_html


class TestDrawerUi:
    def test_skeleton_has_required_hooks(self):
        html = str(dashboard_drawer_ui())
        for hook in (
            "querychat-dash-drawer",
            "querychat-dash-canvas",
            "querychat-dash-palette",
            "querychat-dash-badge",
            "data-qcdash-inputs",
        ):
            assert hook in html


class TestPaletteHtml:
    def test_items_carry_drag_payload(self):
        items = [
            PaletteItem(
                id="viz-0",
                kind="chart",
                title="Trend",
                source="SELECT 1 VISUALISE",
                thumbnail="data:image/png;base64,x",
                preview_html=None,
                on_canvas=True,
            ),
        ]
        html = palette_html(items)
        assert 'data-palette-id="viz-0"' in html
        assert "on-canvas" in html  # used-indicator class
        assert "<img" in html  # thumbnail

    def test_preview_html_injected_raw(self):
        # preview_html is trusted server-rendered HTML and must NOT be escaped.
        items = [
            PaletteItem(
                id="q",
                kind="table",
                title="Top cars",
                source="SELECT 1",
                thumbnail=None,
                preview_html="<table><tbody><tr><td>val</td></tr></tbody></table>",
                on_canvas=False,
            ),
        ]
        assert "<table>" in palette_html(items)

    def test_escapes_titles(self):
        items = [
            PaletteItem(
                id="q",
                kind="table",
                title="<script>x</script>",
                source="SELECT 1",
                thumbnail=None,
                preview_html=None,
                on_canvas=False,
            ),
        ]
        assert "<script>x" not in palette_html(items)
