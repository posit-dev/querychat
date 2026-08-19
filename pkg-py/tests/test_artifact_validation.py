import nbformat
import pytest
from querychat._artifact_types import ArtifactLanguage, resolve_artifact_type
from querychat._artifact_validation import (
    ArtifactValidationError,
    validate_artifact_source,
)


def notebook_source(language: str) -> str:
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("1 + 1")],
        metadata={
            "kernelspec": {
                "display_name": language,
                "language": language,
                "name": "test",
            }
        },
    )
    return nbformat.writes(notebook)


@pytest.mark.parametrize("language", ["python", "r"])
def test_valid_notebook_matches_target_language(language: ArtifactLanguage) -> None:
    artifact_type = resolve_artifact_type("jupyter-notebook", language)

    validate_artifact_source(notebook_source(language), artifact_type)


def test_notebook_language_comparison_is_case_insensitive() -> None:
    artifact_type = resolve_artifact_type("jupyter-notebook", "r")

    validate_artifact_source(notebook_source("R"), artifact_type)


def test_malformed_notebook_json_is_rejected() -> None:
    artifact_type = resolve_artifact_type("jupyter-notebook", "r")

    with pytest.raises(ArtifactValidationError, match="valid notebook JSON"):
        validate_artifact_source("{", artifact_type)


def test_invalid_notebook_schema_is_rejected() -> None:
    artifact_type = resolve_artifact_type("jupyter-notebook", "r")
    source = '{"nbformat": 4, "nbformat_minor": 5, "metadata": {}}'

    with pytest.raises(ArtifactValidationError, match="valid notebook JSON"):
        validate_artifact_source(source, artifact_type)


def test_mismatched_kernel_language_is_rejected() -> None:
    artifact_type = resolve_artifact_type("jupyter-notebook", "r")

    with pytest.raises(ArtifactValidationError, match="R kernelspec"):
        validate_artifact_source(notebook_source("python"), artifact_type)


def test_text_target_requires_nonempty_source() -> None:
    artifact_type = resolve_artifact_type("shiny-app", "python")

    with pytest.raises(ArtifactValidationError, match="empty"):
        validate_artifact_source("  ", artifact_type)
