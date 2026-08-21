# HandoffStore$replace() / leaves the old states and order intact when validation fails

    Code
      store$replace(list(new_store_handoff_state("new"), "invalid"))
    Condition
      Error in `check_handoff_store_state()`:
      ! `state` must be a <HandoffState>.

# HandoffStore$new() / rejects invalid item limits

    Code
      HandoffStore$new(max_items = 0L)
    Condition
      Error in `initialize()`:
      ! `max_items` must be a positive whole number.

# HandoffBundleStore$stage() / rejects one bundle larger than the byte budget

    Code
      store$stage(list(large.csv = charToRaw("abc")))
    Condition
      Error in `store$stage()`:
      ! Handoff data snapshot exceeds the session storage limit.

# HandoffBundleStore$stage() / rejects empty bundles without changing store state

    Code
      store$stage(list())
    Condition
      Error in `copy_handoff_bundle_files()`:
      ! Handoff data snapshot must contain at least one file.

---

    Code
      store$put(list())
    Condition
      Error in `copy_handoff_bundle_files()`:
      ! Handoff data snapshot must contain at least one file.

---

    Code
      store$stage(list())
    Condition
      Error in `copy_handoff_bundle_files()`:
      ! Handoff data snapshot must contain at least one file.

# HandoffBundleStore$new() / rejects invalid byte limits

    Code
      HandoffBundleStore$new(max_bytes = 0)
    Condition
      Error in `initialize()`:
      ! `max_bytes` must be a positive number.

