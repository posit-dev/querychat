from __future__ import annotations

import narwhals as nw
import pandas as pd
import pytest
from querychat._dashboard_autogen import (
    AutogenResult,
    apply_autogen_result,
    format_session_results,
)
from querychat._dashboard_palette import PaletteItem
from querychat._dashboard_state import CardLayout, CardSpec
from querychat._datasource import DataFrameSource


@pytest.fixture
def source() -> DataFrameSource:
    df = pd.DataFrame({"mpg": [21.0, 22.8], "cyl": [6, 4]})
    return DataFrameSource(nw.from_native(df), "mtcars")


class TestFormatSessionResults:
    def test_empty(self):
        assert "none yet" in format_session_results([])

    def test_lists_items_with_source(self):
        items = [
            PaletteItem(id="q", kind="table", title="Top cars",
                        source="SELECT 1", thumbnail=None,
                        preview_html=None, on_canvas=False),
        ]
        out = format_session_results(items)
        assert "Top cars" in out
        assert "SELECT 1" in out


class TestApplyAutogenResult:
    def test_valid_cards_become_spec(self, source):
        result = AutogenResult(
            title="Cars overview",
            cards=[
                CardSpec(name="avg", type="value_box", title="Avg MPG",
                         sql="SELECT AVG(mpg) FROM mtcars",
                         layout=CardLayout(x=0, y=0, w=4, h=2)),
            ],
        )
        spec = apply_autogen_result(source, result)
        assert spec.title == "Cars overview"
        assert len(spec.cards) == 1

    def test_invalid_cards_dropped_not_fatal(self, source):
        result = AutogenResult(
            title="t",
            cards=[
                CardSpec(name="ok", type="markdown", title="t", text="hi",
                         layout=CardLayout(x=0, y=0, w=12, h=2)),
                CardSpec(name="bad", type="table", title="t",
                         sql="SELECT x FROM nope",
                         layout=CardLayout(x=0, y=2, w=12, h=4)),
            ],
        )
        spec = apply_autogen_result(source, result)
        assert [c.name for c in spec.cards] == ["ok"]

    def test_cards_without_layout_get_auto_placed(self, source):
        result = AutogenResult(
            title="t",
            cards=[CardSpec(name="m", type="markdown", title="t", text="x")],
        )
        spec = apply_autogen_result(source, result)
        assert spec.cards[0].layout is not None
