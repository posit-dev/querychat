import asyncio

from querychat._dashboard_state import CardLayout
from querychat._dashboard_view import MESSAGE_PREFIX, DashboardView


class FakeSession:
    def __init__(self):
        self.messages: list[tuple[str, dict]] = []

    async def send_custom_message(self, msg_type: str, payload: dict) -> None:
        self.messages.append((msg_type, payload))


def make_view() -> tuple[DashboardView, FakeSession]:
    session = FakeSession()
    return DashboardView(session), session


class TestSetOpen:
    def test_sends_drawer_toggle(self):
        v, session = make_view()
        asyncio.run(v.set_open(is_open=True))
        assert session.messages == [(f"{MESSAGE_PREFIX}drawer-toggle", {"open": True})]

    def test_sends_drawer_toggle_false(self):
        v, session = make_view()
        asyncio.run(v.set_open(is_open=False))
        assert session.messages == [(f"{MESSAGE_PREFIX}drawer-toggle", {"open": False})]


class TestCardUpsert:
    def test_includes_layout(self):
        v, session = make_view()
        asyncio.run(v.card_upsert("kpi", "<div/>", CardLayout(x=0, y=0, w=4, h=2)))
        assert len(session.messages) == 1
        action, payload = session.messages[0]
        assert action == f"{MESSAGE_PREFIX}card-upsert"
        assert payload == {
            "name": "kpi",
            "html": "<div/>",
            "layout": {"x": 0, "y": 0, "w": 4, "h": 2},
        }


class TestCanvasReset:
    def test_sends_canvas_reset_with_title(self):
        v, session = make_view()
        asyncio.run(v.canvas_reset(title="Demo"))
        assert len(session.messages) == 1
        action, payload = session.messages[0]
        assert action == f"{MESSAGE_PREFIX}canvas-reset"
        assert payload == {"title": "Demo"}


class TestRemainingActions:
    """Typo guard for the rest of the wire contract (one smoke test per action)."""

    def test_actions_and_payload_keys(self):
        v, session = make_view()
        asyncio.run(v.card_remove("kpi"))
        asyncio.run(v.layout_apply([{"name": "kpi", "x": 0, "y": 0, "w": 4, "h": 2}]))
        asyncio.run(v.set_badge(3))
        asyncio.run(v.palette_update("<div/>"))
        asyncio.run(v.set_autogen(active=True))
        asyncio.run(v.set_history_buttons(can_undo=True, can_redo=False))
        assert session.messages == [
            (f"{MESSAGE_PREFIX}card-remove", {"name": "kpi"}),
            (
                f"{MESSAGE_PREFIX}layout-apply",
                {"placements": [{"name": "kpi", "x": 0, "y": 0, "w": 4, "h": 2}]},
            ),
            (f"{MESSAGE_PREFIX}badge", {"count": 3}),
            (f"{MESSAGE_PREFIX}palette", {"html": "<div/>"}),
            (f"{MESSAGE_PREFIX}autogen", {"active": True}),
            (f"{MESSAGE_PREFIX}history", {"can_undo": True, "can_redo": False}),
        ]
