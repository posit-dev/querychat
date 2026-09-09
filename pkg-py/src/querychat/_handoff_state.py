from __future__ import annotations

import chatlas  # noqa: TC002 -- pydantic needs this at runtime for field validation
from pydantic import BaseModel, Field

from ._handoff_types import (
    HandoffType,  # noqa: TC001 -- pydantic needs this at runtime for field validation
)


class HandoffState(BaseModel):
    handoff_id: str
    handoff_type: HandoffType
    system_prompt: str
    source: str
    turns: list[chatlas.Turn] = Field(default_factory=list)
    summary: str = ""
    install_instructions: str = ""
    run_instructions: str = ""
    referenced_tables: list[str] = Field(default_factory=list)
    bundled_tables: list[str] = Field(default_factory=list)
    bundle_id: str | None = None
    data_instructions: str = ""
