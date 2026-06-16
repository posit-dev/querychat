# tool_card() checks inputs

    Code
      tool_card("invalid_source")
    Condition
      Error in `tool_card()`:
      ! `data_source` must be a <DataSource> object, not a string.

---

    Code
      tool_card(df_source, manage_card = NULL)
    Condition
      Error in `tool_card()`:
      ! `manage_card` must be a function, not `NULL`.

