from querychat._handoff_orchestrator import (
    GenerateRequest,
    build_freeform_handoff_type,
    parse_generate_payload,
)
from querychat._handoff_prompt import FreeformMetadata


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


class TestBuildFreeformHandoffType:
    def test_prepends_missing_dot_to_extension(self):
        meta = FreeformMetadata(
            file_extension="sql",
            editor_language="sql",
            run_instructions="duckdb < {filename}",
        )
        handoff_type = build_freeform_handoff_type("SQL script", meta, "python")
        assert handoff_type.file_extension == ".sql"

    def test_preserves_existing_dot_and_metadata(self):
        meta = FreeformMetadata(
            file_extension=".md",
            editor_language="markdown",
            run_instructions="open {filename}",
        )
        handoff_type = build_freeform_handoff_type("R Markdown report", meta, "r")
        assert handoff_type.id == "other"
        assert handoff_type.label == "R Markdown report"
        assert handoff_type.file_extension == ".md"
        assert handoff_type.editor_language == "markdown"
