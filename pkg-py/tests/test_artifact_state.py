import copy

import chatlas
from querychat._artifact_state import ArtifactState, ArtifactVersion
from querychat._artifact_types import resolve_artifact_type


def make_state() -> ArtifactState:
    return ArtifactState(
        artifact_id="a",
        artifact_type=resolve_artifact_type("quarto-dashboard", "python"),
        language="python",
        system_prompt="sys",
        versions=[ArtifactVersion(source="v1", turns=[], kind="generated")],
    )


class TestVersionTimeline:
    def test_initial_state(self):
        state = make_state()
        assert state.total == 1
        assert state.current_index == 0
        assert state.source == "v1"
        assert state.turns == []
        assert state.current_version.kind == "generated"

    def test_push_appends_and_advances(self):
        state = make_state()
        state.push_version(ArtifactVersion(source="v2", turns=[], kind="revised"))
        assert state.total == 2
        assert state.current_index == 1
        assert state.source == "v2"
        assert state.current_version.kind == "revised"

    def test_push_truncates_forward_history(self):
        state = make_state()
        state.push_version(ArtifactVersion(source="v2", turns=[], kind="revised"))
        state.push_version(ArtifactVersion(source="v3", turns=[], kind="revised"))
        state.step(-1)
        assert state.source == "v2"
        removed = state.push_version(
            ArtifactVersion(source="v2b", turns=[], kind="revised")
        )
        assert state.total == 3
        assert state.current_index == 2
        assert state.source == "v2b"
        assert [version.source for version in removed] == ["v3"]

    def test_step_clamps_at_bounds(self):
        state = make_state()
        state.step(-1)
        assert state.current_index == 0
        state.push_version(ArtifactVersion(source="v2", turns=[], kind="revised"))
        state.step(1)
        assert state.current_index == 1


class TestPerVersionMetadata:
    def test_state_metadata_delegates_to_current_version(self):
        state = ArtifactState(
            artifact_id="a",
            artifact_type=resolve_artifact_type("quarto-dashboard", "python"),
            language="python",
            system_prompt="sys",
            versions=[
                ArtifactVersion(
                    source="v1",
                    turns=[],
                    kind="generated",
                    summary="first",
                    install_instructions="pip install one",
                )
            ],
        )
        assert state.summary == "first"
        assert state.install_instructions == "pip install one"

    def test_exposes_current_version_run_instructions(self):
        state = make_state()
        state.current_version.run_instructions = (
            "```bash\nquarto preview artifact.qmd\n```"
        )
        assert "quarto preview" in state.run_instructions

    def test_push_version_carries_metadata_and_switches(self):
        state = ArtifactState(
            artifact_id="a",
            artifact_type=resolve_artifact_type("quarto-dashboard", "python"),
            language="python",
            system_prompt="sys",
            versions=[
                ArtifactVersion(
                    source="v1", turns=[], kind="generated", summary="first"
                )
            ],
        )
        state.push_version(
            ArtifactVersion(
                source="v2",
                turns=[],
                kind="revised",
                summary="second",
                install_instructions="pip install two",
            )
        )
        assert state.summary == "second"
        assert state.install_instructions == "pip install two"

        state.step(-1)
        assert state.summary == "first"
        assert state.install_instructions == ""

    def test_table_metadata_is_per_version(self):
        state = make_state()
        state.push_version(
            ArtifactVersion(
                source="v2",
                turns=[],
                kind="revised",
                referenced_tables=["orders", "customers"],
                bundled_tables=["orders"],
            )
        )

        assert state.current_version.referenced_tables == ["orders", "customers"]
        assert state.current_version.bundled_tables == ["orders"]


