# validate_handoff_source() / rejects non-scalar, non-character, and blank source consistently

    Code
      validate_handoff_source(" \n\t", type)
    Condition
      Error in `validate_handoff_source()`:
      ! Generated handoff source must be a non-empty string.

# validate_handoff_source() / requires a resolved handoff type

    Code
      validate_handoff_source("source", "not a handoff type")
    Condition
      Error in `validate_handoff_source()`:
      ! `handoff_type` must be a <HandoffType> object.

