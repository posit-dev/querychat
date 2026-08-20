from __future__ import annotations

import asyncio
import io
import json
import zipfile

import chatlas
import nbformat
import pytest
import querychat._artifact_view as view_mod
from pydantic import ValidationError
from querychat._artifact_bundle_store import ArtifactSnapshotUnavailableError
from querychat._artifact_data import ArtifactDataContext, ArtifactDataError
from querychat._artifact_orchestrator import (
    ArtifactOrchestrator,
    GenerateRequest,
    build_freeform_artifact_type,
    state_from_result,
)
from querychat._artifact_prompt import ArtifactResult, FreeformMetadata
from querychat._artifact_state import ArtifactState
from querychat._artifact_types import ArtifactLanguage, resolve_artifact_type
from querychat._artifact_validation import ArtifactValidationError
from querychat._datasource import DataFrameSource
from querychat.data import tips


@pytest.fixture(autouse=True)
def no_modal(monkeypatch):
    monkeypatch.setattr(view_mod.ui, "modal_remove", lambda: None)


class FakeSession:
    """Records custom messages sent to the client; namespaces ids predictably."""

    def __init__(self):
        self.messages: list[tuple[str, dict]] = []

    def ns(self, name: str) -> str:
        return f"ns-{name}"

    async def send_custom_message(self, msg_type: str, payload: dict) -> None:
        self.messages.append((msg_type, payload))


class FakeStreamController:
    def __init__(self, streams: list[list[str]]) -> None:
        self.streams = streams
        self.stream_count = 0
        self.incoming_turns: list[list[chatlas.Turn]] = []

    def __deepcopy__(self, memo: dict[int, object]) -> FakeStreamController:
        """Keep stream sequencing shared across copied chat forks."""
        return self


class FakeChat:
    """Minimal chatlas.Chat stand-in: streams fixed chunks, tracks turns."""

    def __init__(
        self,
        chunks: list[str] | None = None,
        structured: object = None,
        *,
        streams: list[list[str]] | None = None,
    ):
        self.controller = FakeStreamController(
            streams if streams is not None else [list(chunks or [])]
        )
        self._structured = structured
        self._turns: list[object] = []
        self.system_prompt: str | None = None

    @property
    def stream_count(self) -> int:
        return self.controller.stream_count

    @property
    def incoming_turns(self) -> list[list[chatlas.Turn]]:
        return self.controller.incoming_turns

    def set_turns(self, turns):
        self._turns = list(turns)

    def get_turns(self):
        return list(self._turns)

    async def stream_async(self, prompt, echo="none", data_model=None):
        chunks = self.controller.streams[self.controller.stream_count]
        self.controller.incoming_turns.append(list(self._turns))
        self.controller.stream_count += 1
        self._turns.extend(
            [
                chatlas.Turn(role="user", contents=prompt),
                chatlas.Turn(role="assistant", contents="".join(chunks)),
            ]
        )

        async def gen():
            for chunk in chunks:
                yield chunk

        return gen()

    async def chat_structured_async(self, prompt, data_model=None):
        return self._structured


class FakeDataSource:
    """Non-DataFrame data source: artifact data context falls back to database."""

    def __init__(self, table_name: str = "mtcars"):
        self.table_name = table_name

    def get_db_type(self) -> str:
        return "DuckDB"

    def get_schema(self, *, categorical_threshold: int = 20) -> str:
        return "Table mtcars\nColumns: mpg (FLOAT), cyl (INTEGER)"


class RecordingDataFrameSource(DataFrameSource):
    def __init__(self, table_name: str):
        super().__init__(tips(), table_name)
        self.get_data_calls = 0

    def get_data(self):
        self.get_data_calls += 1
        return super().get_data()


class FakeExecutor:
    def get_schema(
        self,
        table_name: str,
        categorical_threshold: int,
    ) -> str:
        return f"Table {table_name}\nColumns: id (INTEGER)"


class FakeChatUI:
    """Minimal shinychat.Chat stand-in that records complete messages."""

    def __init__(self):
        self.appended: list[object] = []

    async def append_message(self, message: object) -> None:
        self.appended.append(message)

    async def append_message_stream(self, stream) -> None:
        raise AssertionError("Artifact pills must be appended as complete messages")


