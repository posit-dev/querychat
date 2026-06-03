import chatlas
from querychat._artifact_state import ArtifactState, ArtifactVersion
from querychat._artifact_types import ARTIFACT_TYPES


def make_state() -> ArtifactState:
    return ArtifactState(
        artifact_id="a",
        artifact_type=ARTIFACT_TYPES["quarto-dashboard"],
        system_prompt="sys",
        versions=[ArtifactVersion(source="v1", turns=[], kind="generated")],
    )


class TestVersionTimeline:
    def test_initial_state(self):
        s = make_state()
        assert s.total == 1
        assert s.current_index == 0
        assert s.source == "v1"
        assert s.turns == []
        assert s.current_version.kind == "generated"

    def test_push_appends_and_advances(self):
        s = make_state()
        s.push_version(ArtifactVersion(source="v2", turns=[], kind="revised"))
        assert s.total == 2
        assert s.current_index == 1
        assert s.source == "v2"
        assert s.current_version.kind == "revised"

    def test_push_truncates_forward_history(self):
        s = make_state()
        s.push_version(ArtifactVersion(source="v2", turns=[], kind="revised"))
        s.push_version(ArtifactVersion(source="v3", turns=[], kind="revised"))
        s.step(-1)  # back to v2 (index 1)
        assert s.source == "v2"
        s.push_version(ArtifactVersion(source="v2b", turns=[], kind="revised"))
        assert s.total == 3  # v1, v2, v2b — v3 discarded
        assert s.current_index == 2
        assert s.source == "v2b"

    def test_step_clamps_at_bounds(self):
        s = make_state()
        s.step(-1)
        assert s.current_index == 0
        s.push_version(ArtifactVersion(source="v2", turns=[], kind="revised"))
        s.step(1)
        assert s.current_index == 1


class TestPerVersionMetadata:
    def test_state_metadata_delegates_to_current_version(self):
        state = ArtifactState(
            artifact_id="a",
            artifact_type=ARTIFACT_TYPES["quarto-dashboard"],
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

    def test_push_version_carries_metadata_and_switches(self):
        state = ArtifactState(
            artifact_id="a",
            artifact_type=ARTIFACT_TYPES["quarto-dashboard"],
            system_prompt="sys",
            versions=[
                ArtifactVersion(source="v1", turns=[], kind="generated", summary="first")
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


class TestSerializeRoundtrip:
    def test_roundtrip_preserves_versions_and_turns(self):
        state = ArtifactState(
            artifact_id="a1",
            # shiny-app carries language_variants + a tuple field, exercising
            # full ArtifactType reconstruction.
            artifact_type=ARTIFACT_TYPES["shiny-app"],
            system_prompt="sys",
            versions=[
                ArtifactVersion(
                    source="v1",
                    turns=[chatlas.Turn(role="user", contents="make app")],
                    kind="generated",
                    summary="first",
                    install_instructions="pip install shiny",
                ),
                ArtifactVersion(
                    source="v2", turns=[], kind="revised", summary="second"
                ),
            ],
            current_index=1,
            bundled_files={"mtcars.csv": b"original"},
            data_instructions="orig",
        )

        data = state.model_dump(mode="json")
        # Excluded fields must not be persisted in the bookmark.
        assert "bundled_files" not in data
        assert "data_instructions" not in data

        # Bundled data is regenerable from the data source, so it is supplied at
        # restore time rather than carried through the bookmark.
        restored = ArtifactState.model_validate(data)
        restored.bundled_files = {"mtcars.csv": b"regenerated"}
        restored.data_instructions = "new"

        assert restored.artifact_id == "a1"
        assert restored.artifact_type == ARTIFACT_TYPES["shiny-app"]
        assert restored.system_prompt == "sys"
        assert restored.current_index == 1
        assert restored.total == 2
        assert restored.versions[0].source == "v1"
        assert restored.versions[0].kind == "generated"
        assert restored.versions[0].summary == "first"
        assert restored.versions[0].install_instructions == "pip install shiny"
        assert restored.versions[0].turns[0].contents[0].text == "make app"
        assert restored.versions[1].kind == "revised"
        assert restored.bundled_files == {"mtcars.csv": b"regenerated"}
        assert restored.data_instructions == "new"


class TestLegacyBookmarkCompat:
    def test_old_shape_dict_restores(self):
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
                "language_variants": {
                    "r": {
                        "file_extension": ".R",
                        "editor_language": "r",
                        "run_instructions": None,
                        "generation_notes": None,
                    }
                },
            },
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

        assert restored.artifact_id == "a1"
        assert restored.artifact_type.supported_languages == ("python", "r")
        assert restored.artifact_type.language_variants["r"].file_extension == ".R"
        assert restored.source == "v1"
        assert restored.total == 1

