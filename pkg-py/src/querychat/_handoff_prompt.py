from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import chevron
from pydantic import BaseModel, Field, create_model, field_validator

from ._handoff_gallery import GalleryItem, QueryGalleryItem, VizGalleryItem
from ._handoff_types import (
    LANGUAGES,
    HandoffFormat,
    HandoffLanguage,
    HandoffType,
)

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from ._handoff_validation import HandoffValidationError


class Recommendation(BaseModel):
    selected_ids: list[str] = Field(
        description="IDs of the results to include in the handoff"
    )
    format_id: str = Field(
        description="ID of the output format to use for the handoff"
    )
    directions: str = Field(
        default="",
        description="Optional suggested layout directions for the handoff",
    )


class HandoffResult(BaseModel):
    source: str = Field(
        description="The complete raw source for the handoff: no markdown code fences, no commentary before or after."
    )
    language: HandoffLanguage = Field(
        description="Programming language used by the handoff.",
    )
    summary: str = Field(
        default="",
        description="A brief, succinct summary of what this handoff shows or does, useful at a glance.",
    )
    install_instructions: str = Field(
        default="",
        description="Concise Markdown for installing the handoff's software dependencies: a short intro line followed by a fenced code block of install commands. Cover only installation, not how to run it.",
    )
    run_instructions: str = Field(
        default="",
        description=(
            "Concise Markdown explaining how to run the generated handoff, "
            "including fenced command blocks where appropriate."
        ),
    )
    referenced_tables: list[str] = Field(
        description="Registered table names used by the handoff source.",
    )


class FreeformMetadata(BaseModel):
    file_extension: str = Field(
        description="File extension for this format, including the leading dot (e.g., '.Rmd', '.py', '.sql')"
    )
    editor_language: str = Field(
        description="Editor syntax highlighting language (e.g., 'markdown', 'python', 'sql')"
    )

    @field_validator("file_extension")
    @classmethod
    def normalize_file_extension(cls, value: str) -> str:
        extension = value if value.startswith(".") else f".{value}"
        suffix = extension[1:]
        is_safe = (
            bool(suffix)
            and ".." not in extension
            and all(
                char.isascii() and (char.isalnum() or char in {".", "_", "+", "-"})
                for char in suffix
            )
        )
        if not is_safe:
            raise ValueError("file_extension must be a safe file extension")
        return extension


def recommendation_model(
    item_ids: list[str],
    format_ids: list[str],
) -> type[Recommendation]:
    item_id_type = Literal[tuple(item_ids)]  # type: ignore[valid-type]
    format_id_type = Literal[tuple(format_ids)]  # type: ignore[valid-type]

    return create_model(
        "Recommendation",
        __base__=Recommendation,
        selected_ids=(
            list[item_id_type],  # type: ignore[valid-type]
            Field(description="IDs of the results to include in the handoff"),
        ),
        format_id=(
            format_id_type,  # type: ignore[valid-type]
            Field(description="ID of the output format to use for the handoff"),
        ),
    )


def handoff_result_model(
    table_names: list[str],
    languages: tuple[HandoffLanguage, ...],
    *,
    require_run_instructions: bool = False,
) -> type[HandoffResult]:
    # Static typing cannot express Literal values created from runtime names.
    table_name_type = Literal[tuple(table_names)]  # type: ignore[valid-type]
    referenced_tables = (
        list[table_name_type],  # type: ignore[valid-type]
        Field(description="Registered table names used by the handoff source."),
    )
    language_type = Literal[tuple(languages)]  # type: ignore[valid-type]
    language = (
        language_type,  # type: ignore[valid-type]
        Field(description="Programming language used by the handoff."),
    )
    if require_run_instructions:
        return create_model(
            "HandoffResult",
            __base__=HandoffResult,
            language=language,
            run_instructions=required_run_instructions_field(),
            referenced_tables=referenced_tables,
        )
    return create_model(
        "HandoffResult",
        __base__=HandoffResult,
        language=language,
        referenced_tables=referenced_tables,
    )


