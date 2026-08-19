from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import chevron
from pydantic import BaseModel, Field, create_model, field_validator

from ._artifact_gallery import GalleryItem, QueryGalleryItem, VizGalleryItem
from ._artifact_types import (
    LANGUAGES,
    ArtifactFormat,
    ArtifactLanguage,
    ArtifactType,
)

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from ._artifact_validation import ArtifactValidationError


class Recommendation(BaseModel):
    selected_ids: list[str] = Field(
        description="IDs of the results to include in the artifact"
    )
    format_id: str = Field(
        description="ID of the output format to use for the artifact"
    )
    directions: str = Field(
        default="",
        description="Optional suggested layout directions for the artifact",
    )


class ArtifactResult(BaseModel):
    source: str = Field(
        description="The complete raw source for the artifact: no markdown code fences, no commentary before or after."
    )
    language: ArtifactLanguage | None = Field(
        default=None,
        description=(
            "Programming language used by the artifact. Required for registered "
            "formats and optional for freeform formats."
        ),
    )
    summary: str = Field(
        default="",
        description="A brief, succinct summary of what this artifact shows or does, useful at a glance.",
    )
    install_instructions: str = Field(
        default="",
        description="Concise Markdown for installing the artifact's software dependencies: a short intro line followed by a fenced code block of install commands. Cover only installation, not how to run it.",
    )
    run_instructions: str = Field(
        default="",
        description=(
            "Concise Markdown explaining how to run the generated artifact, "
            "including fenced command blocks where appropriate."
        ),
    )
    referenced_tables: list[str] = Field(
        description="Registered table names used by the artifact source.",
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
                char.isascii()
                and (char.isalnum() or char in {".", "_", "+", "-"})
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
            Field(description="IDs of the results to include in the artifact"),
        ),
        format_id=(
            format_id_type,  # type: ignore[valid-type]
            Field(description="ID of the output format to use for the artifact"),
        ),
    )


def artifact_result_model(
    table_names: list[str],
    languages: tuple[ArtifactLanguage, ...] | None = None,
    *,
    require_run_instructions: bool = False,
) -> type[ArtifactResult]:
    # Static typing cannot express Literal values created from runtime names.
    table_name_type = Literal[tuple(table_names)]  # type: ignore[valid-type]
    referenced_tables = (
        list[table_name_type],  # type: ignore[valid-type]
        Field(description="Registered table names used by the artifact source."),
    )
    if languages:
        language_type = Literal[tuple(languages)]  # type: ignore[valid-type]
        language = (
            language_type,  # type: ignore[valid-type]
            Field(
                description=(
                    "Programming language used by the artifact. Required for "
                    "registered formats and optional for freeform formats."
                )
            ),
        )
        if require_run_instructions:
            return create_model(
                "ArtifactResult",
                __base__=ArtifactResult,
                language=language,
                run_instructions=required_run_instructions_field(),
                referenced_tables=referenced_tables,
            )
        return create_model(
            "ArtifactResult",
            __base__=ArtifactResult,
            language=language,
            referenced_tables=referenced_tables,
        )

    if require_run_instructions:
        return create_model(
            "ArtifactResult",
            __base__=ArtifactResult,
            run_instructions=required_run_instructions_field(),
            referenced_tables=referenced_tables,
        )
    return create_model(
        "ArtifactResult",
        __base__=ArtifactResult,
        referenced_tables=referenced_tables,
    )


def build_artifact_system_prompt(
    selected_items: list[GalleryItem],
    schema: str,
    custom_directions: str,
    *,
    format_id: str,
    language: ArtifactLanguage | None,
    data_instructions: str = "",
) -> str:
    template = load_template("artifact-system.md")

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
        "language_label": LANGUAGES[language] if language is not None else "",
        "format_quarto": format_id == "quarto-dashboard",
        "format_marimo": format_id == "marimo-notebook",
        "format_shiny": format_id == "shiny-app",
        "format_jupyter": format_id == "jupyter-notebook",
        "lang_python": language == "python",
        "lang_r": language == "r",
        "language_unspecified": language is None,
    }

    return chevron.render(template, context)


def build_artifact_user_prompt(
    artifact_format: ArtifactFormat,
    language: ArtifactLanguage | None,
) -> str:
    if language is None:
        return (
            f"Generate the complete source for a {artifact_format.label} artifact. "
            "Choose one supported language and report it in the structured result."
        )
    return (
        f"Generate the complete source for a {artifact_format.label} artifact "
        f"in {LANGUAGES[language]}."
    )


def build_freeform_artifact_user_prompt(
    format_name: str,
    language: ArtifactLanguage | None,
) -> str:
    if language is None:
        return (
            f"Generate the complete source for a {format_name} artifact. "
            "Choose one supported language and report it in the structured result."
        )
    return (
        f"Generate the complete source for a {format_name} artifact "
        f"in {LANGUAGES[language]}."
    )


def build_artifact_repair_prompt(
    error: ArtifactValidationError,
    artifact_type: ArtifactType,
) -> str:
    language = (
        LANGUAGES[artifact_type.language]
        if artifact_type.language is not None
        else "the previously selected language"
    )
    return (
        "The generated artifact failed structural validation:\n\n"
        f"{error}\n\n"
        f"Return the complete corrected {artifact_type.label} source in {language}. "
        "Preserve the requested analysis and use the same registered data tables."
    )


def build_recommend_prompt(
    items: list[GalleryItem],
    artifact_formats: dict[str, ArtifactFormat],
) -> str:
    template = load_template("artifact-recommend.md")

    item_dicts = []
    for item in items:
        kind = "visualization" if isinstance(item, VizGalleryItem) else "query"
        item_dicts.append({"id": item.id, "title": item.title, "kind": kind})

    format_dicts = [
        {"id": type_id, "label": art_type.label, "description": art_type.description}
        for type_id, art_type in artifact_formats.items()
    ]

    context = {
        "items": item_dicts,
        "formats": format_dicts,
    }

    return chevron.render(template, context)


def prompts_dir() -> Path:
    return Path(__file__).parent / "prompts"


def load_template(filename: str) -> str:
    return (prompts_dir() / filename).read_text()


def required_run_instructions_field() -> tuple[type[str], FieldInfo]:
    return (
        str,
        Field(
            description=(
                "Concise Markdown explaining how to run the generated artifact, "
                "including fenced command blocks where appropriate."
            )
        ),
    )