def make_session(
    chat: FakeChat | None = None,
    data_source: object | None = None,
    data_sources: dict[str, object] | None = None,
    executor: object | None = None,
    chat_ui: object | None = None,
) -> ArtifactOrchestrator:
    source = data_source or FakeDataSource()
    sources = data_sources or {source.table_name: source}
    return ArtifactOrchestrator(
        session=FakeSession(),
        chat=chat or FakeChat([]),
        data_sources=sources,
        executor=executor or FakeExecutor(),
        chat_ui=chat_ui or FakeChatUI(),
    )


def make_state(
    artifact_id: str = "a",
    source: str = "v1",
    language: ArtifactLanguage = "python",
) -> ArtifactState:
    return ArtifactState(
        artifact_id=artifact_id,
        artifact_type=resolve_artifact_type("quarto-dashboard", language),
        system_prompt="sys",
        source=source,
        turns=[],
        run_instructions=f"```bash\nrun artifact in {language}\n```",
    )


def message_types(orch: ArtifactOrchestrator) -> list[str]:
    return [msg_type for msg_type, _ in orch.view.session.messages]


def result_chunk(
    source: str,
    *,
    language: ArtifactLanguage = "python",
    referenced_tables: list[str] | None = None,
    summary: str = "",
) -> str:
    return json.dumps(
        {
            "source": source,
            "language": language,
            "summary": summary,
            "run_instructions": f"```bash\nrun artifact in {language}\n```",
            "referenced_tables": referenced_tables or [],
        }
    )


def r_notebook_source() -> str:
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("1 + 1")],
        metadata={
            "kernelspec": {
                "display_name": "R",
                "language": "r",
                "name": "ir",
            }
        },
    )
    return nbformat.writes(notebook)


def python_notebook_source() -> str:
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("1 + 1")],
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        },
    )
    return nbformat.writes(notebook)


def artifact_result_json(source: str, language: str = "r") -> str:
    return json.dumps(
        {
            "source": source,
            "language": language,
            "run_instructions": "Run with Jupyter Lab.",
            "referenced_tables": [],
        }
    )


def make_r_notebook_state(source: str) -> ArtifactState:
    return ArtifactState(
        artifact_id="a",
        artifact_type=resolve_artifact_type("jupyter-notebook", "r"),
        system_prompt="sys",
        source=source,
        turns=[],
        run_instructions="Run with Jupyter Lab.",
    )


def test_freeform_type_is_text_target_snapshot():
    artifact_type = build_freeform_artifact_type(
        "SQL script",
        FreeformMetadata(file_extension="sql", editor_language="sql"),
        "python",
    )

    assert artifact_type.language == "python"
    assert artifact_type.file_extension == ".sql"
    assert artifact_type.structure == "text"


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
        assert [state.artifact_id for state in orch.store.values()] == [
            "a2",
            "a3",
            "a4",
        ]

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
        assert [state.artifact_id for state in orch.store.values()] == [
            "a2",
            "a0",
            "a3",
        ]

    def test_artifact_eviction_discards_only_unreferenced_bundles(
        self,
        monkeypatch,
    ):
        monkeypatch.setattr("querychat._artifact_store.MAX_STORED_ARTIFACTS", 2)
        source = RecordingDataFrameSource("tips")
        orch = make_session(
            FakeChat([result_chunk("new", referenced_tables=["tips"])]),
            data_sources={"tips": source},
        )
        shared = orch.bundle_store.put({"shared.csv": b"shared"})
        evicted = make_state("evicted")
        evicted.bundle_id = shared.bundle_id
        retained = make_state("retained")
        retained.bundle_id = shared.bundle_id
        orch.store.remember(evicted)
        orch.store.remember(retained)

        asyncio.run(
            orch.generate(
                GenerateRequest(type_id="quarto-dashboard", language="python"),
                "",
                "generated",
            )
        )

        assert not orch.store.has("evicted")
        assert orch.bundle_store.get(shared.bundle_id) is not None
        generated = orch.store.get("generated")
        assert generated is not None
        assert orch.bundle_store.get(generated.bundle_id) is not None

    def test_artifact_eviction_discards_unreachable_bundle(self, monkeypatch):
        monkeypatch.setattr("querychat._artifact_store.MAX_STORED_ARTIFACTS", 1)
        source = RecordingDataFrameSource("tips")
        orch = make_session(
            FakeChat([result_chunk("new", referenced_tables=["tips"])]),
            data_sources={"tips": source},
        )
        old_bundle = orch.bundle_store.put({"old.csv": b"old"})
        old = make_state("old")
        old.bundle_id = old_bundle.bundle_id
        orch.store.remember(old)

        asyncio.run(
            orch.generate(
                GenerateRequest(type_id="quarto-dashboard", language="python"),
                "",
                "generated",
            )
        )

        assert orch.bundle_store.get(old_bundle.bundle_id) is None


