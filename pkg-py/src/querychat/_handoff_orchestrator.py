"""
Non-reactive business logic for the handoff feature.

`HandoffOrchestrator` owns the handoff store and orchestrates every flow
(recommend, generate, revise, download) by talking to the chat client, data
source, and Shiny session/chat UI directly. It holds no reactive state and
knows nothing about `reactive.Value`, effects, or `input.*` -- that wiring
lives in `_handoff_server.py`, which drives these methods. Keeping the logic
here makes it exercisable with plain fakes.
"""

from __future__ import annotations

import io
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ._handoff_bundle_store import (
    HandoffBundleStore,
    HandoffSnapshotUnavailableError,
)
from ._handoff_chat import HandoffChat
from ._handoff_data import (
    HandoffDataCatalog,
    HandoffDataContext,
    HandoffDataError,
    materialize_handoff_data,
    prepare_handoff_data,
)
from ._handoff_gallery import GalleryItem, extract_gallery_items
from ._handoff_prompt import (
    FreeformMetadata,
    HandoffResult,
    Recommendation,
    build_external_data_repair_system_prompt,
    build_freeform_handoff_user_prompt,
    build_handoff_repair_prompt,
    build_handoff_system_prompt,
    build_handoff_user_prompt,
    build_recommend_prompt,
    handoff_result_model,
    recommendation_model,
)
from ._handoff_readme import build_readme
from ._handoff_state import HandoffState
from ._handoff_store import HandoffStore
from ._handoff_types import (
    HANDOFF_FORMATS,
    LANGUAGES,
    HandoffFormat,
    HandoffLanguage,
    HandoffType,
    resolve_handoff_type,
)
from ._handoff_validation import HandoffValidationError, validate_handoff_source
from ._handoff_view import HandoffView

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
    handoff_format: HandoffFormat | None
    handoff_type: HandoffType
    system_prompt: str
    user_prompt: str
    schema: str
    data_catalog: HandoffDataCatalog
    result_model: type[HandoffResult]


@dataclass(frozen=True)
class GeneratedHandoff:
    result: HandoffResult
    turns: list[chatlas.Turn]
    handoff_type: HandoffType


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


def build_freeform_handoff_type(
    freeform: str,
    metadata: FreeformMetadata,
    language: HandoffLanguage,
) -> HandoffType:
    ext = metadata.file_extension
    if not ext.startswith("."):
        ext = f".{ext}"
    return HandoffType(
        id="other",
        label=freeform,
        language=language,
        file_extension=ext,
        # The LLM-inferred editor language won't match the Literal type statically.
        editor_language=cast("CodeEditorLanguage", metadata.editor_language),
        structure="text",
    )


