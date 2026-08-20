import chatlas
from querychat._artifact_state import ArtifactState
from querychat._artifact_types import resolve_artifact_type


def test_current_artifact_defaults():
    state = ArtifactState(
        artifact_id="a",
        artifact_type=resolve_artifact_type("quarto-dashboard", "python"),
        system_prompt="sys",
        source="v1",
    )

    assert state.turns == []
    assert state.summary == ""
    assert state.bundle_id is None
    assert state.bundled_tables == []


def test_snapshot_keeps_one_current_artifact_with_cumulative_turns():
    artifact_type = resolve_artifact_type("shiny-app", "r")
    turns = [
        chatlas.Turn(role="user", contents="Create the app"),
        chatlas.Turn(role="assistant", contents="First source"),
        chatlas.Turn(role="user", contents="Make it compact"),
        chatlas.Turn(role="assistant", contents="Revised source"),
    ]
    state = ArtifactState(
        artifact_id="a1",
        artifact_type=artifact_type,
        system_prompt="sys",
        source="revised source",
        turns=turns,
        summary="latest",
        install_instructions="pak::pak('shiny')",
        run_instructions="shiny run artifact.py",
        referenced_tables=["mtcars"],
        bundled_tables=["mtcars"],
        bundle_id="bundle-latest",
        data_instructions="Load mtcars.csv",
    )

    data = state.model_dump(mode="json")
    restored = ArtifactState.model_validate(data)

    assert "bundled_files" not in data
    assert restored.artifact_id == "a1"
    assert restored.source == "revised source"
    assert restored.turns == turns
    assert restored.artifact_type == artifact_type
    assert restored.summary == "latest"
    assert restored.install_instructions == "pak::pak('shiny')"
    assert restored.run_instructions == "shiny run artifact.py"
    assert restored.referenced_tables == ["mtcars"]
    assert restored.bundled_tables == ["mtcars"]
    assert restored.bundle_id == "bundle-latest"
    assert restored.data_instructions == "Load mtcars.csv"
