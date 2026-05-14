from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import chevron

from ._viz_utils import has_viz_tool

_SCHEMA_TAG_RE = re.compile(r"\{\{[{#^/]?\s*schema\b")

if TYPE_CHECKING:
    from ._datasource import DataSource


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

        if isinstance(data_description, Path):
            self.data_description = data_description.read_text()
        else:
            self.data_description = data_description

        if isinstance(extra_instructions, Path):
            self.extra_instructions = extra_instructions.read_text()
        else:
            self.extra_instructions = extra_instructions

        self.categorical_threshold = categorical_threshold
        self._relationships = relationships or {}
        self._table_descriptions = table_descriptions or {}

        # Generate combined schema (skip if template doesn't reference it)
        if _SCHEMA_TAG_RE.search(self.template):
            self.schema = self._generate_combined_schema()
        else:
            self.schema = ""

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

    def render(self, tools: set[str] | None) -> str:
        """
        Render system prompt with tool configuration.

        Args:
            tools: Normalized set of tool groups to enable (already normalized by caller)

        Returns:
            Fully rendered system prompt string

        """
        first_source = next(iter(self._data_sources.values()))
        db_type = first_source.get_db_type()
        is_duck_db = db_type.lower() == "duckdb"

        context = {
            "db_type": db_type,
            "is_duck_db": is_duck_db,
            "semantic_views": first_source.get_semantic_views_description(),
            "schema": self.schema,
            "data_description": self.data_description,
            "extra_instructions": self.extra_instructions,
            "has_tool_update": "update" in tools if tools else False,
            "has_tool_query": "query" in tools if tools else False,
            "has_tool_visualize": has_viz_tool(tools),
            "include_query_guidelines": len(tools or ()) > 0,
            "relationships": self._generate_relationships_text(),
            "multi_table": len(self._data_sources) > 1,
        }

        prompts_dir = str(Path(__file__).parent / "prompts")
        return chevron.render(
            self.template,
            context,
            partials_path=prompts_dir,
            partials_ext="md",
        )

    @property
    def data_source(self) -> DataSource:
        """Return single data source for backwards compatibility."""
        if len(self._data_sources) == 1:
            return next(iter(self._data_sources.values()))
        raise ValueError("Multiple data sources present; use _data_sources instead")
