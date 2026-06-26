from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import chevron
import yaml

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
        data_dicts: list[DataDict] | None = None,
        include_tables: bool | list[str] = True,
        include_relationships: bool = True,
        include_glossary: bool = True,
    ):
        if data_sources is not None:
            self._data_sources = data_sources
        elif data_source is not None:
            self._data_sources = {data_source.table_name: data_source}
        else:
            self._data_sources = {}

        self._data_dicts: list[DataDict] = data_dicts or []

        if include_tables is not True:
            resolved = (
                []
                if include_tables is False
                else [n for n in include_tables if n in self._data_sources]
            )
            self._data_sources = {n: self._data_sources[n] for n in resolved}
            self._data_dicts = [
                dd
                for dd in self._data_dicts
                if any(n in resolved for n in dd.tables)
                or (not dd.tables and dd.description)
            ]
            update: dict[str, object] = {}
            if not include_relationships:
                update["relationships"] = []
            if not include_glossary:
                update["glossary"] = {}
            if update:
                self._data_dicts = [
                    dd.model_copy(update=update) for dd in self._data_dicts
                ]

        if (
            include_tables is True
            and len(self._data_sources) > 1
            and not self._data_dicts
        ):
            warnings.warn(
                "Multiple tables registered without a data_dict. "
                "Providing a data_dict with table descriptions and relationships "
                "gives the LLM better context for multi-table queries.",
                UserWarning,
                stacklevel=3,
            )

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
            desc: str | None = source.get_data_description() or None
            if desc and not self.data_description:
                lines.append(f"- {name}: {desc}")
            else:
                lines.append(f"- {name}")
        return "\n".join(lines)

    def _generate_data_dicts_yaml(self) -> str:
        def escape_attr(val: str) -> str:
            return val.replace('"', "&quot;")

        blocks: list[str] = []
        all_claimed: set[str] = set()

        for dd in self._data_dicts:
            d = dd.to_prompt_dict()
            # Name and description belong in the XML tag, not the YAML body
            d.pop("name", None)
            d.pop("description", None)

            claimed = {n for n in self._data_sources if n in dd.tables}
            all_claimed.update(claimed)
            if "tables" in d:
                d["tables"] = {
                    n: v for n, v in d["tables"].items() if n in self._data_sources
                }
                if not d["tables"]:
                    del d["tables"]

            attrs = f'name="{escape_attr(dd.name)}"' if dd.name else ""
            if dd.description:
                attrs += f' description="{escape_attr(dd.description)}"'

            body = (
                yaml.dump(
                    d, default_flow_style=False, allow_unicode=True, sort_keys=False
                ).rstrip()
                if d
                else ""
            )
            blocks.append(
                f"<data-dict {attrs}>\n{body}\n</data-dict>"
                if body
                else f"<data-dict {attrs}/>"
            )

        unclaimed = [n for n in self._data_sources if n not in all_claimed]
        if unclaimed:
            tables: dict = {}
            for name in unclaimed:
                desc = (
                    self._data_sources[name].get_data_description() or None
                    if not self.data_description
                    else None
                )
                tables[name] = {"description": desc} if desc else None
            yaml_str = yaml.dump(
                {"tables": tables},
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            ).rstrip()
            blocks.append(f"<tables>\n{yaml_str}\n</tables>")

        return "\n\n".join(blocks)

    def render(self, tools: set[str] | None) -> str:
        """
        Render system prompt with tool configuration.

        Args:
            tools: Normalized set of tool groups to enable (already normalized by caller)

        Returns:
            Fully rendered system prompt string

        """
        first_source = next(iter(self._data_sources.values()), None)
        db_type = first_source.get_db_type() if first_source is not None else "SQL"
        # Data dicts can carry global (table-less) descriptions, so they may
        # render even when no tables are selected (e.g. a generic greeting).
        has_dicts = bool(self._data_dicts)
        semantic_views = (
            first_source.get_semantic_views_description()
            if first_source is not None
            else ""
        )
        tables_overview = (
            ""
            if has_dicts
            else (self._generate_tables_overview() if first_source is not None else "")
        )
        data_dicts = self._generate_data_dicts_yaml() if has_dicts else ""

        context = {
            "db_type": db_type,
            "is_duck_db": db_type.lower() == "duckdb",
            "has_tables": first_source is not None,
            "semantic_views": semantic_views,
            "has_data_dicts": has_dicts,
            "data_dicts": data_dicts,
            "tables_overview": tables_overview,
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
