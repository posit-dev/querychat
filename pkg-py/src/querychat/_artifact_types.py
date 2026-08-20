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


ArtifactLanguage = Literal["python", "r"]
ArtifactStructure = Literal["text", "notebook-json"]

LANGUAGES: dict[ArtifactLanguage, str] = {"r": "R", "python": "Python"}


class ArtifactTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_extension: str
    editor_language: EditorLanguage
    structure: ArtifactStructure

    @field_validator("file_extension")
    @classmethod
    def require_leading_dot(cls, value: str) -> str:
        if not value.startswith("."):
            raise ValueError("file_extension must start with '.'")
        return value


class ArtifactFormat(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    description: str
    icon: ICON_NAMES
    targets: dict[ArtifactLanguage, ArtifactTarget]

    @property
    def supported_languages(self) -> tuple[ArtifactLanguage, ...]:
        return tuple(self.targets)


class ArtifactRegistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: Literal[1]
    formats: dict[str, ArtifactFormat]


class ArtifactType(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    icon: ICON_NAMES = "file-earmark-code"
    language: ArtifactLanguage
    file_extension: str
    editor_language: EditorLanguage
    structure: ArtifactStructure = "text"


def load_artifact_registry() -> ArtifactRegistry:
    path = files("querychat").joinpath("artifact-formats.yml")
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("Artifact registry must be a mapping.")
    formats = raw.get("formats")
    if not isinstance(formats, dict):
        raise TypeError("Artifact registry formats must be a mapping.")

    normalized: dict[str, object] = {}
    for format_id, definition in formats.items():
        if not isinstance(format_id, str) or not isinstance(definition, dict):
            raise TypeError("Artifact registry format entries must be mappings.")
        normalized[format_id] = {"id": format_id, **definition}

    return ArtifactRegistry.model_validate({**raw, "formats": normalized})


ARTIFACT_REGISTRY = load_artifact_registry()
ARTIFACT_FORMATS = ARTIFACT_REGISTRY.formats


def resolve_artifact_target(
    format_id: str,
    language: ArtifactLanguage,
) -> ArtifactTarget:
    artifact_format = ARTIFACT_FORMATS.get(format_id)
    if artifact_format is None:
        raise ValueError(f"Unknown artifact format: {format_id}")
    target = artifact_format.targets.get(language)
    if target is None:
        label = LANGUAGES[language]
        raise ValueError(
            f"Artifact format '{artifact_format.label}' does not support {label}."
        )
    return target


def resolve_artifact_type(
    format_id: str,
    language: ArtifactLanguage,
) -> ArtifactType:
    artifact_format = ARTIFACT_FORMATS.get(format_id)
    if artifact_format is None:
        raise ValueError(f"Unknown artifact format: {format_id}")
    target = resolve_artifact_target(format_id, language)
    return ArtifactType(
        id=format_id,
        label=artifact_format.label,
        icon=artifact_format.icon,
        language=language,
        **target.model_dump(),
    )
