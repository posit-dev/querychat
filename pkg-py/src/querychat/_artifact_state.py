from __future__ import annotations

from typing import Literal

import chatlas  # noqa: TC002 — pydantic needs this at runtime for field validation
from pydantic import BaseModel, Field, model_validator

from ._artifact_types import (
    ArtifactLanguage,  # noqa: TC001 — pydantic needs this at runtime for field validation
    ArtifactType,  # noqa: TC001 — pydantic needs this at runtime for field validation
)

VersionKind = Literal["generated", "revised"]


class ArtifactVersion(BaseModel):
    source: str
    turns: list[chatlas.Turn] = Field(default_factory=list)
    kind: VersionKind
    summary: str = ""
    install_instructions: str = ""
    run_instructions: str = ""
    referenced_tables: list[str] = Field(default_factory=list)
    bundled_tables: list[str] = Field(default_factory=list)
    bundle_id: str | None = None
    data_instructions: str = ""


class ArtifactState(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    system_prompt: str
    versions: list[ArtifactVersion]
    language: ArtifactLanguage | None = None
    current_index: int = 0

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_metadata(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        migrated = dict(value)
        raw_type = migrated.get("artifact_type")
        if isinstance(raw_type, dict):
            artifact_type = dict(raw_type)
            extension = artifact_type.get("file_extension")
            artifact_type.setdefault(
                "structure",
                "notebook-json" if extension == ".ipynb" else "text",
            )
            artifact_type.setdefault("language", migrated.get("language"))
            migrated["artifact_type"] = artifact_type
            raw_type = artifact_type
        legacy_run = (
            raw_type.get("run_instructions", "") if isinstance(raw_type, dict) else ""
        )
        raw_versions = migrated.get("versions")
        if isinstance(raw_versions, list):
            versions: list[object] = []
            for raw_version in raw_versions:
                if isinstance(raw_version, dict):
                    version = dict(raw_version)
                    if legacy_run:
                        version.setdefault("run_instructions", legacy_run)
                    version.setdefault("bundle_id", None)
                    version.setdefault("data_instructions", "")
                    versions.append(version)
                else:
                    versions.append(raw_version)
            migrated["versions"] = versions
        return migrated

    @property
    def current_version(self) -> ArtifactVersion:
        return self.versions[self.current_index]

    @property
    def source(self) -> str:
        return self.current_version.source

    @property
    def summary(self) -> str:
        return self.current_version.summary

    @property
    def install_instructions(self) -> str:
        return self.current_version.install_instructions

    @property
    def run_instructions(self) -> str:
        return self.current_version.run_instructions

    @property
    def turns(self) -> list[chatlas.Turn]:
        return self.current_version.turns

    @property
    def total(self) -> int:
        return len(self.versions)

    def push_version(self, version: ArtifactVersion) -> list[ArtifactVersion]:
        removed = self.versions[self.current_index + 1 :]
        del self.versions[self.current_index + 1 :]
        self.versions.append(version)
        self.current_index = len(self.versions) - 1
        return removed

    def step(self, delta: int) -> None:
        self.current_index = max(0, min(self.total - 1, self.current_index + delta))
