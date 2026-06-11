from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
import pandas as pd
import pytest
from querychat._dashboard_tools import (
    tool_canvas_arrange,
    tool_canvas_remove_card,
    tool_canvas_set_cards,
)
from querychat._datasource import DataFrameSource
from querychat._tool_names import (
    TOOL_CANVAS_ARRANGE,
    TOOL_CANVAS_REMOVE_CARD,
    TOOL_CANVAS_SET_CARDS,
)

if TYPE_CHECKING:
    from querychat._dashboard_state import CardSpec, Placement


@pytest.fixture
def source() -> DataFrameSource:
    df = pd.DataFrame({"mpg": [21.0, 22.8], "cyl": [6, 4]})
    return DataFrameSource(nw.from_native(df), "mtcars")


class TestSetCards:
    def test_valid_cards_invoke_callback_and_succeed(self, source):
        received: list[list[CardSpec]] = []
        tool = tool_canvas_set_cards(source, lambda cards: received.append(cards))
        result = tool.func(
            cards=[
                {
                    "name": "avg",
                    "type": "value_box",
                    "title": "Avg MPG",
                    "sql": "SELECT AVG(mpg) FROM mtcars",
                }
            ]
        )
        assert result.error is None
        assert len(received) == 1
        assert received[0][0].name == "avg"

    def test_invalid_card_is_all_or_nothing(self, source):
        received: list[list[CardSpec]] = []
        tool = tool_canvas_set_cards(source, lambda cards: received.append(cards))
        result = tool.func(
            cards=[
                {"name": "ok", "type": "markdown", "title": "t", "text": "hi"},
                {"name": "bad", "type": "table", "title": "t", "sql": "SELECT x FROM nope"},
            ]
        )
        assert result.error is not None
        assert received == []  # nothing applied

    def test_tool_name_and_description(self, source):
        tool = tool_canvas_set_cards(source, lambda cards: None)
        assert tool.name == TOOL_CANVAS_SET_CARDS
        assert "12-column" in (tool.func.__doc__ or "")


class TestArrange:
    def test_placements_forwarded(self):
        received: list[list[Placement]] = []
        tool = tool_canvas_arrange(lambda p: received.append(p))
        result = tool.func(placements=[{"name": "a", "x": 0, "y": 0, "w": 6, "h": 3}])
        assert result.error is None
        assert received[0][0].name == "a"

    def test_callback_keyerror_becomes_tool_error(self):
        def boom(placements):
            raise KeyError("nope")

        tool = tool_canvas_arrange(boom)
        result = tool.func(placements=[{"name": "nope", "x": 0, "y": 0, "w": 1, "h": 1}])
        assert result.error is not None
        assert tool.name == TOOL_CANVAS_ARRANGE

    def test_invalid_placement_rejected(self):
        tool = tool_canvas_arrange(lambda p: None)
        result = tool.func(placements=[{"name": "a", "x": 99, "y": 0, "w": 1, "h": 1}])
        assert result.error is not None


class TestRemoveCard:
    def test_remove_forwarded(self):
        received: list[str] = []
        tool = tool_canvas_remove_card(lambda name: received.append(name))
        result = tool.func(name="trend")
        assert result.error is None
        assert received == ["trend"]
        assert tool.name == TOOL_CANVAS_REMOVE_CARD
