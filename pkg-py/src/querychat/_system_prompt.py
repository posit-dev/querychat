from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import chevron

if TYPE_CHECKING:
    from ._datasource import DataSource
    from ._querychat import TOOL_GROUPS


class QueryChatSystemPrompt:
    """Manages system prompt template and component assembly."""

    def __init__(
        self,
        prompt_template: str | Path,
        data_source: DataSource,
        data_description: str | Path | None = None,
        extra_instructions: str | Path | None = None,
        categorical_threshold: int = 10,
    ):
        """
        Initialize with prompt components.

        Args:
            prompt_template: Mustache template string or path to template file
            data_source: DataSource instance for schema generation
            data_description: Optional data context (string or path)
            extra_instructions: Optional custom LLM instructions (string or path)
            categorical_threshold: Threshold for categorical column detection

        """
        if isinstance(prompt_template, Path):
            self.template = prompt_template.read_text()
        else:
            self.template = prompt_template

        if isinstance(data_description, Path):
            self.data_description = data_description.read_text()
        else:
            self.data_description = data_description

        if isinstance(extra_instructions, Path):
            self.extra_instructions = extra_instructions.read_text()
        else:
            self.extra_instructions = extra_instructions

        self.schema = data_source.get_schema(
            categorical_threshold=categorical_threshold
        )

        self.categorical_threshold = categorical_threshold
        self.data_source = data_source

    def render(self, tools: tuple[TOOL_GROUPS, ...] | None) -> str:
        """
        Render system prompt with tool configuration.

        Args:
            tools: Normalized tuple of tool groups to enable (already normalized by caller)

        Returns:
            Fully rendered system prompt string

        """
        is_duck_db = self.data_source.get_db_type().lower() == "duckdb"

        context = {
            "db_type": self.data_source.get_db_type(),
            "is_duck_db": is_duck_db,
            "schema": self.schema,
            "data_description": self.data_description,
            "extra_instructions": self.extra_instructions,
            "has_tool_update": "update" in tools if tools else False,
            "has_tool_query": "query" in tools if tools else False,
            "include_query_guidelines": len(tools or ()) > 0,
        }

        return chevron.render(self.template, context)
