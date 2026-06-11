from __future__ import annotations

from querychat._dashboard_context import build_canvas_context, render_grid_ascii
from querychat._dashboard_state import CardLayout, CardSpec, DashboardSpec


def spec_with_two_cards() -> DashboardSpec:
    return DashboardSpec(
        title="Demo",
        cards=[
            CardSpec(
                name="kpi", type="value_box", title="Avg MPG",
                sql="SELECT AVG(mpg) FROM mtcars",
                layout=CardLayout(x=0, y=0, w=4, h=2),
            ),
            CardSpec(
                name="trend", type="chart", title="Trend",
                ggsql="SELECT 1 VISUALISE",
                layout=CardLayout(x=4, y=0, w=8, h=2),
            ),
            CardSpec(  # hidden card: not in the ascii grid
                name="hidden", type="markdown", title="", text="x",
            ),
        ],
    )


class TestRenderGridAscii:
    def test_empty_spec(self):
        assert render_grid_ascii(DashboardSpec()) == "(canvas is empty)"

    def test_cards_marked_by_letter_with_legend(self):
        out = render_grid_ascii(spec_with_two_cards())
        lines = out.splitlines()
        # 12 columns wide, rows = max(y+h) = 2
        grid_lines = [ln for ln in lines if set(ln) <= set("AB.")]
        assert len(grid_lines) == 2
        assert grid_lines[0] == "AAAABBBBBBBB"
        assert "A = kpi (value_box, 4x2)" in out
        assert "B = trend (chart, 8x2)" in out

    def test_hidden_cards_not_in_grid(self):
        out = render_grid_ascii(spec_with_two_cards())
        assert "hidden" not in out


class TestBuildCanvasContext:
    def test_contains_json_ascii_and_hidden_list(self):
        ctx = build_canvas_context(spec_with_two_cards())
        assert "AAAABBBBBBBB" in ctx
        assert '"name": "kpi"' in ctx
        assert "hidden" in ctx  # off-canvas cards listed so LLM can restore them
        assert ctx.startswith("<dashboard-canvas-state>")
        assert ctx.rstrip().endswith("</dashboard-canvas-state>")
