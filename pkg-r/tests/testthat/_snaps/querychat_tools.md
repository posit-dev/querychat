# tool_update_dashboard() checks update_fn inputs

    Code
      tool_update_dashboard(executor, "test_table", update_fn = NULL)
    Condition
      Error in `tool_update_dashboard()`:
      ! `update_fn` must be a function, not `NULL`.
    Code
      tool_update_dashboard(executor, "test_table", update_fn = function(query) { })
    Condition
      Error in `tool_update_dashboard()`:
      ! `update_fn` must accept at least three named arguments: "query", "title", and "table".
      x "title" and "table" arguments were missing.
    Code
      tool_update_dashboard(executor, "test_table", update_fn = function(title, extra)
        { })
    Condition
      Error in `tool_update_dashboard()`:
      ! `update_fn` must accept at least three named arguments: "query", "title", and "table".
      x "query" and "table" arguments were missing.

# tool_reset_dashboard() checks inputs

    Code
      tool_reset_dashboard("not_a_function", table_names = "t")
    Condition
      Error in `tool_reset_dashboard()`:
      ! `reset_fn` must be a function, not the string "not_a_function".

