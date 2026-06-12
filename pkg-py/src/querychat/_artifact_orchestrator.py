"""
Non-reactive business logic for the artifact feature.

`ArtifactOrchestrator` owns the artifact store and orchestrates every flow
(recommend, generate, revise, version navigation, download) by talking
to the chat client, data source, and Shiny session/chat UI directly. It holds
no reactive state and knows nothing about `reactive.Value`, effects, or
`input.*` — that wiring lives in `_artifact_server.py`, which drives these
methods. Keeping the logic here makes it exercisable with plain fakes.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._artifact_chat import ArtifactChat
from ._artifact_data import ArtifactDataContext, get_artifact_data_context
from ._artifact_gallery import GalleryItem, extract_gallery_items
from ._artifact_prompt import (
    ArtifactResult,
    FreeformMetadata,
    Recommendation,
    build_artifact_system_prompt,
    build_artifact_user_prompt,
    build_recommend_prompt,
    recommendation_model,
)
from ._artifact_readme import build_readme
from ._artifact_state import (
    ArtifactState,
    ArtifactVersion,
    VersionKind,
)
from ._artifact_store import ArtifactStore
from ._artifact_types import (
    ARTIFACT_TYPES,
    LANGUAGES,
    ArtifactType,
    resolve_for_language,
)
from ._artifact_view import ArtifactView

if TYPE_CHECKING:
    import chatlas
    import shinychat
    from shiny.ui._input_code_editor import CodeEditorLanguage

    from shiny import Session

    from ._datasource import DataSource


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
    artifact_type: ArtifactType
    system_prompt: str
    user_prompt: str
    data_context: ArtifactDataContext


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
    freeform: str, metadata: FreeformMetadata
) -> ArtifactType:
    ext = metadata.file_extension
    if not ext.startswith("."):
        ext = f".{ext}"
    return ArtifactType(
        id="other",
        label=freeform,
        file_extension=ext,
        description="",
        # The LLM-inferred language won't match the Literal type statically.
        editor_language=cast("CodeEditorLanguage", metadata.editor_language),
        run_instructions=metadata.run_instructions,
    )


def version_from_result(
    result: ArtifactResult, turns: list[chatlas.Turn], kind: VersionKind
) -> ArtifactVersion:
    return ArtifactVersion(
        source=result.source,
        turns=turns,
        kind=kind,
        summary=result.summary,
        install_instructions=result.install_instructions,
    )


def format_language_label(art_type: ArtifactType, language: str) -> str:
    if language in art_type.supported_languages:
        return LANGUAGES.get(language, "")
    return ""


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
        data_source: DataSource,
        chat_ui: shinychat.Chat,
    ) -> None:
        self.chat = ArtifactChat(chat)
        self.data_source = data_source
        self.view = ArtifactView(session, chat_ui)
        self.store = ArtifactStore()
        self.gallery_items: list[GalleryItem] = []
        self.default_type_id = next(iter(ARTIFACT_TYPES.keys()))

    def restore_from_bookmark(self, saved: list[dict]) -> None:
        """
        Rebuild the store from `bookmark_values` output.

        Bundled download data is regenerated from the current data source rather
        than carried through the bookmark, mirroring how visualization widgets
        re-execute their ggsql on restore.
        """
        data_context = get_artifact_data_context(self.data_source)
        for data in saved:
            state = ArtifactState.model_validate(data)
            state.bundled_files = data_context.bundled_files
            state.data_instructions = data_context.data_instructions
            self.store.remember(state)

    def open_modal(self) -> list[GalleryItem]:
        """Extract gallery items from chat history, stash them, and show the modal."""
        items = extract_gallery_items(self.chat.history_turns())
        self.gallery_items = items
        self.view.show_modal(items)
        return items

    async def recommend(self, items: list[GalleryItem]) -> Recommendation:
        prompt = build_recommend_prompt(items=items, artifact_types=ARTIFACT_TYPES)
        model = recommendation_model(
            item_ids=[item.id for item in items],
            format_ids=list(ARTIFACT_TYPES.keys()),
        )
        return await self.chat.ask(prompt, model)

    async def resolve_artifact_type(self, req: GenerateRequest) -> ArtifactType:
        if req.type_id == "other":
            metadata = await self.chat.ask(
                f"What file extension, editor language, and run command should be used for a '{req.freeform}' artifact?",
                FreeformMetadata,
            )
            art_type = build_freeform_artifact_type(req.freeform, metadata)
        else:
            art_type = ARTIFACT_TYPES.get(
                req.type_id, ARTIFACT_TYPES[self.default_type_id]
            )
        return resolve_for_language(art_type, req.language)

    async def prepare_generation(
        self, req: GenerateRequest, directions: str
    ) -> GenerationPlan:
        art_type = await self.resolve_artifact_type(req)
        selected_items = [
            item for item in self.gallery_items if item.id in req.selected_ids
        ]
        language_label = format_language_label(art_type, req.language)
        schema = self.data_source.get_schema(categorical_threshold=20)
        data_context = get_artifact_data_context(self.data_source)

        system_prompt = build_artifact_system_prompt(
            selected_items=selected_items,
            schema=schema,
            custom_directions=directions,
            data_instructions=data_context.data_instructions,
            language_label=language_label,
        )
        user_prompt = build_artifact_user_prompt(
            art_type, language_label=language_label
        )
        return GenerationPlan(
            artifact_type=art_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            data_context=data_context,
        )

    async def generate(
        self, req: GenerateRequest, directions: str, artifact_id: str
    ) -> None:
        """
        Generate a new artifact under `artifact_id`. Raises on failure.

        The caller (the reactive server layer) owns the id and the
        `active_artifact_id` reactive that drives panel visibility, so this
        method never opens the panel itself.
        """
        plan = await self.prepare_generation(req, directions)

        self.view.remove_modal()
        await self.view.clear_editor(plan.artifact_type.editor_language)

        try:
            result, turns = await self.chat.stream(
                plan.user_prompt,
                turns=[],
                system_prompt=plan.system_prompt,
                sink=self.view,
            )
            state = ArtifactState(
                artifact_id=artifact_id,
                artifact_type=plan.artifact_type,
                system_prompt=plan.system_prompt,
                versions=[version_from_result(result, turns, "generated")],
                bundled_files=plan.data_context.bundled_files,
                data_instructions=plan.data_context.data_instructions,
            )
            self.store.remember(state)
            await self.view.show_version(state)
            await self.view.append_pill(
                artifact_id, plan.artifact_type, result.summary
            )
        except Exception:
            self.store.discard(artifact_id)
            raise

    async def show_version(self, artifact_id: str | None) -> None:
        state = self.store.get(artifact_id)
        if state is not None:
            await self.view.show_version(state)

    async def step_version(self, artifact_id: str | None, delta: int) -> None:
        state = self.store.get(artifact_id)
        if state is None:
            return
        state.step(delta)
        await self.view.show_version(state)

    async def revise(self, artifact_id: str | None, instructions: str) -> None:
        state = self.store.get(artifact_id)
        if state is None or not instructions:
            return
        try:
            result, turns = await self.chat.stream(
                instructions,
                turns=state.turns,
                system_prompt=state.system_prompt,
                sink=self.view,
            )
            state.push_version(version_from_result(result, turns, "revised"))
            await self.view.show_version(state)
        except Exception:
            # A failed stream may have left a partial rewrite in the editor;
            # restore the current version before surfacing the error.
            await self.view.show_version(state)
            raise

    async def build_download(self, artifact_id: str | None) -> bytes | None:
        state = self.store.get(artifact_id)
        if state is None:
            return None
        source_filename = f"artifact{state.artifact_type.file_extension}"
        readme = build_readme(
            artifact_type=state.artifact_type,
            source_filename=source_filename,
            summary=state.summary,
            install_instructions=state.install_instructions,
            data_instructions=state.data_instructions,
            bundled_files=list(state.bundled_files.keys()),
        )
        return build_artifact_zip(
            source=state.source,
            source_filename=source_filename,
            readme=readme,
            bundled_files=state.bundled_files,
        )
