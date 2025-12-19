# tool_update_dashboard() checks inputs

    Code
      tool_update_dashboard("foo")
    Condition
      Error in `tool_update_dashboard()`:
      ! `data_source` must be a <DataSource> object, not a string.

---

    Code
      tool_update_dashboard(df_source, update_fn = NULL)
    Condition
      Error in `tool_update_dashboard()`:
      ! `update_fn` must be a function, not `NULL`.
    Code
      tool_update_dashboard(df_source, update_fn = function(query) { })
    Condition
      Error in `tool_update_dashboard()`:
      ! `update_fn` must accept at least two named arguments: "query" and "title".
      x "title" argument was missing.
    Code
      tool_update_dashboard(df_source, update_fn = function(title, extra) { })
    Condition
      Error in `tool_update_dashboard()`:
      ! `update_fn` must accept at least two named arguments: "query" and "title".
      x "query" argument was missing.

# tool_reset_dashboard() checks inputs

    Code
      tool_reset_dashboard("not_a_function")
    Condition
      Error in `tool_reset_dashboard()`:
      ! `reset_fn` must be a function, not the string "not_a_function".

# tool_query() checks inputs

    Code
      tool_query("invalid_source")
    Condition
      Error in `tool_query()`:
      ! `data_source` must be a <DataSource> object, not a string.

