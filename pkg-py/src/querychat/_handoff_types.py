from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

from ._icons import (
    ICON_NAMES,  # noqa: TC001 — pydantic needs this at runtime for field validation
)

if TYPE_CHECKING:
    from shiny.ui._input_code_editor import CodeEditorLanguage

    EditorLanguage = CodeEditorLanguage
else:
    EditorLanguage = str


HandoffLanguage = Literal["python", "r"]
HandoffStructure = Literal["text", "notebook-json"]

LANGUAGES: dict[HandoffLanguage, str] = {"python": "Python", "r": "R"}


class HandoffTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_extension: str
    editor_language: EditorLanguage
    structure: HandoffStructure

    @field_validator("file_extension")
    @classmethod
    def require_leading_dot(cls, value: str) -> str:
        if not value.startswith("."):
            raise ValueError("file_extension must start with '.'")
        return value


class HandoffFormat(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    description: str
    icon: ICON_NAMES
    targets: dict[HandoffLanguage, HandoffTarget]

    @property
    def supported_languages(self) -> tuple[HandoffLanguage, ...]:
        return tuple(self.targets)


class HandoffRegistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: Literal[1]
    formats: dict[str, HandoffFormat]


class HandoffType(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    icon: ICON_NAMES = "file-earmark-code"
    language: HandoffLanguage
    file_extension: str
    editor_language: EditorLanguage
    structure: HandoffStructure = "text"


def load_handoff_registry() -> HandoffRegistry:
    path = files("querychat").joinpath("handoff-formats.yml")
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("Handoff registry must be a mapping.")
    formats = raw.get("formats")
    if not isinstance(formats, dict):
        raise TypeError("Handoff registry formats must be a mapping.")

    normalized: dict[str, object] = {}
    for format_id, definition in formats.items():
        if not isinstance(format_id, str) or not isinstance(definition, dict):
            raise TypeError("Handoff registry format entries must be mappings.")
        normalized[format_id] = {"id": format_id, **definition}

    return HandoffRegistry.model_validate({**raw, "formats": normalized})


HANDOFF_REGISTRY = load_handoff_registry()
HANDOFF_FORMATS = HANDOFF_REGISTRY.formats


def resolve_handoff_target(
    format_id: str,
    language: HandoffLanguage,
) -> HandoffTarget:
    handoff_format = HANDOFF_FORMATS.get(format_id)
    if handoff_format is None:
        raise ValueError(f"Unknown handoff format: {format_id}")
    target = handoff_format.targets.get(language)
    if target is None:
        label = LANGUAGES[language]
        raise ValueError(
            f"Handoff format '{handoff_format.label}' does not support {label}."
        )
    return target


def resolve_handoff_type(
    format_id: str,
    language: HandoffLanguage,
) -> HandoffType:
    handoff_format = HANDOFF_FORMATS.get(format_id)
    if handoff_format is None:
        raise ValueError(f"Unknown handoff format: {format_id}")
    target = resolve_handoff_target(format_id, language)
    return HandoffType(
        id=format_id,
        label=handoff_format.label,
        icon=handoff_format.icon,
        language=language,
        **target.model_dump(),
    )
