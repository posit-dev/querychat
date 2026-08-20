import pytest
import querychat._handoff_prompt as handoff_prompt
from pydantic import ValidationError
from querychat._handoff_gallery import GalleryItem, QueryGalleryItem, VizGalleryItem
from querychat._handoff_prompt import (
    FreeformMetadata,
    HandoffResult,
    Recommendation,
    build_handoff_system_prompt,
    build_handoff_user_prompt,
    build_recommend_prompt,
    recommendation_model,
)
from querychat._handoff_types import HANDOFF_FORMATS, resolve_handoff_type
from querychat._handoff_validation import HandoffValidationError


class TestRecommendation:
    def test_default_directions(self):
        rec = Recommendation(selected_ids=["viz-0"], format_id="quarto-dashboard")
        assert rec.directions == ""

    def test_all_fields(self):
        rec = Recommendation(
            selected_ids=["viz-0", "query-1"],
            format_id="marimo-notebook",
            directions="Use a 2x2 grid layout",
        )
        assert rec.selected_ids == ["viz-0", "query-1"]
        assert rec.format_id == "marimo-notebook"
        assert rec.directions == "Use a 2x2 grid layout"


class TestRecommendationModel:
    def test_constrains_item_ids(self):
        model = recommendation_model(
            item_ids=["viz-0", "query-1"],
            format_ids=["quarto-dashboard"],
        )
        rec = model(selected_ids=["viz-0"], format_id="quarto-dashboard")
        assert rec.selected_ids == ["viz-0"]

        with pytest.raises(ValidationError):
            model(selected_ids=["bogus-id"], format_id="quarto-dashboard")

    def test_constrains_format_ids(self):
        model = recommendation_model(
            item_ids=["viz-0"],
            format_ids=["quarto-dashboard", "marimo-notebook"],
        )
        rec = model(selected_ids=["viz-0"], format_id="marimo-notebook")
        assert rec.format_id == "marimo-notebook"

        with pytest.raises(ValidationError):
            model(selected_ids=["viz-0"], format_id="bogus-format")

    def test_is_subclass_of_recommendation(self):
        model = recommendation_model(
            item_ids=["viz-0"],
            format_ids=["quarto-dashboard"],
        )
        rec = model(selected_ids=["viz-0"], format_id="quarto-dashboard")
        assert isinstance(rec, Recommendation)

    def test_enum_in_json_schema(self):
        model = recommendation_model(
            item_ids=["viz-0", "query-1"],
            format_ids=["quarto-dashboard", "shiny-app"],
        )
        schema = model.model_json_schema()
        format_field = schema["properties"]["format_id"]
        assert set(format_field["enum"]) == {"quarto-dashboard", "shiny-app"}


class TestFreeformMetadata:
    def test_has_only_target_metadata(self):
        assert set(FreeformMetadata.model_fields) == {
            "file_extension",
            "editor_language",
        }

    def test_basic_fields(self):
        meta = FreeformMetadata(
            file_extension=".Rmd",
            editor_language="markdown",
        )
        assert meta.file_extension == ".Rmd"
        assert meta.editor_language == "markdown"

    @pytest.mark.parametrize(
        "file_extension",
        ["../handoff.py", "unsafe/handoff.py", r"..\handoff.py", ".py\x00"],
    )
    def test_rejects_unsafe_file_extensions(self, file_extension: str):
        with pytest.raises(ValidationError, match="safe file extension"):
            FreeformMetadata(
                file_extension=file_extension,
                editor_language="python",
            )

    def test_json_schema_has_descriptions(self):
        schema = FreeformMetadata.model_json_schema()
        props = schema["properties"]
        assert "description" in props["file_extension"]
        assert "description" in props["editor_language"]


