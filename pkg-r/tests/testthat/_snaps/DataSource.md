# DataSource base class / throws not_implemented_error for all abstract methods

    Code
      base_source$get_db_type()
    Condition
      Error in `base_source$get_db_type()`:
      ! get_db_type() must be implemented by subclass

---

    Code
      base_source$get_schema()
    Condition
      Error in `base_source$get_schema()`:
      ! get_schema() must be implemented by subclass

---

    Code
      base_source$execute_query("SELECT * FROM test")
    Condition
      Error in `base_source$execute_query()`:
      ! execute_query() must be implemented by subclass

---

    Code
      base_source$test_query("SELECT * FROM test LIMIT 1")
    Condition
      Error in `base_source$test_query()`:
      ! test_query() must be implemented by subclass

---

    Code
      base_source$get_data()
    Condition
      Error in `base_source$get_data()`:
      ! get_data() must be implemented by subclass

---

    Code
      base_source$cleanup()
    Condition
      Error in `base_source$cleanup()`:
      ! cleanup() must be implemented by subclass

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
      ! `table_name` must be a valid SQL table name.
    Code
      DataFrameSource$new(test_df, "table-name")
    Condition
      Error in `initialize()`:
      ! `table_name` must be a valid SQL table name.
    Code
      DataFrameSource$new(test_df, "table name")
    Condition
      Error in `initialize()`:
      ! `table_name` must be a valid SQL table name.
    Code
      DataFrameSource$new(test_df, "")
    Condition
      Error in `initialize()`:
      ! `table_name` must be a valid SQL table name.
    Code
      DataFrameSource$new(test_df, NULL)
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single string, not `NULL`.

# DBISource$new() / errors with non-DBI connection

    Code
      DBISource$new(list(fake = "connection"), "test_table")
    Condition
      Error in `initialize()`:
      ! `conn` must be a DBI connection

---

    Code
      DBISource$new(NULL, "test_table")
    Condition
      Error in `initialize()`:
      ! `conn` must be a DBI connection

---

    Code
      DBISource$new("not a connection", "test_table")
    Condition
      Error in `initialize()`:
      ! `conn` must be a DBI connection

# DBISource$new() / errors with invalid table_name types

    Code
      DBISource$new(db$conn, 123)
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single character string or a DBI::Id object

---

    Code
      DBISource$new(db$conn, c("table1", "table2"))
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single character string or a DBI::Id object

---

    Code
      DBISource$new(db$conn, list(name = "table"))
    Condition
      Error in `initialize()`:
      ! `table_name` must be a single character string or a DBI::Id object

# DBISource$new() / errors when table does not exist

    Code
      DBISource$new(db$conn, "non_existent_table")
    Condition
      Error:
      ! ! Could not evaluate cli `{}` expression: `DBI::dbQuoteIdent...`.
      Caused by error in `h(simpleError(msg, call))`:
      ! error in evaluating the argument 'conn' in selecting a method for function 'dbQuoteIdentifier': object 'x' not found

# assemble_system_prompt() / errors with non-DataSource input

    Code
      assemble_system_prompt(list(not = "a data source"), data_description = "Test")
    Condition
      Error in `assemble_system_prompt()`:
      ! `source` must be a DataSource object

---

    Code
      assemble_system_prompt(data.frame(x = 1:3), data_description = "Test")
    Condition
      Error in `assemble_system_prompt()`:
      ! `source` must be a DataSource object

