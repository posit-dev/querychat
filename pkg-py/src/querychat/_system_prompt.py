from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import chevron

from ._viz_utils import has_viz_tool

if TYPE_CHECKING:
    from ._data_dict import DataDict
    from ._datasource import DataSource


class QueryChatSystemPrompt:
    """Manages system prompt template and component assembly."""

    def __init__(
        self,
        *,
        prompt_template: str | Path | None,
        data_source: DataSource | None = None,
        data_sources: dict[str, DataSource] | None = None,
        data_description: str | Path | None = None,
        extra_instructions: str | Path | None = None,
        categorical_threshold: int = 20,
        data_dict: DataDict | None = None,
    ):
        """
        Initialize with prompt components.

        Args:
            prompt_template: Mustache template string or path to template file, or None for default
            data_source: Single DataSource instance (backwards compatibility)
            data_sources: Dictionary of DataSource instances keyed by table name
            data_description: Optional data context (string or path)
            extra_instructions: Optional custom LLM instructions (string or path)
            categorical_threshold: Threshold for categorical column detection
            data_dict: Optional DataDict for table descriptions, relationships, and glossary

        """
        if data_sources is not None:
            self._data_sources = data_sources
        elif data_source is not None:
            self._data_sources = {data_source.table_name: data_source}
        else:
            raise ValueError("Either data_source or data_sources must be provided")

        self._data_dict = data_dict

        if prompt_template is None:
            prompt_template = Path(__file__).parent / "prompts" / "prompt.md"
        self.template = (
            prompt_template.read_text()
            if isinstance(prompt_template, Path)
            else prompt_template
        )

        self.data_description = (
            data_description.read_text()
            if isinstance(data_description, Path)
            else data_description
        )
        self.extra_instructions = (
            extra_instructions.read_text()
            if isinstance(extra_instructions, Path)
            else extra_instructions
        )
        self.categorical_threshold = categorical_threshold

    def _generate_tables_overview(self) -> str:
        lines = []
        for name, source in self._data_sources.items():
            desc: str | None = None
            if self._data_dict and name in self._data_dict.tables:
                desc = self._data_dict.tables[name].description
            if not desc and not self.data_description:
                desc = source.get_data_description() or None
            if desc:
                lines.append(f"- {name}: {desc}")
            else:
                lines.append(f"- {name}")
        return "\n".join(lines)

    def _generate_relationships_text(self) -> str:
        if not self._data_dict or not self._data_dict.relationships:
            return ""
        lines = []
        for rel in self._data_dict.relationships:
            line = rel.join
            if rel.cardinality:
                line += f" ({rel.cardinality})"
            if rel.description:
                line += f": {rel.description}"
            lines.append("- " + line)
        return "\n".join(lines)

    def _generate_glossary_text(self) -> str:
        if not self._data_dict or not self._data_dict.glossary:
            return ""
        return "\n".join(
            f"- {term}: {definition}"
            for term, definition in self._data_dict.glossary.items()
        )

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

        context = {
            "db_type": db_type,
            "is_duck_db": db_type.lower() == "duckdb",
            "semantic_views": first_source.get_semantic_views_description(),
            "tables_overview": self._generate_tables_overview(),
            "relationships": self._generate_relationships_text(),
            "glossary": self._generate_glossary_text(),
            "data_description": self.data_description,
            "extra_instructions": self.extra_instructions,
            "has_tool_update": "update" in tools if tools else False,
            "has_tool_query": "query" in tools if tools else False,
            "has_tool_visualize": has_viz_tool(tools),
            "include_query_guidelines": len(tools or ()) > 0,
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
