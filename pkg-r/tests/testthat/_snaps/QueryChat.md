# QueryChat$new() / errors with invalid argument types

    Code
      QueryChat$new(test_df, table_name = "test", id = 123)
    Condition
      Error in `initialize()`:
      ! `id` must be a single string or `NULL`, not the number 123.

---

    Code
      QueryChat$new(test_df, table_name = "test", greeting = 123)
    Condition
      Error in `initialize()`:
      ! `greeting` must be a single string or `NULL`, not the number 123.

---

    Code
      QueryChat$new(test_df, table_name = "test", categorical_threshold = "not_a_number")
    Condition
      Error in `initialize()`:
      ! `categorical_threshold` must be a whole number, not the string "not_a_number".

---

    Code
      QueryChat$new(test_df, table_name = "test", cleanup = "not_logical")
    Condition
      Error in `initialize()`:
      ! `cleanup` must be `TRUE`, `FALSE`, or `NA`, not the string "not_logical".

# QueryChat$server() errors when called outside Shiny context

    Code
      qc$server()
    Condition
      Error in `qc$server()`:
      ! `$server()` must be called within a Shiny server function

# QueryChat$server() resolves history (explicit > constructor > TRUE) and warns on enable_bookmarking

    Code
      shiny::testServer(function(input, output, session) qc_no_history$server(
        enable_bookmarking = TRUE), { })
    Message
      Using model = "gpt-4.1".
    Condition
      Warning:
      The `enable_bookmarking` argument of `QueryChat$server()` is deprecated as of querychat 0.4.0.
      i Please use the `history` argument instead.
      i Use history = shinychat::history_options(restore_mode = "bookmark") for the equivalent behavior.

# normalize_data_source() / errors with invalid data source types

    Code
      normalize_data_source("not_a_data_source", "table_name")
    Condition
      Error in `normalize_data_source()`:
      ! `data_source` must be a <DataSource>, <data.frame>, or <DBIConnection>, not a string.

---

    Code
      normalize_data_source(list(a = 1, b = 2), "table_name")
    Condition
      Error in `normalize_data_source()`:
      ! `data_source` must be a <DataSource>, <data.frame>, or <DBIConnection>, not a list.

---

    Code
      normalize_data_source(NULL, "table_name")
    Condition
      Error in `normalize_data_source()`:
      ! `data_source` must be a <DataSource>, <data.frame>, or <DBIConnection>, not NULL.

