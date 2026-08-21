# HandoffOrchestrator$prepare_generation() / rejects blank Other names before asking the model

    Code
      sync_promise(fixture$orchestrator$prepare_generation(request, ""))
    Condition
      Error:
      ! Enter a format name for "Other" before generating a handoff.

# HandoffOrchestrator$prepare_generation() / rejects missing languages and incompatible targets

    Code
      sync_promise(fixture$orchestrator$prepare_generation(HandoffGenerateRequest(
        type_id = "quarto-dashboard"), ""))
    Condition
      Error:
      ! Select R or Python before generating a handoff.

---

    Code
      sync_promise(fixture$orchestrator$prepare_generation(HandoffGenerateRequest(
        type_id = "marimo-notebook", language = "r"), ""))
    Condition
      Error in `resolve_handoff_target()`:
      ! Handoff format "Marimo" does not support R.

# HandoffOrchestrator$prepare_generation() / rejects unknown built-in format IDs

    Code
      sync_promise(fixture$orchestrator$prepare_generation(HandoffGenerateRequest(
        type_id = "unknown-format", language = "python"), ""))
    Condition
      Error:
      ! Unknown handoff format: unknown-format

# HandoffOrchestrator$restore_snapshot() / leaves state and bundles intact when validation fails

    Code
      fixture$orchestrator$restore_snapshot(list(list(version = 99L)))
    Condition
      Error in `check_exact_fields()`:
      ! Handoff state record is missing required field: "handoff_id", "handoff_type", "system_prompt", "source", "turns", "summary", "install_instructions", "run_instructions", "referenced_tables", "bundled_tables", "bundle_id", and "data_instructions".

# HandoffOrchestrator$generate() / rejects a repaired language change and rolls back

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error:
      ! Repaired handoff changed its language.

# HandoffOrchestrator$generate() / rolls back stream and cancellation failures

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error:
      ! stream failed

---

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error:
      ! generation cancelled

# HandoffOrchestrator$generate() / rolls back a second validation failure

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error in `validate_handoff_source()`:
      ! Generated handoff source must be a non-empty string.

# HandoffOrchestrator$generate() / rolls back completed-view and pill failures before remember

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error in `record()`:
      ! show_handoff failed

---

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error in `record()`:
      ! append_pill failed

# HandoffOrchestrator$generate() / aborts when the correction changes the handoff language

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error:
      ! Corrected handoff changed its language.

# HandoffOrchestrator$generate() / aborts when the correction changes the referenced-table set

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error:
      ! Corrected handoff changed its referenced-table set.

# HandoffOrchestrator$generate() / propagates an unrelated correction stream error unchanged

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error:
      ! model returned malformed JSON

# HandoffOrchestrator$generate() / fails when the corrected source is invalid

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error in `validate_handoff_source()`:
      ! Generated handoff source must be a non-empty string.

# HandoffOrchestrator$generate() / rolls back when the correction is cancelled

    Code
      sync_promise(fixture$orchestrator$generate(transaction_request(), "",
      "handoff-1"))
    Condition
      Error:
      ! correction cancelled

# HandoffOrchestrator$revise() / rejects a revised language change and restores the old handoff

    Code
      sync_promise(fixture$orchestrator$revise("handoff-1", "Rewrite it."))
    Condition
      Error:
      ! Revised handoff changed its language.

# HandoffOrchestrator$revise() / restores state, source, and download after transaction failures

    Code
      sync_promise(fixture$orchestrator$revise("handoff-1", "Revise it."))
    Condition
      Error:
      ! revision stream failed

---

    Code
      sync_promise(fixture$orchestrator$revise("handoff-1", "Revise it."))
    Condition
      Error in `validate_handoff_source()`:
      ! Generated handoff source must be a non-empty string.

---

    Code
      sync_promise(fixture$orchestrator$revise("handoff-1", "Revise it."))
    Condition
      Error:
      ! revision cancelled

---

    Code
      sync_promise(fixture$orchestrator$revise("handoff-1", "Revise it."))
    Condition
      Error in `record()`:
      ! show_handoff failed

# HandoffOrchestrator$revise() / rethrows the original condition when restoring the view fails

    Code
      stop(caught)
    Condition
      Error:
      ! original revision failure

# HandoffOrchestrator$revise() / preserves the current handoff when correction fails during revision

    Code
      sync_promise(fixture$orchestrator$revise("handoff-1", "Make it smaller."))
    Condition
      Error:
      ! Corrected handoff changed its referenced-table set.

# HandoffOrchestrator$build_download() / reports the snapshot as unavailable when bundled tables have no bundle ID

    Code
      fixture$orchestrator$build_download("handoff-1")
    Condition
      Error in `abort_handoff_snapshot_unavailable()`:
      ! This handoff data snapshot is unavailable.

# HandoffOrchestrator$build_download() / reports the snapshot as unavailable when the bundle ID is missing from the store

    Code
      fixture$orchestrator$build_download("handoff-1")
    Condition
      Error in `abort_handoff_snapshot_unavailable()`:
      ! This handoff data snapshot is unavailable.

