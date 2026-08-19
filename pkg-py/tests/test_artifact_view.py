import asyncio
import re
from pathlib import Path

import pytest
from pydantic import ValidationError
from querychat._artifact_protocol import (
    ARTIFACT_MESSAGE_ACTIONS,
    SourceUpdateMessage,
)
from querychat._artifact_types import resolve_artifact_type
from querychat._artifact_view import ArtifactView


def test_source_update_message_uses_protocol_action_and_payload():
    message = SourceUpdateMessage(
        root_id="artifact_root",
        id="artifact_source_editor",
        value="print(1)",
    )

    assert message.message_type() == "querychat-artifact-source-update"
    assert message.payload() == {
        "root_id": "artifact_root",
        "id": "artifact_source_editor",
        "value": "print(1)",
    }


def test_protocol_messages_reject_unknown_payload_fields():
    with pytest.raises(ValidationError, match="extra_field"):
        SourceUpdateMessage(
            root_id="artifact_root",
            id="artifact_source_editor",
            value="print(1)",
            extra_field=True,
        )


def test_protocol_actions_match_browser_handlers():
    source = (Path(__file__).parents[2] / "js" / "src" / "artifact-core.ts").read_text()
    browser_actions = re.findall(
        r'^\s*"([a-z-]+)",$',
        source.split("const artifactMessageActions = [", 1)[1].split("] as const;", 1)[
            0
        ],
        flags=re.MULTILINE,
    )

    assert browser_actions == list(ARTIFACT_MESSAGE_ACTIONS)


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
    return ArtifactView(FakeSession(), FakeChatUI())


class TestUpdateSource:
    def test_sends_source_update_to_editor(self):
        view = make_view()
        asyncio.run(view.update_source("print(1)"))
        assert view.session.messages == [
            (
                "querychat-artifact-source-update",
                {
                    "root_id": view.panel_root_id,
                    "id": view.editor_id,
                    "value": "print(1)",
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
                "querychat-artifact-streaming",
                {"root_id": view.panel_root_id, "active": True},
            ),
            (
                "querychat-artifact-streaming",
                {"root_id": view.panel_root_id, "active": False},
            ),
        ]


class TestAppendPill:
    def test_appends_complete_pill_message_with_summary(self):
        view = make_view()
        art_type = resolve_artifact_type("quarto-dashboard", "python")
        asyncio.run(view.append_pill("abc123", art_type, "A dashboard"))

        assert len(view.chat_ui.appended) == 1
        message = str(view.chat_ui.appended[0])
        assert "abc123" in message
        assert "<p>A dashboard</p>" in message
        assert view.chat_ui.streamed == []

    def test_omits_empty_summary(self):
        view = make_view()
        art_type = resolve_artifact_type("quarto-dashboard", "python")
        asyncio.run(view.append_pill("abc123", art_type, ""))

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
        monkeypatch.setattr("querychat._artifact_view.ui", fake_ui)
        monkeypatch.setattr(
            "querychat._artifact_view.build_modal_ui",
            lambda ns, items: "MODAL",
        )
        view = make_view()
        view.show_modal([])
        assert fake_ui.shown == ["MODAL"]

    def test_remove_modal_delegates_to_ui(self, monkeypatch):
        fake_ui = FakeUI()
        monkeypatch.setattr("querychat._artifact_view.ui", fake_ui)
        view = make_view()
        view.remove_modal()
        assert fake_ui.removed == 1
