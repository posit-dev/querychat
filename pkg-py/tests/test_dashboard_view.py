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
