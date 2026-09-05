"""Typed server-to-browser messages for the handoff feature."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

HandoffMessageAction = Literal[
    "recommend",
    "recommend-error",
    "source-update",
    "streaming",
    "panel-toggle",
]

HANDOFF_MESSAGE_ACTIONS: tuple[HandoffMessageAction, ...] = (
    "recommend",
    "recommend-error",
    "source-update",
    "streaming",
    "panel-toggle",
)
MESSAGE_PREFIX = "querychat-handoff-"


class HandoffMessage(BaseModel):
    """Base type for handoff custom-message payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: ClassVar[HandoffMessageAction]
    root_id: str

    @classmethod
    def message_type(cls) -> str:
        return f"{MESSAGE_PREFIX}{cls.action}"

    def payload(self) -> dict[str, object]:
        return self.model_dump(exclude_none=True)


class RecommendationMessage(HandoffMessage):
    action: ClassVar[HandoffMessageAction] = "recommend"

    selected_ids: list[str]
    format_id: str
    directions: str
    directions_id: str


class RecommendationErrorMessage(HandoffMessage):
    action: ClassVar[HandoffMessageAction] = "recommend-error"

    error: str


class SourceUpdateMessage(HandoffMessage):
    action: ClassVar[HandoffMessageAction] = "source-update"

    id: str
    value: str
    append: bool | None = None
    language: str | None = None
    download_available: bool | None = None


class StreamingMessage(HandoffMessage):
    action: ClassVar[HandoffMessageAction] = "streaming"

    active: bool


class PanelToggleMessage(HandoffMessage):
    action: ClassVar[HandoffMessageAction] = "panel-toggle"

    open: bool
