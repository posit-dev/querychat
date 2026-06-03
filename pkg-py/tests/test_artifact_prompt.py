import pytest
from pydantic import ValidationError
from querychat._artifact_gallery import GalleryItem, QueryGalleryItem, VizGalleryItem
from querychat._artifact_prompt import (
    ArtifactResult,
    FreeformMetadata,
    Recommendation,
    build_artifact_system_prompt,
    build_artifact_user_prompt,
    build_recommend_prompt,
    recommendation_model,
)
from querychat._artifact_types import ARTIFACT_TYPES


class TestRecommendation:
    def test_default_directions(self):
        rec = Recommendation(
            selected_ids=["viz-0"], format_id="quarto-dashboard"
        )
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
    def test_has_run_instructions_field(self):
        assert "run_instructions" in FreeformMetadata.model_fields

    def test_basic_fields(self):
        meta = FreeformMetadata(
            file_extension=".Rmd",
            editor_language="markdown",
            run_instructions="Rscript -e \"rmarkdown::render('{filename}')\"",
        )
        assert meta.file_extension == ".Rmd"
        assert meta.editor_language == "markdown"
        assert "{filename}" in meta.run_instructions

    def test_json_schema_has_descriptions(self):
        schema = FreeformMetadata.model_json_schema()
        props = schema["properties"]
        assert "description" in props["file_extension"]
        assert "description" in props["editor_language"]
        assert "description" in props["run_instructions"]


class TestBuildArtifactSystemPrompt:
    def test_returns_nonempty_string(self):
        items: list[GalleryItem] = [
            VizGalleryItem(
                id="viz-0",
                title="Sales",
                thumbnail=None,
                ggsql="SELECT x FROM t VISUALISE x DRAW bar",
            ),
        ]
        result = build_artifact_system_prompt(
            selected_items=items,
            schema="CREATE TABLE t (x INT, y INT)",
            custom_directions="Use a dark theme",
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
        result = build_artifact_system_prompt(
            selected_items=items,
            schema="CREATE TABLE t (rev INT)",
            custom_directions="",
        )
        assert "SUM(rev)" in result

    def test_renders_shared_sections(self):
        items: list[GalleryItem] = [
            VizGalleryItem(
                id="viz-0", title="Chart", thumbnail=None, ggsql="SELECT 1"
            ),
        ]
        result = build_artifact_system_prompt(
            selected_items=items,
            schema="CREATE TABLE t (x INT)",
            custom_directions="custom note",
            data_instructions="Load from bundled CSV",
        )
        assert "Database schema" in result
        assert "Data access" in result
        assert "bundled CSV" in result
        assert "Selected results" in result
        assert "custom note" in result

    def test_names_ggsql_as_source_of_visuals(self):
        result = build_artifact_system_prompt(
            selected_items=[],
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
        )
        assert "ggsql" in result

    def test_does_not_name_a_specific_artifact_type_as_the_task(self):
        # The chosen artifact type belongs in the user prompt, not the system
        # prompt. The system prompt frames a generic "standalone artifact".
        result = build_artifact_system_prompt(
            selected_items=[],
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
        )
        assert "standalone" in result


class TestBuildArtifactUserPrompt:
    def test_mentions_label_and_notes(self):
        prompt = build_artifact_user_prompt(ARTIFACT_TYPES["quarto-dashboard"])
        assert "Quarto" in prompt
        assert "dashboard layout" in prompt

    def test_no_longer_instructs_about_code_fences(self):
        prompt = build_artifact_user_prompt(ARTIFACT_TYPES["shiny-app"])
        assert "code fence" not in prompt.lower()
        assert "verbatim" not in prompt.lower()

    def test_includes_language_when_given(self):
        prompt = build_artifact_user_prompt(
            ARTIFACT_TYPES["shiny-app"], language_label="R"
        )
        assert "Write it in R" in prompt


class TestBuildRecommendPrompt:
    def test_returns_nonempty_string(self):
        items = [
            VizGalleryItem(id="viz-0", title="Sales", thumbnail=None, ggsql="..."),
            QueryGalleryItem(id="query-0", title="Count", sql="SELECT COUNT(*) FROM t"),
        ]
        result = build_recommend_prompt(
            items=items,
            artifact_types=ARTIFACT_TYPES,
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
            artifact_types=ARTIFACT_TYPES,
        )
        for type_id, art_type in ARTIFACT_TYPES.items():
            assert type_id in result
            assert art_type.label in result


class TestArtifactResult:
    def test_source_required_metadata_optional(self):
        r = ArtifactResult(source="print('hi')")
        assert r.source == "print('hi')"
        assert r.summary == ""
        assert r.install_instructions == ""

    def test_source_field_is_first(self):
        # source must stream before metadata, so it must be declared first
        assert list(ArtifactResult.model_fields) == [
            "source",
            "summary",
            "install_instructions",
        ]


class TestLanguagePreferenceInPrompt:
    def _items(self) -> list[GalleryItem]:
        return [
            VizGalleryItem(
                id="viz-0",
                title="Chart",
                thumbnail=None,
                ggsql="SELECT x FROM t VISUALISE x DRAW bar",
            ),
        ]

    def test_no_preference_omits_language_instruction(self):
        result = build_artifact_system_prompt(
            selected_items=self._items(),
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
        )
        assert "Generate this artifact in" not in result

    def test_python_preference_adds_instruction(self):
        result = build_artifact_system_prompt(
            selected_items=self._items(),
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
            language_label="Python",
        )
        assert "Generate this artifact in Python" in result

    def test_r_preference_uses_r_ggsql_binding(self):
        result = build_artifact_system_prompt(
            selected_items=self._items(),
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
            language_label="R",
        )
        assert "Generate this artifact in R" in result
        assert "ggsql_execute" in result
        assert "render_altair" not in result

    def test_python_preference_uses_python_ggsql_api(self):
        result = build_artifact_system_prompt(
            selected_items=self._items(),
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
            language_label="Python",
        )
        assert "render_altair" in result
        assert "ggsql_execute" not in result

    def test_no_preference_shows_both_ggsql_variants(self):
        result = build_artifact_system_prompt(
            selected_items=self._items(),
            schema="CREATE TABLE t (x INT)",
            custom_directions="",
        )
        assert "render_altair" in result
        assert "ggsql_execute" in result

    def test_user_prompt_includes_language(self):
        result = build_artifact_user_prompt(
            ARTIFACT_TYPES["shiny-app"], language_label="R"
        )
        assert "Write it in R." in result

    def test_user_prompt_without_language_unchanged(self):
        result = build_artifact_user_prompt(ARTIFACT_TYPES["shiny-app"])
        assert "Write it in" not in result


