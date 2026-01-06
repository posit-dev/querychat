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

