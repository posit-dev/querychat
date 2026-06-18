from querychat._artifact_types import (
    ARTIFACT_TYPES,
    LANGUAGES,
    ArtifactType,
    LanguageVariant,
    resolve_for_language,
)


class TestArtifactType:
    def test_quarto_dashboard_in_registry(self):
        assert "quarto-dashboard" in ARTIFACT_TYPES
        at = ARTIFACT_TYPES["quarto-dashboard"]
        assert at.label == "Quarto"
        assert at.file_extension == ".qmd"
        assert at.editor_language == "markdown"

    def test_all_types_have_required_fields(self):
        for type_id, at in ARTIFACT_TYPES.items():
            assert at.id == type_id
            assert at.label
            assert at.file_extension.startswith(".")
            assert at.description
            assert at.editor_language
            assert at.generation_notes

    def test_registry_has_four_types(self):
        assert len(ARTIFACT_TYPES) == 4
        assert set(ARTIFACT_TYPES.keys()) == {
            "quarto-dashboard",
            "marimo-notebook",
            "shiny-app",
            "jupyter-notebook",
        }


class TestRunInstructions:
    def test_all_builtin_types_have_run_instructions_with_placeholder(self):
        for at in ARTIFACT_TYPES.values():
            assert at.run_instructions
            assert "{filename}" in at.run_instructions

    def test_marimo_run_command(self):
        assert ARTIFACT_TYPES["marimo-notebook"].run_instructions == (
            "marimo edit {filename}"
        )


class TestLanguages:
    def test_registry_is_r_and_python(self):
        assert LANGUAGES == {"r": "R", "python": "Python"}


class TestResolveForLanguage:
    def _shiny(self) -> ArtifactType:
        return ArtifactType(
            id="shiny-app",
            label="Shiny",
            file_extension=".py",
            description="x",
            editor_language="python",
            run_instructions="shiny run --reload {filename}",
            supported_languages=("python", "r"),
            language_variants={
                "r": LanguageVariant(
                    file_extension=".R",
                    editor_language="r",
                    run_instructions='R -e "shiny::runApp(\'{filename}\')"',
                )
            },
        )

    def test_empty_language_returns_same_object(self):
        t = self._shiny()
        assert resolve_for_language(t, "") is t
        assert resolve_for_language(t, None) is t

    def test_unsupported_language_returns_same_object(self):
        t = ArtifactType(
            id="marimo-notebook",
            label="Marimo",
            file_extension=".py",
            description="x",
            editor_language="python",
            supported_languages=("python",),
        )
        assert resolve_for_language(t, "r") is t

    def test_supported_language_without_variant_returns_same_object(self):
        t = ArtifactType(
            id="quarto-dashboard",
            label="Quarto",
            file_extension=".qmd",
            description="x",
            editor_language="markdown",
            supported_languages=("python", "r"),
        )
        assert resolve_for_language(t, "r") is t

    def test_applies_variant_overrides(self):
        resolved = resolve_for_language(self._shiny(), "r")
        assert resolved.file_extension == ".R"
        assert resolved.editor_language == "r"
        assert resolved.run_instructions == 'R -e "shiny::runApp(\'{filename}\')"'

    def test_python_keeps_defaults(self):
        t = self._shiny()
        resolved = resolve_for_language(t, "python")
        assert resolved is t  # no variant registered for "python"
        assert resolved.file_extension == ".py"
        assert resolved.editor_language == "python"
        assert resolved.run_instructions == "shiny run --reload {filename}"

    def test_applies_generation_notes_override(self):
        t = ArtifactType(
            id="shiny-app",
            label="Shiny",
            file_extension=".py",
            description="x",
            editor_language="python",
            generation_notes="Use Shiny for Python Express syntax.",
            supported_languages=("python", "r"),
            language_variants={
                "r": LanguageVariant(
                    generation_notes="Use Shiny for R.",
                )
            },
        )
        resolved = resolve_for_language(t, "r")
        assert resolved.generation_notes == "Use Shiny for R."


class TestPerFormatLanguages:
    def test_marimo_is_python_only(self):
        assert ARTIFACT_TYPES["marimo-notebook"].supported_languages == ("python",)

    def test_multilingual_formats_support_both(self):
        for type_id in ("quarto-dashboard", "shiny-app", "jupyter-notebook"):
            assert set(ARTIFACT_TYPES[type_id].supported_languages) == {
                "python",
                "r",
            }

    def test_shiny_has_r_variant(self):
        shiny = ARTIFACT_TYPES["shiny-app"]
        resolved = resolve_for_language(shiny, "r")
        assert resolved.file_extension == ".R"
        assert resolved.editor_language == "r"
        assert "runApp" in resolved.run_instructions
        assert "{filename}" in resolved.run_instructions

    def test_only_shiny_defines_variants(self):
        for type_id, at in ARTIFACT_TYPES.items():
            if type_id == "shiny-app":
                assert at.language_variants
            else:
                assert at.language_variants == {}

    def test_shiny_r_variant_overrides_generation_notes(self):
        resolved = resolve_for_language(ARTIFACT_TYPES["shiny-app"], "r")
        assert "Python" not in resolved.generation_notes
        assert resolved.generation_notes  # non-empty
