from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import chevron

if TYPE_CHECKING:
    from ._datasource import DataSource
    from ._querychat_base import TOOL_GROUPS


def _load_text(value: str | Path | None) -> str | None:
    """Load text from string or Path."""
    if isinstance(value, Path):
        return value.read_text()
    return value


class QueryChatSystemPrompt:
    """Manages system prompt template and component assembly."""

    def __init__(
        self,
        prompt_template: str | Path,
        data_source: DataSource | None = None,
        data_sources: dict[str, DataSource] | None = None,
        data_description: str | Path | None = None,
        extra_instructions: str | Path | None = None,
        categorical_threshold: int = 10,
        relationships: dict[str, dict[str, str]] | None = None,
        table_descriptions: dict[str, str] | None = None,
    ):
        """
        Initialize with prompt components.

        Args:
            prompt_template: Mustache template string or path to template file
            data_source: Single DataSource instance (backwards compatibility)
            data_sources: Dictionary of DataSource instances keyed by table name
            data_description: Optional data context (string or path)
            extra_instructions: Optional custom LLM instructions (string or path)
            categorical_threshold: Threshold for categorical column detection
            relationships: Optional dict mapping table.column to foreign table.column
            table_descriptions: Optional dict mapping table names to descriptions

        """
        # Handle both single source (backwards compat) and dict of sources
        if data_sources is not None:
            self._data_sources = data_sources
        elif data_source is not None:
            self._data_sources = {data_source.table_name: data_source}
        else:
            raise ValueError("Either data_source or data_sources must be provided")

        # Load template
        if isinstance(prompt_template, Path):
            self.template = prompt_template.read_text()
        else:
            self.template = prompt_template

        # Store metadata
        self.data_description = _load_text(data_description)
        self.extra_instructions = _load_text(extra_instructions)
        self.categorical_threshold = categorical_threshold
        self._relationships = relationships or {}
        self._table_descriptions = table_descriptions or {}

        # Generate combined schema
        self.schema = self._generate_combined_schema()

    def _generate_combined_schema(self) -> str:
        """Generate schema string for all tables."""
        schemas = []
        for name, source in self._data_sources.items():
            schema = source.get_schema(categorical_threshold=self.categorical_threshold)
            schemas.append(f'<table name="{name}">\n{schema}\n</table>')

        return "\n\n".join(schemas)

    def _generate_relationships_text(self) -> str:
        """Generate relationship information text."""
        if not self._relationships:
            return ""

        lines = []
        for table, rels in self._relationships.items():
            for local_col, foreign_ref in rels.items():
                lines.append(f"- {table}.{local_col} references {foreign_ref}")

        return "\n".join(lines)

    def render(self, tools: tuple[TOOL_GROUPS, ...] | None) -> str:
        """
        Render system prompt with tool configuration.

        Args:
            tools: Normalized tuple of tool groups to enable (already normalized by caller)

        Returns:
            Fully rendered system prompt string

        """
        first_source = next(iter(self._data_sources.values()))
        is_duck_db = first_source.get_db_type().lower() == "duckdb"

        context = {
            "db_type": first_source.get_db_type(),
            "is_duck_db": is_duck_db,
            "schema": self.schema,
            "data_description": self.data_description,
            "extra_instructions": self.extra_instructions,
            "has_tool_update": "update" in tools if tools else False,
            "has_tool_query": "query" in tools if tools else False,
            "include_query_guidelines": len(tools or ()) > 0,
            "relationships": self._generate_relationships_text(),
        }

        return chevron.render(self.template, context)

    # Backwards compatibility
    @property
    def data_source(self) -> DataSource:
        """Return single data source for backwards compatibility."""
        if len(self._data_sources) == 1:
            return next(iter(self._data_sources.values()))
        raise ValueError("Multiple data sources present; use _data_sources instead")