def state_from_result(
    result: HandoffResult,
    turns: list[chatlas.Turn],
    *,
    handoff_id: str,
    handoff_type: HandoffType,
    system_prompt: str,
    data_context: HandoffDataContext,
    bundle_id: str | None,
) -> HandoffState:
    return HandoffState(
        handoff_id=handoff_id,
        handoff_type=handoff_type,
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


def parse_handoff_language(language: str) -> HandoffLanguage:
    if not language:
        raise ValueError("Select R or Python before generating a handoff.")
    if language not in LANGUAGES:
        raise ValueError(f"Unknown handoff language: {language}")
    return cast("HandoffLanguage", language)


def build_handoff_zip(
    source: str,
    source_filename: str,
    readme: str,
    bundled_files: dict[str, bytes],
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(source_filename, source)
        zf.writestr("README.md", readme)
        # source_filename is always "handoff.<ext>" and bundled_files are keyed
        # as "<table>.csv", so they never collide with the entries above.
        for name, data in bundled_files.items():
            zf.writestr(name, data)
    return buf.getvalue()


class HandoffOrchestrator:
    """
    Owns the handoff store and orchestrates every handoff flow.

    All methods are plain (non-reactive) coroutines: they read no reactive
    values and define no effects. The reactive layer reads `input.*`, manages
    `active_handoff_id`, and calls these methods.
    """

    def __init__(
        self,
        session: Session,
        chat: chatlas.Chat,
        data_sources: dict[str, DataSource],
        executor: QueryExecutor,
        chat_ui: shinychat.Chat,
    ) -> None:
        self.chat = HandoffChat(chat)
        self.data_sources = data_sources
        self.executor = executor
        self.view = HandoffView(session, chat_ui)
        self.store = HandoffStore()
        self.bundle_store = HandoffBundleStore()
        self.gallery_items: list[GalleryItem] = []
        self.default_type_id = next(iter(HANDOFF_FORMATS))

    def restore_snapshot(self, saved: list[dict]) -> None:
        """Rebuild the handoff store from persisted handoff metadata."""
        states = [HandoffState.model_validate(data) for data in saved]
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
            handoff_formats=HANDOFF_FORMATS,
        )
        model = recommendation_model(
            item_ids=[item.id for item in items],
            format_ids=list(HANDOFF_FORMATS),
        )
        return await self.chat.ask(prompt, model)

    async def prepare_generation(
        self, req: GenerateRequest, directions: str
    ) -> GenerationPlan:
        language = parse_handoff_language(req.language)
        handoff_format: HandoffFormat | None
        handoff_type: HandoffType | None
        if req.type_id == "other":
            metadata = await self.chat.ask(
                f"What file extension and editor language should be used for a '{req.freeform}' handoff?",
                FreeformMetadata,
            )
            handoff_format = None
            handoff_type = build_freeform_handoff_type(
                req.freeform,
                metadata,
                language,
            )
        else:
            handoff_format = HANDOFF_FORMATS.get(req.type_id)
            if handoff_format is None:
                raise ValueError(f"Unknown handoff format: {req.type_id}")
            handoff_type = resolve_handoff_type(handoff_format.id, language)
        selected_items = [
            item for item in self.gallery_items if item.id in req.selected_ids
        ]
        schema = "\n\n".join(
            self.executor.get_schema(name, categorical_threshold=20)
            for name in self.data_sources
        )
        data_catalog = prepare_handoff_data(
            self.data_sources,
            language=language,
        )

        system_prompt = build_handoff_system_prompt(
            selected_items=selected_items,
            schema=schema,
            custom_directions=directions,
            format_id=handoff_format.id if handoff_format is not None else "other",
            language=language,
            data_instructions=data_catalog.prompt_instructions,
        )
        user_prompt = (
            build_freeform_handoff_user_prompt(req.freeform, language)
            if handoff_format is None
            else build_handoff_user_prompt(
                handoff_format,
                language,
            )
        )
        return GenerationPlan(
            handoff_format=handoff_format,
            handoff_type=handoff_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            data_catalog=data_catalog,
            result_model=handoff_result_model(
                list(self.data_sources),
                (language,),
                require_run_instructions=True,
            ),
        )

    async def generate(
        self, req: GenerateRequest, directions: str, handoff_id: str
    ) -> None:
        """
        Generate a new handoff under `handoff_id`. Raises on failure.

        The caller owns the id, panel visibility, and persistence; generation
        streams the source and stores the completed handoff.
        """
        plan = await self.prepare_generation(req, directions)

        self.view.remove_modal()
        await self.view.clear_editor(plan.handoff_type.editor_language)

        bundle_id: str | None = None
        committed = False
        try:
            generated = await self._stream_validated(
                prompt=plan.user_prompt,
                turns=[],
                system_prompt=plan.system_prompt,
                result_model=plan.result_model,
                handoff_type=plan.handoff_type,
            )
            generated, data_context = await self._materialize_generated(
                generated,
                data_catalog=plan.data_catalog,
                schema=plan.schema,
                result_model=plan.result_model,
            )
            if data_context.bundled_files:
                bundle_id = self.bundle_store.stage(
                    data_context.bundled_files,
                ).bundle_id
            state = state_from_result(
                generated.result,
                generated.turns,
                handoff_id=handoff_id,
                handoff_type=generated.handoff_type,
                system_prompt=plan.system_prompt,
                data_context=data_context,
                bundle_id=bundle_id,
            )
            await self.view.show_handoff(
                state,
                download_available=False,
            )
            await self.view.append_pill(
                handoff_id,
                generated.handoff_type,
                generated.result.summary,
            )
            removed_states = self.store.remember(state)
            committed = True
            self._discard_unreferenced_bundles(
                removed_state.bundle_id for removed_state in removed_states
            )
            self.bundle_store.evict()
            download_available = self._download_available(state)
            with suppress(Exception):
                await self.view.show_handoff(
                    state,
                    download_available=download_available,
                )
        except Exception:
            if not committed:
                self.bundle_store.discard(bundle_id)
                await self.view.clear_editor("plain")
            raise

    async def _stream_validated(
        self,
        *,
        prompt: str,
        turns: list[chatlas.Turn],
        system_prompt: str,
        result_model: type[HandoffResult],
        handoff_type: HandoffType,
    ) -> GeneratedHandoff:
        result, result_turns = await self.chat.stream(
            prompt,
            turns=turns,
            system_prompt=system_prompt,
            sink=self.view,
            model=result_model,
        )
        try:
            validate_handoff_source(result.source, handoff_type)
        except HandoffValidationError as error:
            repair_model = handoff_result_model(
                list(self.data_sources),
                (handoff_type.language,),
                require_run_instructions=True,
            )
            result, result_turns = await self.chat.stream(
                build_handoff_repair_prompt(error, handoff_type),
                turns=result_turns,
                system_prompt=system_prompt,
                sink=self.view,
                model=repair_model,
            )
            if result.language != handoff_type.language:
                raise ValueError("Repaired handoff changed its language.") from error
            validate_handoff_source(result.source, handoff_type)
        return GeneratedHandoff(
            result=result,
            turns=result_turns,
            handoff_type=handoff_type,
        )

    async def _materialize_generated(
        self,
        generated: GeneratedHandoff,
        *,
        data_catalog: HandoffDataCatalog,
        schema: str,
        result_model: type[HandoffResult],
    ) -> tuple[GeneratedHandoff, HandoffDataContext]:
        data_context = materialize_handoff_data(
            data_catalog,
            self.data_sources,
            generated.result.referenced_tables,
        )
        if not data_context.externalized_dataframe_tables:
            return generated, data_context

        expected_tables = set(generated.result.referenced_tables)
        repair_system_prompt = build_external_data_repair_system_prompt(
            handoff_type=generated.handoff_type,
            schema=schema,
            data_instructions=data_context.data_instructions,
            referenced_tables=generated.result.referenced_tables,
        )
        try:
            repaired_result, repaired_turns = await self.chat.stream(
                "Return the complete corrected handoff now.",
                turns=generated.turns,
                system_prompt=repair_system_prompt,
                sink=self.view,
                model=result_model,
            )
        except ValidationError as error:
            error_roots = {
                detail["loc"][0] for detail in error.errors() if detail["loc"]
            }
            if "language" in error_roots:
                raise HandoffDataError(
                    "Corrected handoff changed its language."
                ) from error
            if "referenced_tables" in error_roots:
                raise HandoffDataError(
                    "Corrected handoff changed its referenced-table set."
                ) from error
            raise
        if repaired_result.language != generated.handoff_type.language:
            raise HandoffDataError("Corrected handoff changed its language.")
        if set(repaired_result.referenced_tables) != expected_tables:
            raise HandoffDataError(
                "Corrected handoff changed its referenced-table set."
            )
        validate_handoff_source(repaired_result.source, generated.handoff_type)
        return (
            GeneratedHandoff(
                result=repaired_result,
                turns=repaired_turns,
                handoff_type=generated.handoff_type,
            ),
            data_context,
        )

    async def show_handoff(self, handoff_id: str | None) -> None:
        state = self.store.get(handoff_id)
        if state is not None:
            await self.view.show_handoff(
                state,
                download_available=self._download_available(state),
            )

    async def revise(self, handoff_id: str | None, instructions: str) -> None:
        state = self.store.get(handoff_id)
        if state is None or not instructions:
            return
        language = state.handoff_type.language
        schema = "\n\n".join(
            self.executor.get_schema(name, categorical_threshold=20)
            for name in self.data_sources
        )
        data_catalog = prepare_handoff_data(
            self.data_sources,
            language=language,
        )
        result_model = handoff_result_model(
            list(self.data_sources),
            (language,),
            require_run_instructions=True,
        )

        def resolve_type(result: HandoffResult) -> HandoffType:
            if result.language != language:
                raise ValueError("Revised handoff changed its language.")
            return state.handoff_type

        bundle_id: str | None = None
        replacement_saved = False
        try:
            generated = await self._stream_validated(
                prompt=instructions,
                turns=state.turns,
                system_prompt=state.system_prompt,
                result_model=result_model,
                handoff_type=state.handoff_type,
            )
            generated, data_context = await self._materialize_generated(
                generated,
                data_catalog=data_catalog,
                schema=schema,
                result_model=result_model,
            )
            if data_context.bundled_files:
                bundle_id = self.bundle_store.stage(
                    data_context.bundled_files,
                ).bundle_id
            replacement = state_from_result(
                generated.result,
                generated.turns,
                handoff_id=state.handoff_id,
                handoff_type=state.handoff_type,
                system_prompt=state.system_prompt,
                data_context=data_context,
                bundle_id=bundle_id,
            )
            await self.view.show_handoff(
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
            await self.view.show_handoff(
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

    def _download_available(self, state: HandoffState) -> bool:
        if state.bundle_id is None:
            return not state.bundled_tables
        return self.bundle_store.get(state.bundle_id) is not None

    async def build_download(self, handoff_id: str | None) -> bytes | None:
        state = self.store.get(handoff_id)
        if state is None:
            return None
        if state.bundle_id is None:
            if state.bundled_tables:
                raise HandoffSnapshotUnavailableError(
                    "This handoff data snapshot is unavailable."
                )
            bundled_files: dict[str, bytes] = {}
        else:
            bundle = self.bundle_store.get(state.bundle_id)
            if bundle is None:
                raise HandoffSnapshotUnavailableError(
                    "This handoff data snapshot is unavailable."
                )
            bundled_files = dict(bundle.bundled_files)
        source_filename = f"handoff{state.handoff_type.file_extension}"
        readme = build_readme(
            handoff_type=state.handoff_type,
            source_filename=source_filename,
            summary=state.summary,
            install_instructions=state.install_instructions,
            run_instructions=state.run_instructions,
            data_instructions=state.data_instructions,
            bundled_files=list(bundled_files),
        )
        return build_handoff_zip(
            source=state.source,
            source_filename=source_filename,
            readme=readme,
            bundled_files=bundled_files,
        )
