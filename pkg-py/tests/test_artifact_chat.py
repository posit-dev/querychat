import asyncio
import itertools

import pytest
import querychat._artifact_prompt as artifact_prompt
from pydantic import BaseModel, ValidationError
from querychat._artifact_chat import ArtifactChat
from querychat._artifact_prompt import ArtifactResult


class FakeChat:
    """chatlas.Chat stand-in: streams fixed chunks or returns a structured value."""

    def __init__(self, chunks=None, structured=None, expected_data_model=None):
        self._chunks = list(chunks or [])
        self._structured = structured
        self._turns = []
        self.system_prompt = None
        self.expected_data_model = expected_data_model

    def set_turns(self, turns):
        self._turns = list(turns)

    def get_turns(self):
        return list(self._turns)

    async def stream_async(self, prompt, data_model=None, echo="none"):
        if self.expected_data_model is not None:
            assert data_model is self.expected_data_model
        chunks = self._chunks

        async def gen():
            for c in chunks:
                yield c

        return gen()

    async def chat_structured_async(self, prompt, data_model=None):
        return self._structured


class FakeSink:
    """Records what ArtifactChat.stream pushes to the view."""

    def __init__(self):
        self.sources = []
        self.streaming = []

    async def update_source(self, value):
        self.sources.append(value)

    async def set_streaming(self, *, active):
        self.streaming.append(active)


class TestStream:
    def test_streams_growing_source_and_returns_result(self):
        chunks = [
            '{"source": "import shiny',
            '\\nfrom shiny import ui", ',
            '"summary": "A demo app", ',
            '"install_instructions": "pip install shiny", ',
            '"referenced_tables": []}',
        ]
        sink = FakeSink()
        chat = ArtifactChat(FakeChat(chunks))
        result, turns = asyncio.run(
            chat.stream(
                "go",
                turns=[],
                system_prompt="sys",
                sink=sink,
                model=ArtifactResult,
            )
        )

        assert result.source == "import shiny\nfrom shiny import ui"
        assert result.summary == "A demo app"
        assert result.install_instructions == "pip install shiny"
        assert turns == []
        assert sink.sources[-1] == "import shiny\nfrom shiny import ui"
        assert all(len(a) <= len(b) for a, b in itertools.pairwise(sink.sources))

    def test_emits_streaming_on_first_then_off_last(self):
        chunks = [
            (
                '{"source": "x", "summary": "s", '
                '"install_instructions": "i", "referenced_tables": []}'
            )
        ]
        sink = FakeSink()
        chat = ArtifactChat(FakeChat(chunks))
        asyncio.run(
            chat.stream(
                "go",
                turns=[],
                system_prompt=None,
                sink=sink,
                model=ArtifactResult,
            )
        )

        assert sink.streaming[0] is True
        assert sink.streaming[-1] is False

    def test_truncated_json_raises_and_clears_streaming(self):
        sink = FakeSink()
        chat = ArtifactChat(FakeChat(['{"source": "x"']))
        with pytest.raises(ValidationError):
            asyncio.run(
                chat.stream(
                    "go",
                    turns=[],
                    system_prompt=None,
                    sink=sink,
                    model=ArtifactResult,
                )
            )
        assert sink.streaming[-1] is False

    def test_stream_uses_supplied_result_model(self):
        model = artifact_prompt.artifact_result_model(["orders"])
        fake = FakeChat(
            ['{"source":"x","referenced_tables":["orders"]}'],
            expected_data_model=model,
        )
        sink = FakeSink()

        result, _ = asyncio.run(
            ArtifactChat(fake).stream(
                "go",
                turns=[],
                system_prompt=None,
                sink=sink,
                model=model,
            )
        )

        assert result.referenced_tables == ["orders"]


class _Meta(BaseModel):
    answer: str


class TestAsk:
    def test_forks_and_returns_structured_result(self):
        chat = ArtifactChat(FakeChat(structured=_Meta(answer="42")))
        result = asyncio.run(chat.ask("q", _Meta))
        assert result.answer == "42"


class TestHistoryTurns:
    def test_returns_live_chat_turns(self):
        fake = FakeChat()
        fake._turns = ["t1", "t2"]
        chat = ArtifactChat(fake)
        assert chat.history_turns() == ["t1", "t2"]
