# handoff_recommendation_type() / rejects empty runtime enums clearly

    Code
      handoff_recommendation_type(character(), "quarto-dashboard")
    Condition
      Error in `check_runtime_enum_input()`:
      ! `item_ids` must not be empty.

---

    Code
      handoff_recommendation_type("query-0", character())
    Condition
      Error in `check_runtime_enum_input()`:
      ! `format_ids` must not be empty.

# handoff_result_type() / rejects empty runtime enums clearly

    Code
      handoff_result_type(character(), "python")
    Condition
      Error in `check_runtime_enum_input()`:
      ! `table_names` must not be empty.

---

    Code
      handoff_result_type("sales", character())
    Condition
      Error in `check_runtime_enum_input()`:
      ! `languages` must not be empty.

