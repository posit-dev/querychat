import asyncio

import pytest
from querychat._artifact_orchestrator import (
    ArtifactOrchestrator,
    GenerateRequest,
    format_language_label,
    version_from_result,
)
from querychat._artifact_prompt import ArtifactResult
from querychat._artifact_state import ArtifactState, ArtifactVersion
from querychat._artifact_types import ARTIFACT_TYPES


class FakeSession:
    """Records custom messages sent to the client; namespaces ids predictably."""

    def __init__(self):
        self.messages: list[tuple[str, dict]] = []

    def ns(self, name: str) -> str:
        return f"ns-{name}"

    async def send_custom_message(self, msg_type: str, payload: dict) -> None:
        self.messages.append((msg_type, payload))


class FakeChat:
    """Minimal chatlas.Chat stand-in: streams fixed chunks, tracks turns."""

    def __init__(self, chunks: list[str] | None = None, structured: object = None):
        self._chunks = list(chunks or [])
        self._structured = structured
        self._turns: list[object] = []
        self.system_prompt: str | None = None

    def set_turns(self, turns):
        self._turns = list(turns)

    def get_turns(self):
        return list(self._turns)

    async def stream_async(self, prompt, echo="none", data_model=None):
        chunks = self._chunks

        async def gen():
            for chunk in chunks:
                yield chunk

        return gen()

    async def chat_structured_async(self, prompt, data_model=None):
        return self._structured


class FakeDataSource:
    """Non-DataFrame data source: artifact data context falls back to database."""

    table_name = "mtcars"

    def get_db_type(self) -> str:
        return "DuckDB"

    def get_schema(self, *, categorical_threshold: int = 20) -> str:
        return "Table mtcars\nColumns: mpg (FLOAT), cyl (INTEGER)"


class FakeChatUI:
    """Minimal shinychat.Chat stand-in: drains appended message streams."""

    def __init__(self):
        self.appended: list[list[object]] = []

    async def append_message_stream(self, stream) -> None:
        self.appended.append([chunk async for chunk in stream])


def make_session(
    chat: FakeChat | None = None,
    data_source: object | None = None,
    chat_ui: object | None = None,
) -> ArtifactOrchestrator:
    return ArtifactOrchestrator(
        session=FakeSession(),
        chat=chat or FakeChat([]),
        data_source=data_source or object(),
        chat_ui=chat_ui or FakeChatUI(),
    )


def make_state(artifact_id: str = "a", source: str = "v1") -> ArtifactState:
    return ArtifactState(
        artifact_id=artifact_id,
        artifact_type=ARTIFACT_TYPES["quarto-dashboard"],
        system_prompt="sys",
        versions=[ArtifactVersion(source=source, turns=[], kind="generated")],
    )


def message_types(orch: ArtifactOrchestrator) -> list[str]:
    return [msg_type for msg_type, _ in orch.view.session.messages]


class TestFormatLanguageLabel:
    def test_supported_language_returns_label(self):
        assert format_language_label(ARTIFACT_TYPES["quarto-dashboard"], "python") == (
            "Python"
        )

    def test_unsupported_language_returns_empty(self):
        # marimo is python-only
        assert format_language_label(ARTIFACT_TYPES["marimo-notebook"], "r") == ""


class TestStepVersion:
    def test_unknown_id_is_noop(self):
        orch = make_session()
        asyncio.run(orch.step_version("missing", 1))
        assert orch.view.session.messages == []

    def test_step_sends_version_view(self):
        orch = make_session()
        state = make_state()
        state.push_version(ArtifactVersion(source="v2", turns=[], kind="revised"))
        orch.store.remember(state)

        asyncio.run(orch.step_version("a", -1))

        assert state.current_index == 0
        assert "querychat-artifact-source-update" in message_types(orch)
        assert "querychat-artifact-version-update" in message_types(orch)


class TestStoreEviction:
    def test_get_state_unknown_returns_none(self):
        orch = make_session()
        assert orch.store.get("missing") is None
        assert orch.store.get(None) is None

    def test_evicts_least_recently_used_past_cap(self, monkeypatch):
        monkeypatch.setattr("querychat._artifact_store.MAX_STORED_ARTIFACTS", 3)
        orch = make_session()
        for i in range(5):
            orch.store.remember(make_state(artifact_id=f"a{i}"))
        assert list(orch.store.keys()) == ["a2", "a3", "a4"]

    def test_access_protects_from_eviction(self, monkeypatch):
        monkeypatch.setattr("querychat._artifact_store.MAX_STORED_ARTIFACTS", 3)
        orch = make_session()
        for i in range(3):
            orch.store.remember(make_state(artifact_id=f"a{i}"))

        # Touch a0 so it becomes most-recently-used, then push past the cap.
        assert orch.store.get("a0") is not None
        orch.store.remember(make_state(artifact_id="a3"))

        # a1 is now the oldest and is evicted; a0 survives.
        assert orch.store.has("a0")
        assert not orch.store.has("a1")
        assert list(orch.store.keys()) == ["a2", "a0", "a3"]


