from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import chevron
from pydantic import BaseModel, Field, create_model

from ._artifact_gallery import GalleryItem, QueryGalleryItem, VizGalleryItem
from ._artifact_types import LANGUAGES

if TYPE_CHECKING:
    from ._artifact_types import ArtifactType


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
    summary: str = Field(
        default="",
        description="A brief, succinct summary of what this artifact shows or does, useful at a glance.",
    )
    install_instructions: str = Field(
        default="",
        description="Concise Markdown for installing the artifact's software dependencies: a short intro line followed by a fenced code block of install commands. Cover only installation, not how to run it.",
    )


class FreeformMetadata(BaseModel):
    file_extension: str = Field(
        description="File extension for this format, including the leading dot (e.g., '.Rmd', '.py', '.sql')"
    )
    editor_language: str = Field(
        description="Editor syntax highlighting language (e.g., 'markdown', 'python', 'sql')"
    )
    run_instructions: str = Field(
        description="Shell command to run or open a file of this format, using {filename} as a placeholder for the file name (e.g., 'Rscript -e \"rmarkdown::render(\\'{filename}\\')\"')"
    )


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


def build_artifact_system_prompt(
    selected_items: list[GalleryItem],
    schema: str,
    custom_directions: str,
    data_instructions: str = "",
    language_label: str = "",
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
        "language_label": language_label,
        "lang_python": language_label == LANGUAGES["python"],
        "lang_r": language_label == LANGUAGES["r"],
    }

    return chevron.render(template, context)


def build_artifact_user_prompt(
    artifact_type: ArtifactType,
    language_label: str = "",
) -> str:
    notes = (
        f" {artifact_type.generation_notes}" if artifact_type.generation_notes else ""
    )
    language = f" Write it in {language_label}." if language_label else ""
    return f"Generate the complete source for a {artifact_type.label}.{notes}{language}"


def build_recommend_prompt(
    items: list[GalleryItem],
    artifact_types: dict[str, ArtifactType],
) -> str:
    template = load_template("artifact-recommend.md")

    item_dicts = []
    for item in items:
        kind = "visualization" if isinstance(item, VizGalleryItem) else "query"
        item_dicts.append({"id": item.id, "title": item.title, "kind": kind})

    format_dicts = [
        {"id": type_id, "label": art_type.label, "description": art_type.description}
        for type_id, art_type in artifact_types.items()
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