class TestBuildHandoffSystemPrompt:
    def test_returns_nonempty_string(self):
        items: list[GalleryItem] = [
            VizGalleryItem(
                id="viz-0",
                title="Sales",
                thumbnail=None,
                ggsql="SELECT x FROM t VISUALISE x DRAW bar",
            ),
        ]
        result = build_handoff_system_prompt(
            selected_items=items,
            schema="CREATE TABLE t (x INT, y INT)",
            custom_directions="Use a dark theme",
            format_id="quarto-dashboard",
            language="python",
        )
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Sales" in result
        assert "dark theme" in result
        assert "CREATE TABLE" in result

    def test_includes_query_items(self):
        items: list[GalleryItem] = [
            QueryGalleryItem(
                id="query-0", title="Total revenue", sql="SELECT SUM(rev) FROM t"
            ),
        ]
        result = build_handoff_system_prompt(
            selected_items=items,
            schema="CREATE TABLE t (rev INT)",
            custom_directions="",
            format_id="quarto-dashboard",
            language="python",
        )
        assert "SUM(rev)" in result

    def test_preserves_source_fidelity_and_escapes_titles(self):
        sql = (
            'SELECT "name", amount\n'
            "FROM sales\n"
            "WHERE amount > 10 AND note < 'x' AND tag = 'R&D'"
        )
        ggsql = (
            'SELECT "category", SUM(amount) AS total\n'
            "FROM sales\n"
            "WHERE amount >= 10 AND note < 'x&y'\n"
            "VISUALISE category, total\n"
            "DRAW bar"
        )
        items: list[GalleryItem] = [
            VizGalleryItem(
                id="viz-0",
                title='Revenue <raw> & "quoted"',
                thumbnail=None,
                ggsql=ggsql,
            ),
            QueryGalleryItem(id="query-0", title="Query", sql=sql),
        ]

        result = build_handoff_system_prompt(
            selected_items=items,
            schema="CREATE TABLE sales (name TEXT, amount INT, note TEXT, tag TEXT)",
            custom_directions="",
            format_id="quarto-dashboard",
            language="python",
        )

        assert sql in result
        assert ggsql in result
        assert "Revenue &lt;raw&gt; &amp; &quot;quoted&quot;" in result
        assert 'Revenue <raw> & "quoted"' not in result

    def test_renders_shared_sections(self):
        items: list[GalleryItem] = [
            VizGalleryItem(id="viz-0", title="Chart", thumbnail=None, ggsql="SELECT 1"),
        ]
        result = build_handoff_system_prompt(
            selected_items=items,
            schema="CREATE TABLE t (x INT)",
            custom_directions="custom note",
            format_id="quarto-dashboard",
            language="python",
            data_instructions="Load from bundled CSV",
        )
        assert "Database schema" in result
        assert "Data access" in result
        assert "bundled CSV" in result
        assert "Selected results" in result
        assert "custom note" in result

    def test_names_ggsql_as_source_of_visuals(self):
        result = build_handoff_system_prompt(
            selected_items=[],
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
            format_id="quarto-dashboard",
            language="python",
        )
        assert "ggsql" in result

    def test_does_not_name_a_specific_handoff_type_as_the_task(self):
        # The chosen handoff type belongs in the user prompt, not the system
        # prompt. The system prompt frames a generic "standalone handoff".
        result = build_handoff_system_prompt(
            selected_items=[],
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
            format_id="quarto-dashboard",
            language="python",
        )
        assert "standalone" in result


class TestBuildHandoffUserPrompt:
    def test_mentions_label(self):
        prompt = build_handoff_user_prompt(
            HANDOFF_FORMATS["quarto-dashboard"],
            language="python",
        )
        assert "Quarto" in prompt

    def test_no_longer_instructs_about_code_fences(self):
        prompt = build_handoff_user_prompt(
            HANDOFF_FORMATS["shiny-app"],
            language="python",
        )
        assert "code fence" not in prompt.lower()
        assert "verbatim" not in prompt.lower()

    def test_names_only_format_and_explicit_language(self):
        result = build_handoff_user_prompt(
            HANDOFF_FORMATS["shiny-app"],
            language="r",
        )
        assert result == "Generate the complete source for a Shiny handoff in R."


def test_repair_prompt_includes_error_target_and_resolved_language():
    error = HandoffValidationError("Generated source is not valid notebook JSON.")
    handoff_type = resolve_handoff_type("jupyter-notebook", "r")

    result = handoff_prompt.build_handoff_repair_prompt(error, handoff_type)

    assert str(error) in result
    assert handoff_type.label in result
    assert "in R" in result
    assert "same registered data tables" in result


def test_external_data_repair_prompt_is_self_contained():
    handoff_type = resolve_handoff_type("jupyter-notebook", "python")

    result = handoff_prompt.build_external_data_repair_system_prompt(
        handoff_type=handoff_type,
        schema="Table: tips\nColumns:\n- total_bill DOUBLE",
        data_instructions="DATA SETUP: load equivalent tips data.",
        referenced_tables=["tips"],
    )

    assert "first code cell" in result
    assert "Table: tips" in result
    assert "load equivalent tips data" in result
    assert '["tips"]' in result
    assert "exact same referenced-table set" in result
    assert "paths, credentials, or environment variables" in result
    assert "DataFrame snapshots exceed the bundle limit" in result
    assert "preceding conversation contains the complete source to revise" in result
    assert "Call it DATA SETUP and make it visually prominent" in result
    assert "Never invent or hardcode credentials" in result
    assert (
        f"Return the complete corrected {handoff_type.label} source and structured "
        "metadata, not a patch or explanation."
        in result
    )


@pytest.mark.parametrize(
    ("format_id", "setup_location"),
    [
        ("quarto-dashboard", "dedicated DATA SETUP code chunk"),
        ("shiny-app", "prominent top-level DATA SETUP block"),
    ],
)
def test_external_data_repair_prompt_uses_target_setup_location(
    format_id: str,
    setup_location: str,
):
    handoff_type = resolve_handoff_type(format_id, "python")

    result = handoff_prompt.build_external_data_repair_system_prompt(
        handoff_type=handoff_type,
        schema="Table: tips",
        data_instructions="Load tips data.",
        referenced_tables=["tips"],
    )

    assert setup_location in result


