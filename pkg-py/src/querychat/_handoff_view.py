"""
Server→client output for the handoff feature.

`HandoffView` is the single place all handoff UI output lives: the
`querychat-handoff-*` custom messages (the wire contract with
`static/js/handoff.js`), the wizard modal, and the chat pill. It wraps the
Shiny `Session` and chat UI plus the namespaced ids the messages target, so
callers express intent (`view.show_handoff(state)`, `view.append_pill(...)`)
rather than touching `shiny`/`shinychat` directly. It holds no reactive state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shiny import ui

from ._handoff_modal import build_modal_ui
from ._handoff_panel import render_pill_html
from ._handoff_protocol import (
    HandoffMessage,
    PanelToggleMessage,
    RecommendationErrorMessage,
    RecommendationMessage,
    SourceUpdateMessage,
    StreamingMessage,
)

if TYPE_CHECKING:
    import shinychat

    from shiny import Session

    from ._handoff_gallery import GalleryItem
    from ._handoff_prompt import Recommendation
    from ._handoff_state import HandoffState
    from ._handoff_types import HandoffType


class HandoffView:
    def __init__(self, session: Session, chat_ui: shinychat.Chat) -> None:
        self.session = session
        self.chat_ui = chat_ui
        self.panel_root_id = session.ns("handoff_root")
        self.modal_root_id = session.ns("handoff_modal_root")
        self.editor_id = session.ns("handoff_source_editor")
        self.directions_id = session.ns("handoff_directions")
        self.open_input_id = session.ns("handoff_open")

    async def _send(self, message: HandoffMessage) -> None:
        await self.session.send_custom_message(
            message.message_type(),
            message.payload(),
        )

    async def set_panel_open(self, *, is_open: bool) -> None:
        await self._send(PanelToggleMessage(root_id=self.panel_root_id, open=is_open))

    async def clear_editor(self, language: str) -> None:
        await self._send(
            SourceUpdateMessage(
                root_id=self.panel_root_id,
                id=self.editor_id,
                value="",
                language=language,
                download_available=False,
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

    async def append_source(self, value: str) -> None:
        await self._send(
            SourceUpdateMessage(
                root_id=self.panel_root_id,
                id=self.editor_id,
                value=value,
                append=True,
            )
        )

    async def set_streaming(self, *, active: bool) -> None:
        await self._send(StreamingMessage(root_id=self.panel_root_id, active=active))

    async def show_handoff(
        self,
        state: HandoffState,
        *,
        download_available: bool,
    ) -> None:
        await self._send(
            SourceUpdateMessage(
                root_id=self.panel_root_id,
                id=self.editor_id,
                value=state.source,
                language=state.handoff_type.editor_language,
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
        self, handoff_id: str, handoff_type: HandoffType, summary: str
    ) -> None:
        pill_html = render_pill_html(handoff_id, handoff_type, self.open_input_id)
        message = ui.TagList(ui.HTML(pill_html))
        if summary:
            message.append(ui.markdown(summary))
        await self.chat_ui.append_message(message)
