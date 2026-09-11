import pytest
from pydantic import ValidationError
from querychat._handoff_modal import build_language_selector
from querychat._handoff_types import (
    HANDOFF_FORMATS,
    LANGUAGES,
    HandoffRegistry,
    HandoffType,
    resolve_handoff_target,
    resolve_handoff_type,
)


class TestHandoffType:
    def test_resolved_type_is_serializable_target_snapshot(self):
        handoff_type = resolve_handoff_type("shiny-app", "r")

        assert handoff_type.model_dump(mode="json") == {
            "id": "shiny-app",
            "label": "Shiny",
            "icon": "lightning-fill",
            "language": "r",
            "file_extension": ".R",
            "editor_language": "r",
            "structure": "text",
        }

    def test_freeform_type_defaults_to_text_structure(self):
        handoff_type = HandoffType(
            id="other",
            label="SQL script",
            language="python",
            file_extension=".sql",
            editor_language="sql",
        )

        assert handoff_type.structure == "text"

    def test_has_no_generation_or_run_metadata(self):
        assert "generation_notes" not in HandoffType.model_fields
        assert "run_instructions" not in HandoffType.model_fields


class TestLanguages:
    def test_registry_is_python_and_r(self):
        assert list(LANGUAGES) == ["python", "r"]

    def test_selector_uses_python_radio_by_default(self):
        html = str(build_language_selector())

        assert "querychat-handoff-language-radio" in html
        assert 'data-language="python"' in html
        assert 'data-language="r"' in html
        assert 'checked=""' in html


def test_registry_loads_all_builtin_formats():
    assert set(HANDOFF_FORMATS) == {
        "quarto-dashboard",
        "marimo-notebook",
        "shiny-app",
        "jupyter-notebook",
    }


def test_shiny_targets_resolve_complete_mechanical_metadata():
    python = resolve_handoff_target("shiny-app", "python")
    r = resolve_handoff_target("shiny-app", "r")

    assert (python.file_extension, python.editor_language) == (".py", "python")
    assert (r.file_extension, r.editor_language) == (".R", "r")
    assert python.structure == r.structure == "text"


def test_resolve_handoff_type_combines_format_and_target():
    resolved = resolve_handoff_type("jupyter-notebook", "python")

    assert resolved.label == HANDOFF_FORMATS["jupyter-notebook"].label
    assert resolved.language == "python"
    assert resolved.file_extension == ".ipynb"
    assert resolved.editor_language == "json"
    assert resolved.structure == "notebook-json"


def test_unsupported_language_does_not_fall_back():
    with pytest.raises(ValueError, match="does not support R"):
        resolve_handoff_type("marimo-notebook", "r")


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError, match="Unknown handoff format: missing"):
        resolve_handoff_type("missing", "python")


def test_registry_rejects_unknown_structure():
    with pytest.raises(ValidationError, match="structure"):
        HandoffRegistry.model_validate(
            {
                "version": 1,
                "formats": {
                    "x": {
                        "label": "X",
                        "description": "X",
                        "icon": "file-earmark-code",
                        "targets": {
                            "python": {
                                "file_extension": ".x",
                                "editor_language": "plain",
                                "structure": "binary",
                            }
                        },
                    }
                },
            }
        )
