import asyncio

from querychat._artifact_types import ARTIFACT_TYPES
from querychat._artifact_view import ArtifactView


class FakeSession:
    def __init__(self):
        self.messages = []

    def ns(self, name):
        return f"ns-{name}"

    async def send_custom_message(self, msg_type, payload):
        self.messages.append((msg_type, payload))


class FakeChatUI:
    def __init__(self):
        self.streamed = []

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
                {"id": view.editor_id, "value": "print(1)"},
            ),
        ]


class TestSetStreaming:
    def test_toggles_streaming_flag(self):
        view = make_view()
        asyncio.run(view.set_streaming(active=True))
        asyncio.run(view.set_streaming(active=False))
        assert view.session.messages == [
            ("querychat-artifact-streaming", {"active": True}),
            ("querychat-artifact-streaming", {"active": False}),
        ]


class TestAppendPill:
    def test_streams_pill_then_summary(self):
        view = make_view()
        art_type = ARTIFACT_TYPES["quarto-dashboard"]
        asyncio.run(view.append_pill("abc123", art_type, "A dashboard"))

        streamed = view.chat_ui.streamed
        assert "abc123" in str(streamed[0])  # pill HTML carries the artifact id
        assert streamed[-1] == "A dashboard"

    def test_omits_empty_summary(self):
        view = make_view()
        art_type = ARTIFACT_TYPES["quarto-dashboard"]
        asyncio.run(view.append_pill("abc123", art_type, ""))
        assert len(view.chat_ui.streamed) == 1  # pill only, no summary part


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
            "querychat._artifact_view.build_modal_ui", lambda ns, items: "MODAL"
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