class TestBookmark:
    def test_roundtrip_through_bookmark_values(self):
        orch = make_session(data_source=FakeDataSource())
        orch.store.remember(make_state("a", "src-a"))
        orch.store.remember(make_state("b", "src-b"))

        saved = orch.store.bookmark_values()

        restored = make_session(data_source=FakeDataSource())
        restored.restore_snapshot(saved)

        assert restored.store.has("a")
        assert restored.store.has("b")
        # LRU order is preserved on restore (checked before any access reorders it).
        assert [state.artifact_id for state in restored.store.values()] == ["a", "b"]
        assert restored.store.get("a").source == "src-a"

    def test_restore_replaces_artifacts_from_previous_conversation(self):
        previous = make_session(data_source=FakeDataSource())
        previous.store.remember(make_state("old", "src-old"))

        current = make_session(data_source=FakeDataSource())
        current.store.remember(make_state("new", "src-new"))

        previous.restore_snapshot(current.store.bookmark_values())

        assert [state.artifact_id for state in previous.store.values()] == ["new"]
        assert not previous.store.has("old")

    def test_restore_preserves_current_data_contract(self):
        orch = make_session(data_source=FakeDataSource())
        state = make_state("a")
        state.referenced_tables = ["mtcars"]
        state.bundled_tables = ["mtcars"]
        orch.store.remember(state)

        saved = orch.store.bookmark_values()

        restored = make_session(data_source=FakeDataSource())
        restored.restore_snapshot(saved)

        s = restored.store.get("a")
        assert s is not None
        assert s.referenced_tables == ["mtcars"]
        assert s.bundled_tables == ["mtcars"]

    def test_restore_preserves_in_session_bundle_snapshot(self):
        orch = make_session(data_source=FakeDataSource())
        bundle = orch.bundle_store.put({"tips.csv": b"total_bill\n10\n"})
        state = make_state("a")
        state.bundled_tables = ["tips"]
        state.bundle_id = bundle.bundle_id
        state.data_instructions = "Load CSV"
        orch.store.remember(state)
        saved = orch.store.bookmark_values()

        orch.restore_snapshot(saved)

        assert orch.bundle_store.get(bundle.bundle_id) is not None
        archive = asyncio.run(orch.build_download("a"))
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            assert zf.read("tips.csv") == b"total_bill\n10\n"

    def test_bookmark_values_empty_store(self):
        orch = make_session(data_source=FakeDataSource())
        assert orch.store.bookmark_values() == []


class TestDownload:
    def test_restored_database_only_artifact_downloads_without_snapshot(self):
        original = make_session(data_source=FakeDataSource())
        original.store.remember(make_state())

        restored = make_session(data_source=FakeDataSource())
        restored.restore_snapshot(original.store.bookmark_values())
        archive = asyncio.run(restored.build_download("a"))

        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            assert zf.read("artifact.qmd") == b"v1"

    def test_bundle_without_snapshot_never_exports_live_dataframe(self):
        source = RecordingDataFrameSource("tips")
        orch = make_session(data_sources={"tips": source})
        state = make_state()
        state.referenced_tables = ["tips"]
        state.bundled_tables = ["tips"]
        orch.store.remember(state)

        with pytest.raises(ArtifactSnapshotUnavailableError, match="unavailable"):
            asyncio.run(orch.build_download("a"))

        assert source.get_data_calls == 0

    def test_missing_bundle_id_reports_snapshot_unavailable(self):
        orch = make_session(data_source=FakeDataSource())
        state = make_state()
        state.bundled_tables = ["tips"]
        state.bundle_id = "missing"
        orch.store.remember(state)

        with pytest.raises(ArtifactSnapshotUnavailableError, match="unavailable"):
            asyncio.run(orch.build_download("a"))

    def test_download_uses_original_bundle_after_dataframe_mutation(self):
        source = RecordingDataFrameSource("tips")
        orch = make_session(
            FakeChat([result_chunk("source", referenced_tables=["tips"])]),
            data_sources={"tips": source},
        )

        asyncio.run(
            orch.generate(
                GenerateRequest(type_id="quarto-dashboard", language="python"),
                "",
                "a",
            )
        )
        state = orch.store.get("a")
        assert state is not None
        bundle = orch.bundle_store.get(state.bundle_id)
        assert bundle is not None
        original_csv = bundle.bundled_files["tips.csv"]
        source._df = source._df.head(1)

        archive = asyncio.run(orch.build_download("a"))

        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            assert zf.read("tips.csv") == original_csv

    def test_r_artifact_readme_uses_r_database_instructions(self):
        orch = make_session(data_source=FakeDataSource())
        state = make_state(language="r")
        state.referenced_tables = ["mtcars"]
        state.data_instructions = (
            'Use DBI and credentials from `Sys.getenv("DATABASE_URL")`.'
        )
        orch.store.remember(state)

        archive = asyncio.run(orch.build_download("a"))

        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            readme = zf.read("README.md").decode("utf-8")
        assert 'Sys.getenv("DATABASE_URL")' in readme
        assert "os.environ" not in readme

    def test_readme_uses_current_run_instructions(self):
        orch = make_session(data_source=FakeDataSource())
        state = make_state()
        state.run_instructions = "Run it with:\n```bash\npython artifact.py\n```"
        orch.store.remember(state)

        archive = asyncio.run(orch.build_download("a"))

        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            readme = zf.read("README.md").decode("utf-8")
        assert "python artifact.py" in readme


