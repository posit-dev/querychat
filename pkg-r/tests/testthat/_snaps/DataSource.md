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

