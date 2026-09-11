# prepare_handoff_data() / rejects unsupported languages

    Code
      prepare_handoff_data(list(orders = new_fake_handoff_data_source()), language = "javascript")
    Condition
      Error in `check_handoff_data_language()`:
      ! `language` must be one of "python" or "r".

# materialize_handoff_data() / rejects unknown referenced tables before exporting

    Code
      materialize_handoff_data(catalog, sources, "missing")
    Condition
      Error in `validate_handoff_referenced_tables()`:
      ! Handoff referenced unknown tables: "missing"

# materialize_handoff_data() / wraps export failures in a stable handoff-specific message

    Code
      materialize_handoff_data(catalog, sources, "tips")
    Condition
      Error in `export_handoff_data_csv()`:
      ! Handoff data could not export dataframe table "tips" as CSV.
      Caused by error:
      ! cannot export

