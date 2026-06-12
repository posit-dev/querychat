from __future__ import annotations

import narwhals as nw
import pandas as pd
import pytest
from querychat._dashboard_server import DashboardController
from querychat._dashboard_state import CardLayout, CardSpec, DashboardSpec, Placement
from querychat._datasource import DataFrameSource


@pytest.fixture
def controller() -> DashboardController:
    df = pd.DataFrame({"mpg": [21.0, 22.8], "cyl": [6, 4]})
    return DashboardController(DataFrameSource(nw.from_native(df), "mtcars"))


def md_card(name: str = "notes") -> CardSpec:
    return CardSpec(name=name, type="markdown", title="Notes", text="hi")


class TestStageMutations:
    def test_stage_set_cards_places_and_queues(self, controller):
        controller.stage_set_cards([md_card()])
        assert controller.spec.get_card("notes").layout is not None
        kinds = [op[0] for op in controller.drain_outbox()]
        assert "card-upsert" in kinds
        assert controller.drain_outbox() == []  # drained

    def test_stage_arrange(self, controller):
        controller.stage_set_cards([md_card()])
        controller.drain_outbox()
        controller.stage_arrange([Placement(name="notes", x=6, y=0, w=6, h=2)])
        assert controller.spec.get_card("notes").layout.x == 6

    def test_stage_arrange_unknown_raises_keyerror(self, controller):
        with pytest.raises(KeyError):
            controller.stage_arrange([Placement(name="nope", x=0, y=0, w=1, h=1)])

    def test_browser_layout_ignores_hidden_cards(self, controller):
        controller.stage_set_cards([md_card()])
        controller.stage_remove("notes")
        controller.drain_outbox()
        controller.apply_browser_layout(
            [{"name": "notes", "x": 0, "y": 0, "w": 6, "h": 2}]
        )
        assert controller.spec.get_card("notes").layout is None  # stays hidden

    def test_stage_remove(self, controller):
        controller.stage_set_cards([md_card()])
        controller.stage_remove("notes")
        assert controller.spec.get_card("notes").layout is None
        with pytest.raises(KeyError):
            controller.stage_remove("never_existed")


class TestUndoRedo:
    def test_undo_restores_previous_spec_and_queues_resync(self, controller):
        controller.stage_set_cards([md_card()])
        controller.drain_outbox()
        assert controller.undo() is True
        assert controller.spec.cards == []
        kinds = [op[0] for op in controller.drain_outbox()]
        assert kinds[0] == "canvas-reset"

    def test_redo(self, controller):
        controller.stage_set_cards([md_card()])
        controller.undo()
        assert controller.redo() is True
        assert controller.spec.get_card("notes") is not None

    def test_redo_false_at_head(self, controller):
        assert controller.redo() is False

    def test_drag_layout_change_is_undoable(self, controller):
        controller.stage_set_cards([md_card()])
        controller.apply_browser_layout(
            [{"name": "notes", "x": 6, "y": 0, "w": 6, "h": 2}]
        )
        assert controller.spec.get_card("notes").layout.x == 6
        controller.undo()
        assert controller.spec.get_card("notes").layout.x == 0


class TestBookmarkRoundTrip:
    def test_dump_and_restore(self, controller):
        controller.stage_set_cards([md_card()])
        dumped = controller.bookmark_value()
        c2 = DashboardController(controller.data_source)
        c2.restore_from_bookmark(dumped)
        assert c2.spec.get_card("notes") is not None

    def test_restore_starts_fresh_history(self, controller):
        controller.stage_set_cards([md_card()])
        dumped = controller.bookmark_value()
        c2 = DashboardController(controller.data_source)
        c2.restore_from_bookmark(dumped)
        # dashboard_server sets opened_once on restore; the controller itself
        # restores cleanly with a fresh history timeline
        assert not c2.history.can_undo()


class TestReplaceSpec:
    def test_replace_spec_queues_full_resync(self, controller):
        spec = DashboardSpec(title="Generated")
        card = md_card("gen")
        card.layout = CardLayout(x=0, y=0, w=12, h=2)
        spec.upsert_card(card)
        controller.replace_spec(spec)
        ops = controller.drain_outbox()
        assert ops[0][0] == "canvas-reset"
        assert ops[0][1] == {"title": "Generated"}
        assert any(op[0] == "card-upsert" and op[1]["name"] == "gen" for op in ops)