class TestSerializeRoundtrip:
    def test_roundtrip_preserves_target_snapshot_versions_and_turns(self):
        artifact_type = resolve_artifact_type("shiny-app", "r")
        state = ArtifactState(
            artifact_id="a1",
            artifact_type=artifact_type,
            language="r",
            system_prompt="sys",
            versions=[
                ArtifactVersion(
                    source="v1",
                    turns=[chatlas.Turn(role="user", contents="make app")],
                    kind="generated",
                    summary="first",
                    install_instructions="pak::pak('shiny')",
                    referenced_tables=["mtcars"],
                    bundled_tables=["mtcars"],
                    bundle_id="bundle-1",
                    data_instructions="Load mtcars.csv",
                ),
                ArtifactVersion(
                    source="v2", turns=[], kind="revised", summary="second"
                ),
            ],
            current_index=1,
        )

        data = state.model_dump(mode="json")
        assert "bundled_files" not in data
        assert data["versions"][0]["bundle_id"] == "bundle-1"
        assert data["versions"][0]["data_instructions"] == "Load mtcars.csv"

        restored = ArtifactState.model_validate(data)

        assert restored.artifact_id == "a1"
        assert restored.artifact_type == artifact_type
        assert restored.language == "r"
        assert restored.system_prompt == "sys"
        assert restored.current_index == 1
        assert restored.total == 2
        assert restored.versions[0].source == "v1"
        assert restored.versions[0].kind == "generated"
        assert restored.versions[0].summary == "first"
        assert restored.versions[0].install_instructions == "pak::pak('shiny')"
        assert restored.versions[0].turns[0].contents[0].text == "make app"
        assert restored.versions[0].referenced_tables == ["mtcars"]
        assert restored.versions[0].bundled_tables == ["mtcars"]
        assert restored.versions[0].bundle_id == "bundle-1"
        assert restored.versions[0].data_instructions == "Load mtcars.csv"
        assert restored.versions[1].kind == "revised"
        assert not hasattr(restored, "bundled_files")

    def test_legacy_bundled_version_has_no_snapshot_id(self):
        state = make_state()
        data = state.model_dump(mode="json")
        data["versions"][0]["bundled_tables"] = ["mtcars"]

        restored = ArtifactState.model_validate(data)

        assert restored.current_version.bundle_id is None
        assert restored.current_version.data_instructions == ""


class TestLegacyBookmarkCompat:
    def test_old_type_shape_restores_as_target_snapshot(self):
        data = {
            "artifact_id": "a1",
            "artifact_type": {
                "id": "shiny-app",
                "label": "Shiny",
                "file_extension": ".py",
                "description": "x",
                "editor_language": "python",
                "generation_notes": "",
                "run_instructions": "shiny run {filename}",
                "icon": "lightning-fill",
                "supported_languages": ["python", "r"],
                "language_variants": {},
            },
            "language": "python",
            "system_prompt": "sys",
            "current_index": 0,
            "versions": [
                {
                    "source": "v1",
                    "kind": "generated",
                    "summary": "first",
                    "install_instructions": "",
                    "turns": [],
                }
            ],
        }

        restored = ArtifactState.model_validate(data)

        assert restored.artifact_type.file_extension == ".py"
        assert restored.artifact_type.editor_language == "python"
        assert restored.artifact_type.label == "Shiny"
        assert restored.artifact_type.icon == "lightning-fill"
        assert restored.artifact_type.structure == "text"
        assert restored.artifact_type.language == "python"
        assert restored.source == "v1"

    def test_legacy_notebook_snapshot_infers_notebook_structure(self):
        data = {
            "artifact_id": "a1",
            "artifact_type": {
                "id": "jupyter-notebook",
                "label": "Jupyter",
                "file_extension": ".ipynb",
                "description": "x",
                "editor_language": "json",
                "icon": "file-earmark-code",
            },
            "language": "r",
            "system_prompt": "sys",
            "versions": [{"source": "{}", "kind": "generated", "turns": []}],
        }

        restored = ArtifactState.model_validate(data)

        assert restored.artifact_type.structure == "notebook-json"
        assert restored.artifact_type.language == "r"

    def test_legacy_static_run_command_migrates_to_versions(self):
        legacy_bookmark = {
            "artifact_id": "a1",
            "artifact_type": {
                "id": "shiny-app",
                "label": "Shiny",
                "file_extension": ".py",
                "description": "x",
                "editor_language": "python",
                "generation_notes": "",
                "run_instructions": "shiny run {filename}",
                "icon": "lightning-fill",
                "supported_languages": ["python"],
                "language_variants": {},
            },
            "language": "python",
            "system_prompt": "sys",
            "current_index": 0,
            "versions": [
                {"source": "v1", "kind": "generated", "turns": []},
                {
                    "source": "v2",
                    "kind": "revised",
                    "run_instructions": "shiny run --reload artifact.py",
                    "turns": [],
                },
            ],
        }
        original = copy.deepcopy(legacy_bookmark)

        restored = ArtifactState.model_validate(legacy_bookmark)

        assert restored.versions[0].run_instructions == "shiny run {filename}"
        assert restored.versions[1].run_instructions == "shiny run --reload artifact.py"
        assert legacy_bookmark == original
