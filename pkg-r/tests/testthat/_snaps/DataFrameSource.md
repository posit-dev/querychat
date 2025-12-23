# DataFrameSource$new() / errors with non-data.frame input

    Code
      DataFrameSource$new(list(a = 1, b = 2), "test_table")
    Condition
      Error in `initialize()`:
      ! `df` must be a data frame, not a list.

---

    Code
      DataFrameSource$new(c(1, 2, 3), "test_table")
    Condition
      Error in `initialize()`:
      ! `df` must be a data frame, not a double vector.

---

    Code
      DataFrameSource$new(NULL, "test_table")
    Condition
      Error in `initialize()`:
      ! `df` must be a data frame, not `NULL`.

# DataFrameSource$new() / errors with invalid table names

    Code
      DataFrameSource$new(test_df, "123_invalid")
    Condition
      Error in `initialize()`:
      ! `table_name` must be a valid SQL table name
      i Table names must begin with a letter and contain only letters, numbers, and underscores
      x You provided: "123_invalid"
    Code
      DataFrameSource$new(test_df, "table-name")
    Condition
      Error in `initialize()`:
      ! `table_name` must be a valid SQL table name
      i Table names must begin with a letter and contain only letters, numbers, and underscores
      x You provided: "table-name"
    Code
      DataFrameSource$new(test_df, "table name")
    Condition
      Error in `initialize()`:
      ! `table_name` must be a valid SQL table name
      i Table names must begin with a letter and contain only letters, numbers, and underscores
      x You provided: "table name"
    Code
      DataFrameSource$new(test_df, "")
    Condition
      Error in `initialize()`:
      ! `table_name` must be a valid SQL table name
      i Table names must begin with a letter and contain only letters, numbers, and underscores
      x You provided: ""
    Code
      DataFrameSource$new(test_df, NULL)
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single string, not `NULL`.

# DataFrameSource engine parameter / engine parameter validation / errors on invalid engine name

    Code
      DataFrameSource$new(new_test_df(), "test_table", engine = "postgres")
    Condition
      Error in `initialize()`:
      ! `engine` must be one of "duckdb" or "sqlite", not "postgres".

---

    Code
      DataFrameSource$new(new_test_df(), "test_table", engine = "invalid")
    Condition
      Error in `initialize()`:
      ! `engine` must be one of "duckdb" or "sqlite", not "invalid".

---

    Code
      DataFrameSource$new(new_test_df(), "test_table", engine = "")
    Condition
      Error in `initialize()`:
      ! `engine` must be one of "duckdb" or "sqlite", not "".