class TestRevise:
    def test_revisions_replace_artifact_and_accumulate_conversation(self):
        source = RecordingDataFrameSource("tips")
        prior_turn = chatlas.Turn(role="assistant", contents="first")
        chat = FakeChat(
            streams=[
                [result_chunk("second", referenced_tables=["tips"])],
                [result_chunk("third", referenced_tables=["tips"])],
            ]
        )
        orch = make_session(
            chat,
            data_sources={"tips": source},
        )
        first_bundle = orch.bundle_store.put({"tips.csv": b"first"})
        state = make_state()
        state.turns = [prior_turn]
        state.bundle_id = first_bundle.bundle_id
        state.bundled_tables = ["tips"]
        orch.store.remember(state)
        source._df = source._df.head(1)

        asyncio.run(orch.revise("a", "make it smaller"))

        second = orch.store.get("a")
        assert second is not None
        second_turns = list(second.turns)
        second_bundle_id = second.bundle_id

        asyncio.run(orch.revise("a", "return to the earlier layout"))

        third = orch.store.get("a")
        assert third is not None
        assert third is not state
        assert third.source == "third"
        assert [turn.role for turn in third.turns] == [
            "assistant",
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert third.turns[0] == prior_turn
        assert chat.incoming_turns == [[prior_turn], second_turns]
        assert orch.bundle_store.get(first_bundle.bundle_id) is None
        assert orch.bundle_store.get(second_bundle_id) is None
        assert orch.bundle_store.get(third.bundle_id) is not None

    def test_failed_revision_preserves_snapshot_under_memory_pressure(
        self,
        monkeypatch,
    ):
        source = RecordingDataFrameSource("tips")
        orch = make_session(
            FakeChat([result_chunk("second", referenced_tables=["tips"])]),
            data_sources={"tips": source},
        )
        first_bundle = orch.bundle_store.put({"tips.csv": b"old!"})
        state = make_state()
        state.bundle_id = first_bundle.bundle_id
        state.bundled_tables = ["tips"]
        orch.store.remember(state)
        monkeypatch.setattr(
            "querychat._artifact_bundle_store.MAX_STORED_BUNDLE_BYTES",
            4,
        )
        monkeypatch.setattr(
            "querychat._artifact_orchestrator.materialize_artifact_data",
            lambda *args: ArtifactDataContext(
                data_instructions="Load tips.csv",
                bundled_files={"tips.csv": b"new!"},
                bundled_tables=["tips"],
            ),
        )
        show_calls = 0

        async def fail_replacement_once(*args, **kwargs):
            nonlocal show_calls
            show_calls += 1
            if show_calls == 1:
                raise RuntimeError("client disconnected")

        monkeypatch.setattr(orch.view, "show_artifact", fail_replacement_once)

        with pytest.raises(RuntimeError, match="client disconnected"):
            asyncio.run(orch.revise("a", "make it smaller"))

        assert orch.store.get("a") is state
        assert orch.bundle_store.get(first_bundle.bundle_id) is first_bundle

    def test_failed_dataframe_materialization_leaves_no_artifact_or_bundle(
        self,
        monkeypatch,
    ):
        source = RecordingDataFrameSource("tips")
        orch = make_session(
            FakeChat([result_chunk("source", referenced_tables=["tips"])]),
            data_sources={"tips": source},
        )
        monkeypatch.setattr("querychat._artifact_data.MAX_BUNDLE_SIZE", 1)

        with pytest.raises(ArtifactDataError, match="exceeds"):
            asyncio.run(
                orch.generate(
                    GenerateRequest(type_id="quarto-dashboard", language="python"),
                    "",
                    "a",
                )
            )

        assert not orch.store.has("a")

    def test_revise_replaces_current_artifact(self):
        orch = make_session(
            FakeChat(
                [
                    result_chunk(
                        "new source",
                        referenced_tables=["mtcars"],
                        summary="s",
                    )
                ]
            )
        )
        state = make_state()
        orch.store.remember(state)

        asyncio.run(orch.revise("a", "make it better"))

        revised = orch.store.get("a")
        assert revised is not None
        assert revised.source == "new source"
        assert revised.summary == "s"
        assert revised.referenced_tables == ["mtcars"]

    def test_revise_replaces_table_references(self):
        orch = make_session(
            FakeChat([result_chunk("new source", referenced_tables=["customers"])]),
            data_sources={
                "orders": FakeDataSource("orders"),
                "customers": FakeDataSource("customers"),
            },
        )
        state = make_state()
        state.referenced_tables = ["orders"]
        orch.store.remember(state)

        asyncio.run(orch.revise("a", "use customers instead"))

        revised = orch.store.get("a")
        assert revised is not None
        assert state.referenced_tables == ["orders"]
        assert revised.referenced_tables == ["customers"]

    def test_revise_rejects_unknown_table_reference(self):
        orch = make_session(
            FakeChat([result_chunk("new source", referenced_tables=["payments"])]),
            data_sources={
                "orders": FakeDataSource("orders"),
                "customers": FakeDataSource("customers"),
            },
        )
        state = make_state()
        orch.store.remember(state)

        with pytest.raises(ValidationError, match="payments"):
            asyncio.run(orch.revise("a", "make it better"))

        assert orch.store.get("a") is state

    def test_revise_rejects_language_change(self):
        orch = make_session(
            FakeChat([result_chunk("new source", language="r")]),
        )
        state = make_state(language="python")
        orch.store.remember(state)

        with pytest.raises(ValidationError, match="language"):
            asyncio.run(orch.revise("a", "rewrite it in R"))

        assert orch.store.get("a") is state

    def test_blank_instructions_is_noop(self):
        orch = make_session(FakeChat(["ignored"]))
        state = make_state()
        orch.store.remember(state)

        asyncio.run(orch.revise("a", ""))

        assert orch.store.get("a") is state

    def test_stream_failure_restores_view_and_reraises(self):
        class BoomChat(FakeChat):
            async def stream_async(self, prompt, echo="none", data_model=None):
                raise RuntimeError("stream blew up")

        orch = make_session(BoomChat([]))
        state = make_state()
        orch.store.remember(state)

        with pytest.raises(RuntimeError, match="stream blew up"):
            asyncio.run(orch.revise("a", "do it"))

        assert orch.store.get("a") is state
        assert "querychat-artifact-source-update" in message_types(orch)

    def test_revision_validation_failure_preserves_current_artifact(self):
        original_source = r_notebook_source()
        invalid = artifact_result_json("{")
        chat = FakeChat(streams=[[invalid], [invalid]])
        orch = make_session(chat)
        state = make_r_notebook_state(original_source)
        orch.store.remember(state)

        with pytest.raises(ArtifactValidationError):
            asyncio.run(orch.revise("a", "change it"))

        assert chat.stream_count == 2
        assert orch.store.get("a") is state
        assert orch.store.get("a").source == original_source


class TestStateFromResult:
    def test_maps_current_artifact_fields(self):
        result = ArtifactResult(
            source="src",
            language="python",
            summary="sum",
            install_instructions="pip install x",
            run_instructions="python artifact.py",
            referenced_tables=["mtcars"],
        )
        context = ArtifactDataContext(
            data_instructions="Load mtcars.csv",
            bundled_files={"mtcars.csv": b"mpg\n20\n"},
            bundled_tables=["mtcars"],
        )
        state = state_from_result(
            result,
            [],
            artifact_id="a",
            artifact_type=resolve_artifact_type("quarto-dashboard", "python"),
            system_prompt="sys",
            data_context=context,
            bundle_id="bundle-1",
        )
        assert state.source == "src"
        assert state.summary == "sum"
        assert state.install_instructions == "pip install x"
        assert state.run_instructions == "python artifact.py"
        assert state.turns == []
        assert state.referenced_tables == ["mtcars"]
        assert state.bundled_tables == ["mtcars"]
        assert state.bundle_id == "bundle-1"
        assert state.data_instructions == "Load mtcars.csv"

    def test_carries_cumulative_turns(self):
        turns = [chatlas.Turn(role="user", contents="hi")]
        result = ArtifactResult(
            source="src2",
            language="python",
            summary="",
            install_instructions="",
            referenced_tables=[],
        )
        context = ArtifactDataContext(data_instructions="Use a database.")
        state = state_from_result(
            result,
            turns,
            artifact_id="a",
            artifact_type=resolve_artifact_type("quarto-dashboard", "python"),
            system_prompt="sys",
            data_context=context,
            bundle_id=None,
        )
        assert state.turns == turns
        assert state.summary == ""


class TestGenerate:
    def test_stores_under_provided_id(self):
        chat = FakeChat(
            [result_chunk("gen src", referenced_tables=["mtcars"], summary="sum")]
        )
        orch = make_session(chat, data_source=FakeDataSource())
        req = GenerateRequest(type_id="quarto-dashboard", language="python")

        asyncio.run(orch.generate(req, "", "myid"))

        assert orch.store.has("myid")
        assert orch.store.get("myid").source == "gen src"

    def test_does_not_change_panel_visibility(self):
        chat = FakeChat(
            [result_chunk("gen src", referenced_tables=["mtcars"], summary="sum")]
        )
        orch = make_session(chat, data_source=FakeDataSource())
        req = GenerateRequest(type_id="quarto-dashboard", language="python")

        asyncio.run(orch.generate(req, "", "myid"))

        assert "querychat-artifact-panel-toggle" not in message_types(orch)

    def test_stores_declared_and_bundled_tables(self):
        source = RecordingDataFrameSource("tips")
        chat = FakeChat([result_chunk("x", referenced_tables=["tips"])])
        orch = make_session(chat, data_sources={"tips": source})
        req = GenerateRequest(type_id="quarto-dashboard", language="python")

        asyncio.run(orch.generate(req, "", "artifact-1"))

        state = orch.store.get("artifact-1")
        assert state is not None
        assert state.referenced_tables == ["tips"]
        assert state.bundled_tables == ["tips"]
        assert state.bundle_id is not None
        assert source.get_data_calls == 1

    def test_stores_resolved_language(self):
        chat = FakeChat(
            [
                result_chunk(
                    "gen src",
                    language="r",
                    referenced_tables=["mtcars"],
                )
            ]
        )
        orch = make_session(chat, data_source=FakeDataSource())

        asyncio.run(
            orch.generate(
                GenerateRequest(type_id="quarto-dashboard", language="r"),
                "",
                "artifact-1",
            )
        )

        state = orch.store.get("artifact-1")
        assert state is not None
        assert state.artifact_type.language == "r"

    def test_explicit_language_selects_registered_target(self):
        chat = FakeChat(
            [
                (
                    '{"source":"{}","language":"r","run_instructions":"```bash\\n'
                    'Rscript artifact.R\\n```","referenced_tables":["mtcars"]}'
                )
            ]
        )
        orch = make_session(chat)

        asyncio.run(
            orch.generate(
                GenerateRequest(type_id="shiny-app", language="r"),
                "",
                "artifact-1",
            )
        )

        state = orch.store.get("artifact-1")
        assert state is not None
        assert state.artifact_type.language == "r"
        assert state.artifact_type.file_extension == ".R"

    def test_failure_discards_provided_id_and_reraises(self):
        class BoomChat(FakeChat):
            async def stream_async(self, prompt, echo="none", data_model=None):
                raise RuntimeError("boom")

        orch = make_session(BoomChat([]), data_source=FakeDataSource())
        req = GenerateRequest(type_id="quarto-dashboard", language="python")

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(orch.generate(req, "", "myid"))

        assert not orch.store.has("myid")

    def test_generation_repairs_invalid_notebook_once(self):
        chat = FakeChat(
            streams=[
                [artifact_result_json("{")],
                [artifact_result_json(r_notebook_source())],
            ]
        )
        orch = make_session(chat)

        asyncio.run(
            orch.generate(
                GenerateRequest(type_id="jupyter-notebook", language="r"),
                "",
                "artifact-1",
            )
        )

        assert chat.stream_count == 2
        assert orch.store.get("artifact-1") is not None

    def test_generation_repair_continues_turns_and_stores_final_result(self):
        invalid = artifact_result_json("{")
        repaired_source = r_notebook_source()
        repaired = artifact_result_json(repaired_source)
        chat = FakeChat(streams=[[invalid], [repaired]])
        orch = make_session(chat)

        asyncio.run(
            orch.generate(
                GenerateRequest(type_id="jupyter-notebook", language="r"),
                "",
                "artifact-1",
            )
        )

        state = orch.store.get("artifact-1")
        assert state is not None
        assert chat.incoming_turns[0] == []
        first_stream_turns = chat.incoming_turns[1]
        assert [turn.role for turn in first_stream_turns] == ["user", "assistant"]
        assert first_stream_turns[-1].text == invalid
        assert state.source == repaired_source
        assert state.turns[:2] == first_stream_turns
        assert "failed structural validation" in state.turns[-2].text
        assert state.turns[-1].text == repaired

    def test_generation_stops_after_second_invalid_result(self):
        invalid = artifact_result_json("{")
        chat = FakeChat(streams=[[invalid], [invalid]])
        orch = make_session(chat)

        with pytest.raises(ArtifactValidationError, match="valid notebook JSON"):
            asyncio.run(
                orch.generate(
                    GenerateRequest(type_id="jupyter-notebook", language="r"),
                    "",
                    "artifact-1",
                )
            )

        assert chat.stream_count == 2
        assert not orch.store.has("artifact-1")
        assert orch.view.session.messages[-1][1] == {
            "root_id": orch.view.panel_root_id,
            "id": orch.view.editor_id,
            "value": "",
            "language": "plain",
            "download_available": False,
        }


class TestPrepareGeneration:
    def test_includes_every_registered_schema(self):
        orch = make_session(
            data_sources={
                "orders": FakeDataSource("orders"),
                "customers": FakeDataSource("customers"),
            }
        )

        plan = asyncio.run(
            orch.prepare_generation(
                GenerateRequest(type_id="quarto-dashboard", language="python"),
                "",
            )
        )

        assert "Table orders" in plan.system_prompt
        assert "Table customers" in plan.system_prompt

    def test_requires_language(self):
        orch = make_session(data_source=FakeDataSource())
        req = GenerateRequest(
            selected_ids=[], type_id="quarto-dashboard", language="", freeform=""
        )

        with pytest.raises(ValueError, match="Select R or Python"):
            asyncio.run(orch.prepare_generation(req, "make it dark"))

    def test_explicit_r_plan_resolves_before_generation(self):
        orch = make_session(data_source=FakeDataSource())

        plan = asyncio.run(
            orch.prepare_generation(
                GenerateRequest(type_id="shiny-app", language="r"),
                "",
            )
        )

        assert plan.artifact_type.file_extension == ".R"
        assert 'Sys.getenv("DATABASE_URL")' in plan.system_prompt
        assert "os.environ" not in plan.system_prompt

    def test_unsupported_explicit_language_is_rejected(self):
        orch = make_session(data_source=FakeDataSource())

        with pytest.raises(ValueError, match="does not support R"):
            asyncio.run(
                orch.prepare_generation(
                    GenerateRequest(type_id="marimo-notebook", language="r"),
                    "",
                )
            )

    def test_unknown_format_is_rejected(self):
        orch = make_session(data_source=FakeDataSource())

        with pytest.raises(ValueError, match="Unknown artifact format: missing"):
            asyncio.run(
                orch.prepare_generation(
                    GenerateRequest(type_id="missing", language="python"),
                    "",
                )
            )

    def test_freeform_plan_preserves_requested_language(self):
        metadata = FreeformMetadata(
            file_extension=".Rmd",
            editor_language="markdown",
        )
        orch = make_session(FakeChat(structured=metadata))

        plan = asyncio.run(
            orch.prepare_generation(
                GenerateRequest(
                    type_id="other",
                    language="r",
                    freeform="R Markdown report",
                ),
                "",
            )
        )

        assert plan.artifact_format is None
        assert plan.artifact_type.language == "r"
        assert plan.artifact_type.structure == "text"
