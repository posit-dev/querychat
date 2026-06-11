from __future__ import annotations

import pytest
from pydantic import ValidationError
from querychat._dashboard_state import (
    CardLayout,
    CardSpec,
    DashboardSpec,
    Placement,
)


def chart_card(name: str = "trend", **kwargs) -> CardSpec:
    kwargs.setdefault("ggsql", "SELECT x, y FROM t VISUALISE x AS x, y AS y DRAW line")
    return CardSpec(name=name, type="chart", title="Trend", **kwargs)


class TestCardSpec:
    def test_chart_requires_ggsql(self):
        with pytest.raises(ValidationError, match="ggsql"):
            CardSpec(name="c", type="chart", title="t")

    def test_table_requires_sql(self):
        with pytest.raises(ValidationError, match="sql"):
            CardSpec(name="c", type="table", title="t")

    def test_value_box_requires_sql(self):
        with pytest.raises(ValidationError, match="sql"):
            CardSpec(name="c", type="value_box", title="t")

    def test_markdown_requires_text(self):
        with pytest.raises(ValidationError, match="text"):
            CardSpec(name="c", type="markdown", title="t")

    def test_name_must_be_slug(self):
        with pytest.raises(ValidationError):
            CardSpec(name="Bad Name!", type="markdown", title="t", text="hi")

    def test_source_property(self):
        assert chart_card().source.startswith("SELECT")
        md = CardSpec(name="m", type="markdown", title="t", text="hello")
        assert md.source == "hello"

    def test_controls_reserved_and_empty_by_default(self):
        assert chart_card().controls == []

    def test_round_trips_through_json(self):
        card = chart_card(layout=CardLayout(x=0, y=0, w=6, h=3))
        restored = CardSpec.model_validate_json(card.model_dump_json())
        assert restored == card


class TestCardLayout:
    def test_bounds(self):
        CardLayout(x=11, y=0, w=1, h=1)  # max x ok
        with pytest.raises(ValidationError):
            CardLayout(x=12, y=0, w=1, h=1)
        with pytest.raises(ValidationError):
            CardLayout(x=0, y=0, w=13, h=1)
        with pytest.raises(ValidationError):
            CardLayout(x=0, y=0, w=0, h=1)

    def test_overflow_rejected(self):
        with pytest.raises(ValidationError):
            CardLayout(x=10, y=0, w=4, h=1)  # 10 + 4 = 14 > 12
        with pytest.raises(ValidationError):
            Placement(name="a", x=10, y=0, w=4, h=1)


class TestDashboardSpec:
    def test_upsert_appends_then_replaces(self):
        spec = DashboardSpec()
        spec.upsert_card(chart_card())
        assert len(spec.cards) == 1
        spec.upsert_card(CardSpec(name="trend", type="markdown", title="now md", text="x"))
        assert len(spec.cards) == 1
        assert spec.cards[0].type == "markdown"

    def test_get_card(self):
        spec = DashboardSpec(cards=[chart_card()])
        assert spec.get_card("trend") is spec.cards[0]
        assert spec.get_card("nope") is None

    def test_remove_card_hides_not_deletes(self):
        spec = DashboardSpec(cards=[chart_card(layout=CardLayout(x=0, y=0, w=6, h=3))])
        assert spec.remove_card("trend") is True
        assert spec.get_card("trend") is not None  # still in palette
        assert spec.get_card("trend").layout is None
        assert spec.remove_card("nope") is False

    def test_on_canvas_only_lists_placed_cards(self):
        placed = chart_card("a", layout=CardLayout(x=0, y=0, w=6, h=3))
        hidden = chart_card("b")
        spec = DashboardSpec(cards=[placed, hidden])
        assert [c.name for c in spec.on_canvas()] == ["a"]

    def test_next_free_y(self):
        spec = DashboardSpec()
        assert spec.next_free_y() == 0
        spec.upsert_card(chart_card("a", layout=CardLayout(x=0, y=2, w=6, h=3)))
        assert spec.next_free_y() == 5

    def test_apply_placements(self):
        spec = DashboardSpec(cards=[chart_card("a")])
        spec.apply_placements([Placement(name="a", x=3, y=1, w=4, h=2)])
        assert spec.get_card("a").layout == CardLayout(x=3, y=1, w=4, h=2)

    def test_apply_placements_unknown_name_raises(self):
        spec = DashboardSpec()
        with pytest.raises(KeyError, match="nope"):
            spec.apply_placements([Placement(name="nope", x=0, y=0, w=1, h=1)])

    def test_apply_placements_is_atomic(self):
        spec = DashboardSpec(cards=[chart_card("a")])
        with pytest.raises(KeyError):
            spec.apply_placements([
                Placement(name="a", x=3, y=1, w=4, h=2),
                Placement(name="nope", x=0, y=0, w=1, h=1),
            ])
        assert spec.get_card("a").layout is None  # nothing applied

    def test_next_free_y_multiple_and_hidden_cards(self):
        spec = DashboardSpec(cards=[
            chart_card("a", layout=CardLayout(x=0, y=0, w=6, h=2)),
            chart_card("b", layout=CardLayout(x=6, y=3, w=6, h=4)),
            chart_card("c"),  # hidden, ignored
        ])
        assert spec.next_free_y() == 7
