import asyncio

import pytest
from pydantic import ValidationError
from querychat._handoff_protocol import SourceUpdateMessage
from querychat._handoff_state import HandoffState
from querychat._handoff_types import resolve_handoff_type
from querychat._handoff_view import HandoffView


def test_source_update_message_uses_protocol_action_and_payload():
    message = SourceUpdateMessage(
        root_id="handoff_root",
        id="handoff_source_editor",
        value="print(1)",
    )

    assert message.message_type() == "querychat-handoff-source-update"
    assert message.payload() == {
        "root_id": "handoff_root",
        "id": "handoff_source_editor",
        "value": "print(1)",
    }


def test_protocol_messages_reject_unknown_payload_fields():
    with pytest.raises(ValidationError, match="extra_field"):
        SourceUpdateMessage(
            root_id="handoff_root",
            id="handoff_source_editor",
            value="print(1)",
            extra_field=True,
        )


class FakeSession:
    def __init__(self):
        self.messages = []

    def ns(self, name):
        return f"ns-{name}"

    async def send_custom_message(self, msg_type, payload):
        self.messages.append((msg_type, payload))


class FakeChatUI:
    def __init__(self):
        self.appended = []
        self.streamed = []

    async def append_message(self, message):
        self.appended.append(message)

    async def append_message_stream(self, stream):
        async for part in stream:
            self.streamed.append(part)


def make_view():
    return HandoffView(FakeSession(), FakeChatUI())


class TestUpdateSource:
    def test_sends_source_update_to_editor(self):
        view = make_view()
        asyncio.run(view.update_source("print(1)"))
        assert view.session.messages == [
            (
                "querychat-handoff-source-update",
                {
                    "root_id": view.panel_root_id,
                    "id": view.editor_id,
                    "value": "print(1)",
                },
            ),
        ]

    def test_appends_source_delta_to_editor(self):
        view = make_view()
        asyncio.run(view.append_source("print(1)"))

        assert view.session.messages == [
            (
                "querychat-handoff-source-update",
                {
                    "root_id": view.panel_root_id,
                    "id": view.editor_id,
                    "value": "print(1)",
                    "append": True,
                },
            ),
        ]

    def test_show_handoff_sends_current_source_and_download_state(self):
        view = make_view()
        handoff_type = resolve_handoff_type("quarto-dashboard", "python")
        state = HandoffState(
            handoff_id="a",
            handoff_type=handoff_type,
            system_prompt="sys",
            source="print(1)",
        )

        asyncio.run(view.show_handoff(state, download_available=False))

        assert view.session.messages == [
            (
                "querychat-handoff-source-update",
                {
                    "root_id": view.panel_root_id,
                    "id": view.editor_id,
                    "value": "print(1)",
                    "language": handoff_type.editor_language,
                    "download_available": False,
                },
            ),
        ]


class TestSetStreaming:
    def test_toggles_streaming_flag(self):
        view = make_view()
        asyncio.run(view.set_streaming(active=True))
        asyncio.run(view.set_streaming(active=False))
        assert view.session.messages == [
            (
                "querychat-handoff-streaming",
                {"root_id": view.panel_root_id, "active": True},
            ),
            (
                "querychat-handoff-streaming",
                {"root_id": view.panel_root_id, "active": False},
            ),
        ]


class TestAppendPill:
    def test_appends_complete_pill_message_with_summary(self):
        view = make_view()
        handoff_type = resolve_handoff_type("quarto-dashboard", "python")
        asyncio.run(view.append_pill("abc123", handoff_type, "A dashboard"))

        assert len(view.chat_ui.appended) == 1
        message = str(view.chat_ui.appended[0])
        assert "abc123" in message
        assert "<p>A dashboard</p>" in message
        assert view.chat_ui.streamed == []

    def test_omits_empty_summary(self):
        view = make_view()
        handoff_type = resolve_handoff_type("quarto-dashboard", "python")
        asyncio.run(view.append_pill("abc123", handoff_type, ""))

        assert len(view.chat_ui.appended) == 1
        assert "abc123" in str(view.chat_ui.appended[0])
        assert view.chat_ui.streamed == []


class FakeUI:
    def __init__(self):
        self.shown = []
        self.removed = 0

    def modal_show(self, modal):
        self.shown.append(modal)

    def modal_remove(self):
        self.removed += 1


class TestModal:
    def test_show_modal_delegates_to_ui(self, monkeypatch):
        fake_ui = FakeUI()
        monkeypatch.setattr("querychat._handoff_view.ui", fake_ui)
        monkeypatch.setattr(
            "querychat._handoff_view.build_modal_ui",
            lambda ns, items: "MODAL",
        )
        view = make_view()
        view.show_modal([])
        assert fake_ui.shown == ["MODAL"]

    def test_remove_modal_delegates_to_ui(self, monkeypatch):
        fake_ui = FakeUI()
        monkeypatch.setattr("querychat._handoff_view.ui", fake_ui)
        view = make_view()
        view.remove_modal()
        assert fake_ui.removed == 1
