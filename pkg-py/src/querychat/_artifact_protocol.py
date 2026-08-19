"""Typed server-to-browser messages for the artifact feature."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

ArtifactMessageAction = Literal[
    "recommend",
    "recommend-error",
    "source-update",
    "streaming",
    "version-update",
    "panel-toggle",
]

ARTIFACT_MESSAGE_ACTIONS: tuple[ArtifactMessageAction, ...] = (
    "recommend",
    "recommend-error",
    "source-update",
    "streaming",
    "version-update",
    "panel-toggle",
)
MESSAGE_PREFIX = "querychat-artifact-"


class ArtifactMessage(BaseModel):
    """Base type for artifact custom-message payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: ClassVar[ArtifactMessageAction]
    root_id: str

    @classmethod
    def message_type(cls) -> str:
        return f"{MESSAGE_PREFIX}{cls.action}"

    def payload(self) -> dict[str, object]:
        return self.model_dump(exclude_none=True)


class RecommendationMessage(ArtifactMessage):
    action: ClassVar[ArtifactMessageAction] = "recommend"

    selected_ids: list[str]
    format_id: str
    directions: str
    directions_id: str


class RecommendationErrorMessage(ArtifactMessage):
    action: ClassVar[ArtifactMessageAction] = "recommend-error"

    error: str


class SourceUpdateMessage(ArtifactMessage):
    action: ClassVar[ArtifactMessageAction] = "source-update"

    id: str
    value: str
    language: str | None = None


class StreamingMessage(ArtifactMessage):
    action: ClassVar[ArtifactMessageAction] = "streaming"

    active: bool


class VersionUpdateMessage(ArtifactMessage):
    action: ClassVar[ArtifactMessageAction] = "version-update"

    label: str
    total: int
    prev_disabled: bool
    next_disabled: bool
    download_available: bool


class PanelToggleMessage(ArtifactMessage):
    action: ClassVar[ArtifactMessageAction] = "panel-toggle"

    open: bool
