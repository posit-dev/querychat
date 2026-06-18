from __future__ import annotations

from typing import Literal

import chatlas  # noqa: TC002 — pydantic needs this at runtime for field validation
from pydantic import BaseModel, Field

from ._artifact_types import (
    ArtifactType,  # noqa: TC001 — pydantic needs this at runtime for field validation
)

VersionKind = Literal["generated", "revised"]


class ArtifactVersion(BaseModel):
    source: str
    turns: list[chatlas.Turn] = Field(default_factory=list)
    kind: VersionKind
    summary: str = ""
    install_instructions: str = ""


class ArtifactState(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    system_prompt: str
    versions: list[ArtifactVersion]
    current_index: int = 0
    bundled_files: dict[str, bytes] = Field(default_factory=dict, exclude=True)
    data_instructions: str = Field(default="", exclude=True)

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
    def turns(self) -> list[chatlas.Turn]:
        return self.current_version.turns

    @property
    def total(self) -> int:
        return len(self.versions)

    def push_version(self, version: ArtifactVersion) -> None:
        del self.versions[self.current_index + 1 :]
        self.versions.append(version)
        self.current_index = len(self.versions) - 1

    def step(self, delta: int) -> None:
        self.current_index = max(0, min(self.total - 1, self.current_index + delta))

