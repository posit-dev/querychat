import chatlas
from querychat._handoff_state import HandoffState
from querychat._handoff_types import resolve_handoff_type


def test_current_handoff_defaults():
    state = HandoffState(
        handoff_id="a",
        handoff_type=resolve_handoff_type("quarto-dashboard", "python"),
        system_prompt="sys",
        source="v1",
    )

    assert state.turns == []
    assert state.summary == ""
    assert state.bundle_id is None
    assert state.bundled_tables == []


def test_snapshot_keeps_one_current_handoff_with_cumulative_turns():
    handoff_type = resolve_handoff_type("shiny-app", "r")
    turns = [
        chatlas.Turn(role="user", contents="Create the app"),
        chatlas.Turn(role="assistant", contents="First source"),
        chatlas.Turn(role="user", contents="Make it compact"),
        chatlas.Turn(role="assistant", contents="Revised source"),
    ]
    state = HandoffState(
        handoff_id="a1",
        handoff_type=handoff_type,
        system_prompt="sys",
        source="revised source",
        turns=turns,
        summary="latest",
        install_instructions="pak::pak('shiny')",
        run_instructions="shiny run handoff.py",
        referenced_tables=["mtcars"],
        bundled_tables=["mtcars"],
        bundle_id="bundle-latest",
        data_instructions="Load mtcars.csv",
    )

    data = state.model_dump(mode="json")
    restored = HandoffState.model_validate(data)

    assert "bundled_files" not in data
    assert restored.handoff_id == "a1"
    assert restored.source == "revised source"
    assert restored.turns == turns
    assert restored.handoff_type == handoff_type
    assert restored.summary == "latest"
    assert restored.install_instructions == "pak::pak('shiny')"
    assert restored.run_instructions == "shiny run handoff.py"
    assert restored.referenced_tables == ["mtcars"]
    assert restored.bundled_tables == ["mtcars"]
    assert restored.bundle_id == "bundle-latest"
    assert restored.data_instructions == "Load mtcars.csv"