class TestBookmark:
    def test_roundtrip_through_bookmark_values(self):
        orch = make_session(data_source=FakeDataSource())
        orch.store.remember(make_state("a", "src-a"))
        orch.store.remember(make_state("b", "src-b"))

        saved = orch.store.bookmark_values()

        restored = make_session(data_source=FakeDataSource())
        restored.restore_from_bookmark(saved)

        assert restored.store.has("a")
        assert restored.store.has("b")
        # LRU order is preserved on restore (checked before any access reorders it).
        assert list(restored.store.keys()) == ["a", "b"]
        assert restored.store.get("a").source == "src-a"

    def test_restore_regenerates_bundled_data_from_source(self):
        orch = make_session(data_source=FakeDataSource())
        state = make_state("a")
        state.bundled_files = {"mtcars.csv": b"original"}
        state.data_instructions = "original instructions"
        orch.store.remember(state)

        saved = orch.store.bookmark_values()

        restored = make_session(data_source=FakeDataSource())
        restored.restore_from_bookmark(saved)

        s = restored.store.get("a")
        # FakeDataSource isn't a DataFrameSource, so the data context falls back
        # to the database variant: no bundled files, regenerated instructions.
        assert s.bundled_files == {}
        assert "DuckDB" in s.data_instructions

    def test_bookmark_values_empty_store(self):
        orch = make_session(data_source=FakeDataSource())
        assert orch.store.bookmark_values() == []


class TestRevise:
    def test_revise_pushes_new_version(self):
        orch = make_session(
            FakeChat(['{"source": "new source", "summary": "s"}'])
        )
        state = make_state()
        orch.store.remember(state)

        asyncio.run(orch.revise("a", "make it better"))

        assert state.total == 2
        assert state.current_version.kind == "revised"
        assert state.source == "new source"
        assert state.summary == "s"

    def test_blank_instructions_is_noop(self):
        orch = make_session(FakeChat(["ignored"]))
        state = make_state()
        orch.store.remember(state)

        asyncio.run(orch.revise("a", ""))

        assert state.total == 1

    def test_stream_failure_restores_view_and_reraises(self):
        class BoomChat(FakeChat):
            async def stream_async(self, prompt, echo="none", data_model=None):
                raise RuntimeError("stream blew up")

        orch = make_session(BoomChat([]))
        state = make_state()
        orch.store.remember(state)

        with pytest.raises(RuntimeError, match="stream blew up"):
            asyncio.run(orch.revise("a", "do it"))

        # current version preserved and the editor was restored
        assert state.total == 1
        assert "querychat-artifact-source-update" in message_types(orch)


class TestStreamArtifactVersion:
    def test_returns_result_and_turns_and_updates_editor(self):
        chat = FakeChat(['{"source": "generated src", "summary": "s"}'])
        orch = make_session(chat)

        result, turns = asyncio.run(
            orch.chat.stream(
                "make it", turns=[], system_prompt="sys", sink=orch.view
            )
        )

        assert result.source == "generated src"
        assert result.summary == "s"
        # turns come from the forked chat
        assert turns == []
        # the editor received at least one source update
        assert "querychat-artifact-source-update" in message_types(orch)


class TestVersionFromResult:
    def test_maps_fields_for_generated(self):
        result = ArtifactResult(
            source="src", summary="sum", install_instructions="pip install x"
        )
        version = version_from_result(result, [], "generated")
        assert version.source == "src"
        assert version.summary == "sum"
        assert version.install_instructions == "pip install x"
        assert version.kind == "generated"
        assert version.turns == []

    def test_carries_turns_and_kind_for_revised(self):
        import chatlas

        turns = [chatlas.Turn(role="user", contents="hi")]
        result = ArtifactResult(source="src2", summary="", install_instructions="")
        version = version_from_result(result, turns, "revised")
        assert version.kind == "revised"
        assert version.turns == turns
        assert version.summary == ""


class TestGenerate:
    @pytest.fixture(autouse=True)
    def _no_modal(self, monkeypatch):
        # remove_modal()/modal_remove() needs a live Shiny session; stub it so
        # these orchestration tests run with plain fakes.
        import querychat._artifact_view as view_mod

        monkeypatch.setattr(view_mod.ui, "modal_remove", lambda: None)

    def test_stores_under_provided_id(self):
        chat = FakeChat(['{"source": "gen src", "summary": "sum"}'])
        orch = make_session(chat, data_source=FakeDataSource())
        req = GenerateRequest(type_id="quarto-dashboard")

        asyncio.run(orch.generate(req, "", "myid"))

        assert orch.store.has("myid")
        assert orch.store.get("myid").source == "gen src"

    def test_does_not_drive_panel_visibility(self):
        # The panel's open/closed state is owned by the server's
        # active_artifact_id; generate must not emit a panel-toggle itself.
        chat = FakeChat(['{"source": "gen src", "summary": "sum"}'])
        orch = make_session(chat, data_source=FakeDataSource())
        req = GenerateRequest(type_id="quarto-dashboard")

        asyncio.run(orch.generate(req, "", "myid"))

        assert "querychat-artifact-panel-toggle" not in message_types(orch)

    def test_failure_discards_provided_id_and_reraises(self):
        class BoomChat(FakeChat):
            async def stream_async(self, prompt, echo="none", data_model=None):
                raise RuntimeError("boom")

        orch = make_session(BoomChat([]), data_source=FakeDataSource())
        req = GenerateRequest(type_id="quarto-dashboard")

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(orch.generate(req, "", "myid"))

        assert not orch.store.has("myid")


class TestPrepareGeneration:
    def test_builds_plan_for_known_type(self):
        orch = make_session(data_source=FakeDataSource())
        req = GenerateRequest(
            selected_ids=[], type_id="quarto-dashboard", language="", freeform=""
        )

        plan = asyncio.run(orch.prepare_generation(req, "make it dark"))

        assert plan.artifact_type.id == "quarto-dashboard"
        assert isinstance(plan.system_prompt, str)
        assert plan.system_prompt
        assert isinstance(plan.user_prompt, str)
        assert plan.user_prompt
        # FakeDataSource is not a DataFrameSource -> database context, no bundle
        assert plan.data_context.bundled_files == {}
