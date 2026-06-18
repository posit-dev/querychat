from querychat._artifact_orchestrator import (
    GenerateRequest,
    build_freeform_artifact_type,
    parse_generate_payload,
)
from querychat._artifact_prompt import FreeformMetadata


class TestParseGeneratePayload:
    def test_parses_full_payload(self):
        raw = {
            "selected_ids": ["viz-0", "query-1"],
            "type": "shiny-app",
            "language": "r",
            "freeform": "  Streamlit app  ",
        }
        req = parse_generate_payload(raw, default_type="quarto-dashboard")
        assert req == GenerateRequest(
            selected_ids=["viz-0", "query-1"],
            type_id="shiny-app",
            language="r",
            freeform="Streamlit app",
        )

    def test_non_dict_returns_defaults(self):
        req = parse_generate_payload(None, default_type="quarto-dashboard")
        assert req == GenerateRequest(
            selected_ids=[], type_id="quarto-dashboard", language="", freeform=""
        )

    def test_missing_type_uses_default(self):
        req = parse_generate_payload(
            {"selected_ids": []}, default_type="marimo-notebook"
        )
        assert req.type_id == "marimo-notebook"

    def test_empty_type_uses_default(self):
        req = parse_generate_payload({"type": ""}, default_type="marimo-notebook")
        assert req.type_id == "marimo-notebook"

    def test_ignores_non_list_selected_ids(self):
        req = parse_generate_payload(
            {"selected_ids": "viz-0"}, default_type="quarto-dashboard"
        )
        assert req.selected_ids == []

    def test_coerces_selected_ids_to_str(self):
        req = parse_generate_payload(
            {"selected_ids": [0, 1]}, default_type="quarto-dashboard"
        )
        assert req.selected_ids == ["0", "1"]


class TestBuildFreeformArtifactType:
    def test_prepends_missing_dot_to_extension(self):
        meta = FreeformMetadata(
            file_extension="sql",
            editor_language="sql",
            run_instructions="duckdb < {filename}",
        )
        art_type = build_freeform_artifact_type("SQL script", meta)
        assert art_type.file_extension == ".sql"

    def test_preserves_existing_dot_and_metadata(self):
        meta = FreeformMetadata(
            file_extension=".md",
            editor_language="markdown",
            run_instructions="open {filename}",
        )
        art_type = build_freeform_artifact_type("R Markdown report", meta)
        assert art_type.id == "other"
        assert art_type.label == "R Markdown report"
        assert art_type.file_extension == ".md"
        assert art_type.editor_language == "markdown"
        assert art_type.run_instructions == "open {filename}"