def build_handoff_system_prompt(
    selected_items: list[GalleryItem],
    schema: str,
    custom_directions: str,
    *,
    format_id: str,
    language: HandoffLanguage,
    data_instructions: str = "",
) -> str:
    template = load_template("handoff-system.md")

    viz_items = [
        {"title": item.title, "ggsql": item.ggsql}
        for item in selected_items
        if isinstance(item, VizGalleryItem)
    ]
    query_items = [
        {"title": item.title, "sql": item.sql}
        for item in selected_items
        if isinstance(item, QueryGalleryItem)
    ]

    context = {
        "schema": schema,
        "custom_directions": custom_directions,
        "data_instructions": data_instructions,
        "has_items": len(selected_items) > 0,
        "viz_items": viz_items,
        "query_items": query_items,
        "language_label": LANGUAGES[language],
        "format_quarto": format_id == "quarto-dashboard",
        "format_marimo": format_id == "marimo-notebook",
        "format_shiny": format_id == "shiny-app",
        "format_jupyter": format_id == "jupyter-notebook",
        "lang_python": language == "python",
        "lang_r": language == "r",
    }

    return chevron.render(template, context)


def build_handoff_user_prompt(
    handoff_format: HandoffFormat,
    language: HandoffLanguage,
) -> str:
    return (
        f"Generate the complete source for a {handoff_format.label} handoff "
        f"in {LANGUAGES[language]}."
    )


def build_freeform_handoff_user_prompt(
    format_name: str,
    language: HandoffLanguage,
) -> str:
    return (
        f"Generate the complete source for a {format_name} handoff "
        f"in {LANGUAGES[language]}."
    )


def build_handoff_repair_prompt(
    error: HandoffValidationError,
    handoff_type: HandoffType,
) -> str:
    language = LANGUAGES[handoff_type.language]
    return (
        "The generated handoff failed structural validation:\n\n"
        f"{error}\n\n"
        f"Return the complete corrected {handoff_type.label} source in {language}. "
        "Preserve the requested analysis and use the same registered data tables."
    )


def build_external_data_repair_system_prompt(
    *,
    handoff_type: HandoffType,
    schema: str,
    data_instructions: str,
    referenced_tables: list[str],
) -> str:
    setup_location = external_data_setup_location(handoff_type)
    return (
        "You are correcting a generated handoff because its DataFrame snapshots "
        "exceed the bundle limit. The preceding conversation contains the complete "
        "source to revise.\n\n"
        f"Place all external data import and connection code in a {setup_location}. "
        "Call it DATA SETUP and make it visually prominent. Clearly state that "
        "paths, credentials, or environment variables may need adjustment. Never "
        "invent or hardcode credentials.\n\n"
        "Keep the exact same referenced-table set: "
        f"{json.dumps(referenced_tables)}.\n\n"
        f"Database schema:\n{schema}\n\n"
        f"Data access requirements:\n{data_instructions}\n\n"
        f"Return the complete corrected {handoff_type.label} source and structured "
        "metadata, not a patch or explanation."
    )


def build_recommend_prompt(
    items: list[GalleryItem],
    handoff_formats: dict[str, HandoffFormat],
) -> str:
    template = load_template("handoff-recommend.md")

    item_dicts = []
    for item in items:
        kind = "visualization" if isinstance(item, VizGalleryItem) else "query"
        item_dicts.append({"id": item.id, "title": item.title, "kind": kind})

    format_dicts = [
        {
            "id": type_id,
            "label": handoff_type.label,
            "description": handoff_type.description,
        }
        for type_id, handoff_type in handoff_formats.items()
    ]

    context = {
        "items": item_dicts,
        "formats": format_dicts,
    }

    return chevron.render(template, context)


def external_data_setup_location(handoff_type: HandoffType) -> str:
    if handoff_type.id in {"jupyter-notebook", "marimo-notebook"}:
        return "first code cell"
    if handoff_type.id == "quarto-dashboard":
        return "dedicated DATA SETUP code chunk"
    return "prominent top-level DATA SETUP block"


def prompts_dir() -> Path:
    return Path(__file__).parent / "prompts"


def load_template(filename: str) -> str:
    return (prompts_dir() / filename).read_text()


def required_run_instructions_field() -> tuple[type[str], FieldInfo]:
    return (
        str,
        Field(
            description=(
                "Concise Markdown explaining how to run the generated handoff, "
                "including fenced command blocks where appropriate."
            )
        ),
    )
