from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from ._icons import (
    ICON_NAMES,  # noqa: TC001 — pydantic needs this at runtime for field validation
)

if TYPE_CHECKING:
    from shiny.ui._input_code_editor import CodeEditorLanguage

    EditorLanguage = CodeEditorLanguage
else:
    EditorLanguage = str


LANGUAGES: dict[str, str] = {"r": "R", "python": "Python"}


class LanguageVariant(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_extension: str | None = None
    editor_language: EditorLanguage | None = None
    run_instructions: str | None = None
    generation_notes: str | None = None


class ArtifactType(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    file_extension: str
    description: str
    editor_language: EditorLanguage
    generation_notes: str = ""
    run_instructions: str = ""
    icon: ICON_NAMES = "file-earmark-code"
    supported_languages: tuple[str, ...] = ("python", "r")
    language_variants: dict[str, LanguageVariant] = Field(default_factory=dict)


ARTIFACT_TYPES: dict[str, ArtifactType] = {
    "quarto-dashboard": ArtifactType(
        id="quarto-dashboard",
        label="Quarto",
        file_extension=".qmd",
        description="A Quarto dashboard with layout, cards, and ggsql visualizations",
        editor_language="markdown",
        generation_notes="Use a Quarto dashboard layout with rows, columns, and cards.",
        run_instructions="quarto preview {filename}",
        icon="grid-1x2-fill",
    ),
    "marimo-notebook": ArtifactType(
        id="marimo-notebook",
        label="Marimo",
        file_extension=".py",
        description="A marimo reactive notebook",
        editor_language="python",
        generation_notes="Write a reactive marimo notebook.",
        run_instructions="marimo edit {filename}",
        icon="journal-code",
        supported_languages=("python",),
    ),
    "shiny-app": ArtifactType(
        id="shiny-app",
        label="Shiny",
        file_extension=".py",
        description="A Shiny for Python application",
        editor_language="python",
        generation_notes="Use Shiny for Python Express syntax.",
        run_instructions="shiny run --reload {filename}",
        icon="lightning-fill",
        language_variants={
            "r": LanguageVariant(
                file_extension=".R",
                editor_language="r",
                run_instructions='R -e "shiny::runApp(\'{filename}\')"',
                generation_notes="Use Shiny for R (a single app.R defining the UI and server).",
            )
        },
    ),
    "jupyter-notebook": ArtifactType(
        id="jupyter-notebook",
        label="Jupyter",
        file_extension=".ipynb",
        description="A Jupyter notebook",
        editor_language="json",
        generation_notes="Output valid `.ipynb` notebook JSON.",
        run_instructions="jupyter lab {filename}",
        icon="file-earmark-code",
    ),
}


def resolve_for_language(
    artifact_type: ArtifactType, language: str | None
) -> ArtifactType:
    if not language or language not in artifact_type.supported_languages:
        return artifact_type
    variant = artifact_type.language_variants.get(language)
    if variant is None:
        return artifact_type
    return artifact_type.model_copy(update=variant.model_dump(exclude_none=True))
