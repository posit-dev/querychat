# tool_card() checks inputs

    Code
      tool_card("invalid_source")
    Condition
      Error in `tool_card()`:
      ! `executor` must be a <QueryExecutor> object, not a string.

---

    Code
      tool_card(executor, manage_card = NULL)
    Condition
      Error in `tool_card()`:
      ! `manage_card` must be a function, not `NULL`.

