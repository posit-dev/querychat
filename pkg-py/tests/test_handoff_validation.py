import nbformat
import pytest
from querychat._handoff_types import HandoffLanguage, resolve_handoff_type
from querychat._handoff_validation import (
    HandoffValidationError,
    validate_handoff_source,
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
def test_valid_notebook_matches_target_language(language: HandoffLanguage) -> None:
    handoff_type = resolve_handoff_type("jupyter-notebook", language)

    validate_handoff_source(notebook_source(language), handoff_type)


def test_notebook_language_comparison_is_case_insensitive() -> None:
    handoff_type = resolve_handoff_type("jupyter-notebook", "r")

    validate_handoff_source(notebook_source("R"), handoff_type)


def test_malformed_notebook_json_is_rejected() -> None:
    handoff_type = resolve_handoff_type("jupyter-notebook", "r")

    with pytest.raises(HandoffValidationError, match="valid notebook JSON"):
        validate_handoff_source("{", handoff_type)


def test_invalid_notebook_schema_is_rejected() -> None:
    handoff_type = resolve_handoff_type("jupyter-notebook", "r")
    source = '{"nbformat": 4, "nbformat_minor": 5, "metadata": {}}'

    with pytest.raises(HandoffValidationError, match="valid notebook JSON"):
        validate_handoff_source(source, handoff_type)


def test_mismatched_kernel_language_is_rejected() -> None:
    handoff_type = resolve_handoff_type("jupyter-notebook", "r")

    with pytest.raises(HandoffValidationError, match="R kernelspec"):
        validate_handoff_source(notebook_source("python"), handoff_type)


def test_text_target_requires_nonempty_source() -> None:
    handoff_type = resolve_handoff_type("shiny-app", "python")

    with pytest.raises(HandoffValidationError, match="empty"):
        validate_handoff_source("  ", handoff_type)
