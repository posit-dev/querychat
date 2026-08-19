"""
Server→client output for the artifact feature.

`ArtifactView` is the single place all artifact UI output lives: the
`querychat-artifact-*` custom messages (the wire contract with
`static/js/artifact.js`), the wizard modal, and the chat pill. It wraps the
Shiny `Session` and chat UI plus the namespaced ids the messages target, so
callers express intent (`view.show_version(state)`, `view.append_pill(...)`)
rather than touching `shiny`/`shinychat` directly. It holds no reactive state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shiny import ui

from ._artifact_modal import build_modal_ui
from ._artifact_panel import render_pill_html
from ._artifact_protocol import (
    ArtifactMessage,
    PanelToggleMessage,
    RecommendationErrorMessage,
    RecommendationMessage,
    SourceUpdateMessage,
    StreamingMessage,
    VersionUpdateMessage,
)

if TYPE_CHECKING:
    import shinychat

    from shiny import Session

    from ._artifact_gallery import GalleryItem
    from ._artifact_prompt import Recommendation
    from ._artifact_state import ArtifactState
    from ._artifact_types import ArtifactType


class ArtifactView:
    def __init__(self, session: Session, chat_ui: shinychat.Chat) -> None:
        self.session = session
        self.chat_ui = chat_ui
        self.panel_root_id = session.ns("artifact_root")
        self.modal_root_id = session.ns("artifact_modal_root")
        self.editor_id = session.ns("artifact_source_editor")
        self.directions_id = session.ns("artifact_directions")
        self.open_input_id = session.ns("artifact_open")

    async def _send(self, message: ArtifactMessage) -> None:
        await self.session.send_custom_message(
            message.message_type(),
            message.payload(),
        )

    async def set_panel_open(self, *, is_open: bool) -> None:
        await self._send(
            PanelToggleMessage(root_id=self.panel_root_id, open=is_open)
        )

    async def clear_editor(self, language: str) -> None:
        await self._send(
            SourceUpdateMessage(
                root_id=self.panel_root_id,
                id=self.editor_id,
                value="",
                language=language,
            )
        )

    async def update_source(self, value: str) -> None:
        await self._send(
            SourceUpdateMessage(
                root_id=self.panel_root_id,
                id=self.editor_id,
                value=value,
            )
        )

    async def set_streaming(self, *, active: bool) -> None:
        await self._send(
            StreamingMessage(root_id=self.panel_root_id, active=active)
        )

    async def show_version(
        self,
        state: ArtifactState,
        *,
        download_available: bool,
    ) -> None:
        await self._send(
            SourceUpdateMessage(
                root_id=self.panel_root_id,
                id=self.editor_id,
                value=state.source,
                language=state.artifact_type.editor_language,
            )
        )
        await self._send(
            VersionUpdateMessage(
                root_id=self.panel_root_id,
                label=f"v{state.current_index + 1} of {state.total}",
                total=state.total,
                prev_disabled=state.current_index == 0,
                next_disabled=state.current_index >= state.total - 1,
                download_available=download_available,
            )
        )

    async def show_recommendation(self, result: Recommendation) -> None:
        await self._send(
            RecommendationMessage(
                root_id=self.modal_root_id,
                selected_ids=list(set(result.selected_ids)),
                format_id=result.format_id,
                directions=result.directions or "",
                directions_id=self.directions_id,
            )
        )

    async def show_recommendation_error(self, error_msg: str) -> None:
        await self._send(
            RecommendationErrorMessage(
                root_id=self.modal_root_id,
                error=error_msg,
            )
        )

    def show_modal(self, items: list[GalleryItem]) -> None:
        ui.modal_show(build_modal_ui(self.session.ns, items))

    def remove_modal(self) -> None:
        ui.modal_remove()

    async def append_pill(
        self, artifact_id: str, artifact_type: ArtifactType, summary: str
    ) -> None:
        pill_html = render_pill_html(artifact_id, artifact_type, self.open_input_id)
        message = ui.TagList(ui.HTML(pill_html))
        if summary:
            message.append(ui.markdown(summary))
        await self.chat_ui.append_message(message)
