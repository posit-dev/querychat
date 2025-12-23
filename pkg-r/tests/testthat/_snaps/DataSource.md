# DataSource base class / throws not_implemented_error for all abstract methods

    Code
      base_source$get_db_type()
    Condition
      Error in `base_source$get_db_type()`:
      ! `get_db_type()` must be implemented by subclass

---

    Code
      base_source$get_schema()
    Condition
      Error in `base_source$get_schema()`:
      ! `get_schema()` must be implemented by subclass

---

    Code
      base_source$execute_query("SELECT * FROM test")
    Condition
      Error in `base_source$execute_query()`:
      ! `execute_query()` must be implemented by subclass

---

    Code
      base_source$test_query("SELECT * FROM test LIMIT 1")
    Condition
      Error in `base_source$test_query()`:
      ! `test_query()` must be implemented by subclass

---

    Code
      base_source$get_data()
    Condition
      Error in `base_source$get_data()`:
      ! `get_data()` must be implemented by subclass

---

    Code
      base_source$cleanup()
    Condition
      Error in `base_source$cleanup()`:
      ! `cleanup()` must be implemented by subclass

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

# DBISource$new() / errors with non-DBI connection

    Code
      DBISource$new(list(fake = "connection"), "test_table")
    Condition
      Error in `initialize()`:
      ! `conn` must be a <DBIConnection>, not a list

---

    Code
      DBISource$new(NULL, "test_table")
    Condition
      Error in `initialize()`:
      ! `conn` must be a <DBIConnection>, not NULL

---

    Code
      DBISource$new("not a connection", "test_table")
    Condition
      Error in `initialize()`:
      ! `conn` must be a <DBIConnection>, not a string

# DBISource$new() / errors with invalid table_name types

    Code
      DBISource$new(db$conn, 123)
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single character string or a `DBI::Id()` object

---

    Code
      DBISource$new(db$conn, c("table1", "table2"))
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single character string or a `DBI::Id()` object

---

    Code
      DBISource$new(db$conn, list(name = "table"))
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single character string or a `DBI::Id()` object

# DBISource$new() / errors when table does not exist

    Code
      DBISource$new(db$conn, "non_existent_table")
    Condition
      Error in `initialize()`:
      ! Table "`non_existent_table`" not found in database
      i If you're using a table in a catalog or schema, pass a `DBI::Id()` object to `table_name`

# test_query() column validation / provides helpful error message listing missing columns

    Code
      source$test_query("SELECT id FROM test_table", require_all_columns = TRUE)
    Condition
      Error in `source$test_query()`:
      ! Query result missing required columns: 'name', 'value'
      i The query must return all original table columns (in any order).

---

    Code
      source$test_query("SELECT id, name FROM test_table", require_all_columns = TRUE)
    Condition
      Error in `source$test_query()`:
      ! Query result missing required columns: 'value'
      i The query must return all original table columns (in any order).

