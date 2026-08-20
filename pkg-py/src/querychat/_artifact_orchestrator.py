"""
Non-reactive business logic for the artifact feature.

`ArtifactOrchestrator` owns the artifact store and orchestrates every flow
(recommend, generate, revise, download) by talking to the chat client, data
source, and Shiny session/chat UI directly. It holds no reactive state and
knows nothing about `reactive.Value`, effects, or `input.*` -- that wiring
lives in `_artifact_server.py`, which drives these methods. Keeping the logic
here makes it exercisable with plain fakes.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._artifact_bundle_store import (
    ArtifactBundleStore,
    ArtifactSnapshotUnavailableError,
)
from ._artifact_chat import ArtifactChat
from ._artifact_data import (
    ArtifactDataCatalog,
    ArtifactDataContext,
    materialize_artifact_data,
    prepare_artifact_data,
)
from ._artifact_gallery import GalleryItem, extract_gallery_items
from ._artifact_prompt import (
    ArtifactResult,
    FreeformMetadata,
    Recommendation,
    artifact_result_model,
    build_artifact_repair_prompt,
    build_artifact_system_prompt,
    build_artifact_user_prompt,
    build_freeform_artifact_user_prompt,
    build_recommend_prompt,
    recommendation_model,
)
from ._artifact_readme import build_readme
from ._artifact_state import ArtifactState
from ._artifact_store import ArtifactStore
from ._artifact_types import (
    ARTIFACT_FORMATS,
    LANGUAGES,
    ArtifactFormat,
    ArtifactLanguage,
    ArtifactType,
    resolve_artifact_type,
)
from ._artifact_validation import ArtifactValidationError, validate_artifact_source
from ._artifact_view import ArtifactView

if TYPE_CHECKING:
    from collections.abc import Iterable

    import chatlas
    import shinychat
    from shiny.ui._input_code_editor import CodeEditorLanguage

    from shiny import Session

    from ._datasource import DataSource
    from ._query_executor import QueryExecutor


class GenerateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    selected_ids: list[str] = Field(default_factory=list)
    type_id: str = Field(default="", alias="type")
    language: str = ""
    freeform: str = ""

    @field_validator("selected_ids", mode="before")
    @classmethod
    def coerce_ids(cls, v: object) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(x) for x in v]

    @field_validator("type_id", "language", mode="before")
    @classmethod
    def coerce_str(cls, v: object) -> str:
        return str(v) if v else ""

    @field_validator("freeform", mode="before")
    @classmethod
    def coerce_freeform(cls, v: object) -> str:
        return str(v).strip() if v else ""


@dataclass(frozen=True)
class GenerationPlan:
    artifact_format: ArtifactFormat | None
    artifact_type: ArtifactType
    system_prompt: str
    user_prompt: str
    data_catalog: ArtifactDataCatalog
    result_model: type[ArtifactResult]


@dataclass(frozen=True)
class GeneratedArtifact:
    result: ArtifactResult
    turns: list[chatlas.Turn]
    artifact_type: ArtifactType


def parse_generate_payload(raw: object, default_type: str) -> GenerateRequest:
    """
    Parse the JS-supplied Generate event payload into a typed request.

    The client gathers modal state (selected gallery IDs, chosen format,
    language, freeform name) into one event input.
    """
    if not isinstance(raw, dict):
        return GenerateRequest.model_validate({"type": default_type})
    req = GenerateRequest.model_validate(raw)
    if not req.type_id:
        return GenerateRequest.model_validate({**raw, "type": default_type})
    return req


def build_freeform_artifact_type(
    freeform: str,
    metadata: FreeformMetadata,
    language: ArtifactLanguage,
) -> ArtifactType:
    ext = metadata.file_extension
    if not ext.startswith("."):
        ext = f".{ext}"
    return ArtifactType(
        id="other",
        label=freeform,
        language=language,
        file_extension=ext,
        # The LLM-inferred editor language won't match the Literal type statically.
        editor_language=cast("CodeEditorLanguage", metadata.editor_language),
        structure="text",
    )


def state_from_result(
    result: ArtifactResult,
    turns: list[chatlas.Turn],
    *,
    artifact_id: str,
    artifact_type: ArtifactType,
    system_prompt: str,
    data_context: ArtifactDataContext,
    bundle_id: str | None,
) -> ArtifactState:
    return ArtifactState(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        system_prompt=system_prompt,
        source=result.source,
        turns=turns,
        summary=result.summary,
        install_instructions=result.install_instructions,
        run_instructions=result.run_instructions,
        referenced_tables=result.referenced_tables,
        bundled_tables=data_context.bundled_tables,
        bundle_id=bundle_id,
        data_instructions=data_context.data_instructions,
    )


def parse_artifact_language(language: str) -> ArtifactLanguage:
    if not language:
        raise ValueError("Select R or Python before generating an artifact.")
    if language not in LANGUAGES:
        raise ValueError(f"Unknown artifact language: {language}")
    return cast("ArtifactLanguage", language)


def build_artifact_zip(
    source: str,
    source_filename: str,
    readme: str,
    bundled_files: dict[str, bytes],
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(source_filename, source)
        zf.writestr("README.md", readme)
        # source_filename is always "artifact.<ext>" and bundled_files are keyed
        # as "<table>.csv", so they never collide with the entries above.
        for name, data in bundled_files.items():
            zf.writestr(name, data)
    return buf.getvalue()


class ArtifactOrchestrator:
    """
    Owns the artifact store and orchestrates every artifact flow.

    All methods are plain (non-reactive) coroutines: they read no reactive
    values and define no effects. The reactive layer reads `input.*`, manages
    `active_artifact_id`, and calls these methods.
    """

    def __init__(
        self,
        session: Session,
        chat: chatlas.Chat,
        data_sources: dict[str, DataSource],
        executor: QueryExecutor,
        chat_ui: shinychat.Chat,
    ) -> None:
        self.chat = ArtifactChat(chat)
        self.data_sources = data_sources
        self.executor = executor
        self.view = ArtifactView(session, chat_ui)
        self.store = ArtifactStore()
        self.bundle_store = ArtifactBundleStore()
        self.gallery_items: list[GalleryItem] = []
        self.default_type_id = next(iter(ARTIFACT_FORMATS))

    def restore_snapshot(self, saved: list[dict]) -> None:
        """Rebuild the artifact store from persisted artifact metadata."""
        states = [ArtifactState.model_validate(data) for data in saved]
        self.store.replace(states)

    def open_modal(self) -> list[GalleryItem]:
        """Extract gallery items from chat history, stash them, and show the modal."""
        items = extract_gallery_items(self.chat.history_turns())
        self.gallery_items = items
        self.view.show_modal(items)
        return items

    async def recommend(self, items: list[GalleryItem]) -> Recommendation:
        prompt = build_recommend_prompt(
            items=items,
            artifact_formats=ARTIFACT_FORMATS,
        )
        model = recommendation_model(
            item_ids=[item.id for item in items],
            format_ids=list(ARTIFACT_FORMATS),
        )
        return await self.chat.ask(prompt, model)

    async def prepare_generation(
        self, req: GenerateRequest, directions: str
    ) -> GenerationPlan:
        language = parse_artifact_language(req.language)
        artifact_format: ArtifactFormat | None
        artifact_type: ArtifactType | None
        if req.type_id == "other":
            metadata = await self.chat.ask(
                f"What file extension and editor language should be used for a '{req.freeform}' artifact?",
                FreeformMetadata,
            )
            artifact_format = None
            artifact_type = build_freeform_artifact_type(
                req.freeform,
                metadata,
                language,
            )
        else:
            artifact_format = ARTIFACT_FORMATS.get(req.type_id)
            if artifact_format is None:
                raise ValueError(f"Unknown artifact format: {req.type_id}")
            artifact_type = resolve_artifact_type(artifact_format.id, language)
        selected_items = [
            item for item in self.gallery_items if item.id in req.selected_ids
        ]
        schema = "\n\n".join(
            self.executor.get_schema(name, categorical_threshold=20)
            for name in self.data_sources
        )
        data_catalog = prepare_artifact_data(
            self.data_sources,
            language=language,
        )

        system_prompt = build_artifact_system_prompt(
            selected_items=selected_items,
            schema=schema,
            custom_directions=directions,
            format_id=artifact_format.id if artifact_format is not None else "other",
            language=language,
            data_instructions=data_catalog.prompt_instructions,
        )
        user_prompt = (
            build_freeform_artifact_user_prompt(req.freeform, language)
            if artifact_format is None
            else build_artifact_user_prompt(
                artifact_format,
                language,
            )
        )
        return GenerationPlan(
            artifact_format=artifact_format,
            artifact_type=artifact_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            data_catalog=data_catalog,
            result_model=artifact_result_model(
                list(self.data_sources),
                (language,),
                require_run_instructions=True,
            ),
        )

    async def generate(
        self, req: GenerateRequest, directions: str, artifact_id: str
    ) -> None:
        """
        Generate a new artifact under `artifact_id`. Raises on failure.

        The caller owns the id, panel visibility, and persistence; generation
        streams the source and stores the completed artifact.
        """
        plan = await self.prepare_generation(req, directions)

        self.view.remove_modal()
        await self.view.clear_editor(plan.artifact_type.editor_language)

        bundle_id: str | None = None
        try:
            generated = await self._stream_validated(
                prompt=plan.user_prompt,
                turns=[],
                system_prompt=plan.system_prompt,
                result_model=plan.result_model,
                artifact_type=plan.artifact_type,
            )
            data_context = materialize_artifact_data(
                plan.data_catalog,
                self.data_sources,
                generated.result.referenced_tables,
            )
            if data_context.bundled_files:
                bundle_id = self.bundle_store.put(
                    data_context.bundled_files,
                ).bundle_id
            state = state_from_result(
                generated.result,
                generated.turns,
                artifact_id=artifact_id,
                artifact_type=generated.artifact_type,
                system_prompt=plan.system_prompt,
                data_context=data_context,
                bundle_id=bundle_id,
            )
            removed_states = self.store.remember(state)
            self._discard_unreferenced_bundles(
                removed_state.bundle_id for removed_state in removed_states
            )
            await self.view.show_artifact(
                state,
                download_available=self._download_available(state),
            )
            await self.view.append_pill(
                artifact_id,
                generated.artifact_type,
                generated.result.summary,
            )
        except Exception:
            self.store.discard(artifact_id)
            self.bundle_store.discard(bundle_id)
            await self.view.clear_editor("plain")
            raise

    async def _stream_validated(
        self,
        *,
        prompt: str,
        turns: list[chatlas.Turn],
        system_prompt: str,
        result_model: type[ArtifactResult],
        artifact_type: ArtifactType,
    ) -> GeneratedArtifact:
        result, result_turns = await self.chat.stream(
            prompt,
            turns=turns,
            system_prompt=system_prompt,
            sink=self.view,
            model=result_model,
        )
        try:
            validate_artifact_source(result.source, artifact_type)
        except ArtifactValidationError as error:
            repair_model = artifact_result_model(
                list(self.data_sources),
                (artifact_type.language,),
                require_run_instructions=True,
            )
            result, result_turns = await self.chat.stream(
                build_artifact_repair_prompt(error, artifact_type),
                turns=result_turns,
                system_prompt=system_prompt,
                sink=self.view,
                model=repair_model,
            )
            if result.language != artifact_type.language:
                raise ValueError("Repaired artifact changed its language.") from error
            validate_artifact_source(result.source, artifact_type)
        return GeneratedArtifact(
            result=result,
            turns=result_turns,
            artifact_type=artifact_type,
        )

    async def show_artifact(self, artifact_id: str | None) -> None:
        state = self.store.get(artifact_id)
        if state is not None:
            await self.view.show_artifact(
                state,
                download_available=self._download_available(state),
            )

    async def revise(self, artifact_id: str | None, instructions: str) -> None:
        state = self.store.get(artifact_id)
        if state is None or not instructions:
            return
        language = state.artifact_type.language
        data_catalog = prepare_artifact_data(
            self.data_sources,
            language=language,
        )
        result_model = artifact_result_model(
            list(self.data_sources),
            (language,),
            require_run_instructions=True,
        )

        def resolve_type(result: ArtifactResult) -> ArtifactType:
            if result.language != language:
                raise ValueError("Revised artifact changed its language.")
            return state.artifact_type

        bundle_id: str | None = None
        replacement_saved = False
        try:
            generated = await self._stream_validated(
                prompt=instructions,
                turns=state.turns,
                system_prompt=state.system_prompt,
                result_model=result_model,
                artifact_type=state.artifact_type,
            )
            data_context = materialize_artifact_data(
                data_catalog,
                self.data_sources,
                generated.result.referenced_tables,
            )
            if data_context.bundled_files:
                bundle_id = self.bundle_store.stage(
                    data_context.bundled_files,
                ).bundle_id
            replacement = state_from_result(
                generated.result,
                generated.turns,
                artifact_id=state.artifact_id,
                artifact_type=state.artifact_type,
                system_prompt=state.system_prompt,
                data_context=data_context,
                bundle_id=bundle_id,
            )
            await self.view.show_artifact(
                replacement,
                download_available=self._download_available(replacement),
            )
            removed_states = self.store.remember(replacement)
            replacement_saved = True
            self._discard_unreferenced_bundles(
                removed_state.bundle_id for removed_state in removed_states
            )
            self.bundle_store.evict()
        except Exception:
            if not replacement_saved:
                self.bundle_store.discard(bundle_id)
            await self.view.show_artifact(
                state,
                download_available=self._download_available(state),
            )
            raise

    def _discard_unreferenced_bundles(
        self,
        bundle_ids: Iterable[str | None],
    ) -> None:
        retained = {
            state.bundle_id
            for state in self.store.values()
            if state.bundle_id is not None
        }
        for bundle_id in set(bundle_ids) - retained:
            self.bundle_store.discard(bundle_id)

    def _download_available(self, state: ArtifactState) -> bool:
        if state.bundle_id is None:
            return not state.bundled_tables
        return self.bundle_store.get(state.bundle_id) is not None

    async def build_download(self, artifact_id: str | None) -> bytes | None:
        state = self.store.get(artifact_id)
        if state is None:
            return None
        if state.bundle_id is None:
            if state.bundled_tables:
                raise ArtifactSnapshotUnavailableError(
                    "This artifact data snapshot is unavailable."
                )
            bundled_files: dict[str, bytes] = {}
        else:
            bundle = self.bundle_store.get(state.bundle_id)
            if bundle is None:
                raise ArtifactSnapshotUnavailableError(
                    "This artifact data snapshot is unavailable."
                )
            bundled_files = dict(bundle.bundled_files)
        source_filename = f"artifact{state.artifact_type.file_extension}"
        readme = build_readme(
            artifact_type=state.artifact_type,
            source_filename=source_filename,
            summary=state.summary,
            install_instructions=state.install_instructions,
            run_instructions=state.run_instructions,
            data_instructions=state.data_instructions,
            bundled_files=list(bundled_files),
        )
        return build_artifact_zip(
            source=state.source,
            source_filename=source_filename,
            readme=readme,
            bundled_files=bundled_files,
        )
