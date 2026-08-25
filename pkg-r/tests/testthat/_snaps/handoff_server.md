# apply_handoff_snapshot() / rejects malformed and unsupported envelopes without partial restore

    Code
      apply_handoff_snapshot(fixture$orchestrator, "{not json", active_handoff_id)
    Condition
      Error:
      ! lexical error: invalid string in json text.
                                            {not json
                           (right here) ------^

---

    Code
      apply_handoff_snapshot(fixture$orchestrator, malformed_states,
      active_handoff_id)
    Condition
      Error in `check_plain_list()`:
      ! Handoff snapshot `states` must be an unnamed plain list.

---

    Code
      apply_handoff_snapshot(fixture$orchestrator, unsupported, active_handoff_id)
    Condition
      Error in `apply_handoff_snapshot()`:
      ! Handoff snapshot version must be exactly 1.

---

    Code
      apply_handoff_snapshot(fixture$orchestrator, extra_field, active_handoff_id)
    Condition
      Error in `check_exact_fields()`:
      ! Handoff snapshot has unexpected field: "bundles".

# handoff_server() / notifies and unlocks manual selection after recommendation failure

    Code
      flush_handoff_server(session)
    Condition
      Warning in `recommendation_task$invoke()`:
      ERROR: An error occurred when invoking the ExtendedTask.
      Caused by error:
      ! recommend failed

# handoff_server() / opens a new panel before generation and closes failed work

    Code
      flush_handoff_server(session)
    Condition
      Warning in `handoff_task$invoke()`:
      ERROR: An error occurred when invoking the ExtendedTask.
      Caused by error:
      ! generation failed

# handoff_server() / rejects a second generation while the first is running

    Code
      flush_handoff_server(session)
    Condition
      Warning in `handoff_task$invoke()`:
      ERROR: An error occurred when invoking the ExtendedTask.
      Caused by error:
      ! first generation failed