class TestBuildRecommendPrompt:
    def test_returns_nonempty_string(self):
        items = [
            VizGalleryItem(id="viz-0", title="Sales", thumbnail=None, ggsql="..."),
            QueryGalleryItem(id="query-0", title="Count", sql="SELECT COUNT(*) FROM t"),
        ]
        result = build_recommend_prompt(
            items=items,
            handoff_formats=HANDOFF_FORMATS,
        )
        assert isinstance(result, str)
        assert "viz-0" in result
        assert "query-0" in result

    def test_includes_available_formats(self):
        items: list[GalleryItem] = [
            VizGalleryItem(id="viz-0", title="Sales", thumbnail=None, ggsql="..."),
        ]
        result = build_recommend_prompt(
            items=items,
            handoff_formats=HANDOFF_FORMATS,
        )
        for format_id, handoff_format in HANDOFF_FORMATS.items():
            assert format_id in result
            assert handoff_format.label in result


class TestHandoffResult:
    def test_source_required_metadata_optional(self):
        r = HandoffResult(
            source="print('hi')",
            language="python",
            referenced_tables=[],
        )
        assert r.source == "print('hi')"
        assert r.language == "python"
        assert r.summary == ""
        assert r.install_instructions == ""

    def test_accepts_run_instructions(self):
        result = HandoffResult(
            source="print('ok')",
            language="python",
            run_instructions="Run it with:\n```bash\npython handoff.py\n```",
            referenced_tables=[],
        )
        assert "python handoff.py" in result.run_instructions

    def test_source_field_is_first(self):
        # source must stream before metadata, so it must be declared first
        assert list(HandoffResult.model_fields) == [
            "source",
            "language",
            "summary",
            "install_instructions",
            "run_instructions",
            "referenced_tables",
        ]

    def test_model_constrains_table_names(self):
        model = handoff_prompt.handoff_result_model(
            ["orders", "customers"],
            ("python",),
        )
        result = model(
            source="print('ok')",
            language="python",
            referenced_tables=["orders"],
        )
        assert result.referenced_tables == ["orders"]

        with pytest.raises(ValidationError):
            model(
                source="print('bad')",
                referenced_tables=["payments"],
            )

    def test_model_allows_no_table_references(self):
        model = handoff_prompt.handoff_result_model(["orders"], ("python",))
        result = model(
            source="print('static')",
            language="python",
            referenced_tables=[],
        )
        assert result.referenced_tables == []

    def test_model_constrains_languages(self):
        model = handoff_prompt.handoff_result_model(
            ["orders"],
            ("python", "r"),
        )

        assert (
            model(
                source="print('ok')",
                language="r",
                referenced_tables=[],
            ).language
            == "r"
        )
        with pytest.raises(ValidationError, match="language"):
            model(
                source="print('bad')",
                language="javascript",
                referenced_tables=[],
            )

    def test_model_requires_language_when_constrained(self):
        model = handoff_prompt.handoff_result_model(["orders"], ("python",))

        with pytest.raises(ValidationError, match="language"):
            model(source="print('bad')", referenced_tables=[])

    def test_model_can_require_run_instructions(self):
        model = handoff_prompt.handoff_result_model(
            ["orders"],
            ("python",),
            require_run_instructions=True,
        )

        with pytest.raises(ValidationError, match="run_instructions"):
            model(source="print('bad')", referenced_tables=[])

        result = model(
            source="print('ok')",
            language="python",
            run_instructions="```bash\npython handoff.py\n```",
            referenced_tables=[],
        )
        assert "python handoff.py" in result.run_instructions


class TestHandoffPromptTargets:
    def _items(self) -> list[GalleryItem]:
        return [
            VizGalleryItem(
                id="viz-0",
                title="Chart",
                thumbnail=None,
                ggsql="SELECT x FROM t VISUALISE x DRAW bar",
            ),
        ]

    def test_r_jupyter_prompt_uses_r_ggsql_guidance_without_ggsql_kernel(self):
        result = build_handoff_system_prompt(
            selected_items=[],
            schema="",
            custom_directions="",
            format_id="jupyter-notebook",
            language="r",
        )
        assert "ggsql_execute" in result
        assert 'kernel to `"ggsql"`' not in result
        assert "render_altair" not in result

    def test_python_jupyter_prompt_uses_python_api(self):
        result = build_handoff_system_prompt(
            selected_items=[],
            schema="",
            custom_directions="",
            format_id="jupyter-notebook",
            language="python",
        )
        assert "ggsql.render_altair" in result
        assert "ggsql_execute" not in result

    def test_quarto_prompt_keeps_native_ggsql_chunks(self):
        result = build_handoff_system_prompt(
            selected_items=[],
            schema="",
            custom_directions="",
            format_id="quarto-dashboard",
            language="r",
        )
        assert "```{ggsql}" in result

    def test_user_prompt_names_selected_language(self):
        result = build_handoff_user_prompt(
            HANDOFF_FORMATS["shiny-app"],
            language="r",
        )
        assert result == "Generate the complete source for a Shiny handoff in R."
