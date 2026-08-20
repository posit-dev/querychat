import pytest
from pydantic import ValidationError
from querychat._artifact_types import (
    ARTIFACT_FORMATS,
    LANGUAGES,
    ArtifactRegistry,
    ArtifactType,
    resolve_artifact_target,
    resolve_artifact_type,
)


class TestArtifactType:
    def test_resolved_type_is_serializable_target_snapshot(self):
        artifact_type = resolve_artifact_type("shiny-app", "r")

        assert artifact_type.model_dump(mode="json") == {
            "id": "shiny-app",
            "label": "Shiny",
            "icon": "lightning-fill",
            "language": "r",
            "file_extension": ".R",
            "editor_language": "r",
            "structure": "text",
        }

    def test_freeform_type_defaults_to_text_structure(self):
        artifact_type = ArtifactType(
            id="other",
            label="SQL script",
            language="python",
            file_extension=".sql",
            editor_language="sql",
        )

        assert artifact_type.structure == "text"

    def test_has_no_generation_or_run_metadata(self):
        assert "generation_notes" not in ArtifactType.model_fields
        assert "run_instructions" not in ArtifactType.model_fields


class TestLanguages:
    def test_registry_is_r_and_python(self):
        assert LANGUAGES == {"r": "R", "python": "Python"}


def test_registry_loads_all_builtin_formats():
    assert set(ARTIFACT_FORMATS) == {
        "quarto-dashboard",
        "marimo-notebook",
        "shiny-app",
        "jupyter-notebook",
    }


def test_shiny_targets_resolve_complete_mechanical_metadata():
    python = resolve_artifact_target("shiny-app", "python")
    r = resolve_artifact_target("shiny-app", "r")

    assert (python.file_extension, python.editor_language) == (".py", "python")
    assert (r.file_extension, r.editor_language) == (".R", "r")
    assert python.structure == r.structure == "text"


def test_resolve_artifact_type_combines_format_and_target():
    resolved = resolve_artifact_type("jupyter-notebook", "python")

    assert resolved.label == ARTIFACT_FORMATS["jupyter-notebook"].label
    assert resolved.language == "python"
    assert resolved.file_extension == ".ipynb"
    assert resolved.editor_language == "json"
    assert resolved.structure == "notebook-json"


def test_unsupported_language_does_not_fall_back():
    with pytest.raises(ValueError, match="does not support R"):
        resolve_artifact_type("marimo-notebook", "r")


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError, match="Unknown artifact format: missing"):
        resolve_artifact_type("missing", "python")


def test_registry_rejects_unknown_structure():
    with pytest.raises(ValidationError, match="structure"):
        ArtifactRegistry.model_validate(
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
