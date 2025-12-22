describe("DataSource base class", {
  it("throws not_implemented_error for all abstract methods", {
    # Create a base DataSource object (shouldn't be done in practice)
    base_source <- DataSource$new()

    expect_snapshot(error = TRUE, {
      base_source$get_db_type()
    })

    expect_snapshot(error = TRUE, {
      base_source$get_schema()
    })

    expect_snapshot(error = TRUE, {
      base_source$execute_query("SELECT * FROM test")
    })

    expect_snapshot(error = TRUE, {
      base_source$test_query("SELECT * FROM test LIMIT 1")
    })

    expect_snapshot(error = TRUE, {
      base_source$get_data()
    })

    expect_snapshot(error = TRUE, {
      base_source$cleanup()
    })
  })
})

describe("DataFrameSource$new()", {
  skip_if_no_dataframe_engine()

  it("creates proper R6 object for DataFrameSource", {
    test_df <- new_test_df()

    source <- DataFrameSource$new(test_df, "test_table")
    withr::defer(source$cleanup())

    expect_s3_class(source, "DataFrameSource")
    expect_s3_class(source, "DataSource")
    expect_equal(source$table_name, "test_table")
  })

  it("errors with non-data.frame input", {
    expect_snapshot(
      error = TRUE,
      DataFrameSource$new(list(a = 1, b = 2), "test_table")
    )
    expect_snapshot(error = TRUE, DataFrameSource$new(c(1, 2, 3), "test_table"))
    expect_snapshot(error = TRUE, DataFrameSource$new(NULL, "test_table"))
  })

  it("errors with invalid table names", {
    test_df <- new_test_df()

    expect_snapshot(error = TRUE, {
      DataFrameSource$new(test_df, "123_invalid")
      DataFrameSource$new(test_df, "table-name")
      DataFrameSource$new(test_df, "table name")
      DataFrameSource$new(test_df, "")
      DataFrameSource$new(test_df, NULL)
    })
  })
})

describe("DataFrameSource engine parameter", {
  describe("with duckdb engine", {
    skip_if_not_installed("duckdb")

    it("creates connection with duckdb backend", {
      df_source <- local_data_frame_source(new_test_df(), engine = "duckdb")

      expect_s3_class(df_source, "DataFrameSource")
      expect_s3_class(df_source, "DBISource")
      expect_equal(df_source$table_name, "test_table")
      expect_equal(df_source$get_db_type(), "DuckDB")
    })

    it("executes queries correctly", {
      test_df <- new_test_df()
      df_source <- local_data_frame_source(test_df, engine = "duckdb")

      # Test filtering
      result <- df_source$execute_query(
        "SELECT * FROM test_table WHERE value > 25"
      )
      expect_equal(nrow(result), 3)
      expect_equal(result$value, c(30, 40, 50))

      # Test get_data
      all_data <- df_source$get_data()
      expect_equal(all_data, test_df)

      # Test test_query
      one_row <- df_source$test_query("SELECT * FROM test_table")
      expect_equal(nrow(one_row), 1)
    })

    it("returns correct schema", {
      df_source <- local_data_frame_source(
        new_mixed_types_df(),
        engine = "duckdb"
      )
      schema <- df_source$get_schema()

      expect_type(schema, "character")
      expect_match(schema, "Table: test_table")
      expect_match(schema, "id \\(INTEGER\\)")
      expect_match(schema, "name \\(TEXT\\)")
      expect_match(schema, "active \\(BOOLEAN\\)")
    })
  })

  describe("with sqlite engine", {
    skip_if_not_installed("RSQLite")

    it("creates connection with sqlite backend", {
      df_source <- local_data_frame_source(new_test_df(), engine = "sqlite")

      expect_s3_class(df_source, "DataFrameSource")
      expect_s3_class(df_source, "DBISource")
      expect_equal(df_source$table_name, "test_table")
      expect_equal(df_source$get_db_type(), "SQLite")
    })

    it("executes queries correctly", {
      test_df <- new_test_df()
      df_source <- local_data_frame_source(test_df, engine = "sqlite")

      # Test filtering
      result <- df_source$execute_query(
        "SELECT * FROM test_table WHERE value > 25"
      )
      expect_equal(nrow(result), 3)
      expect_equal(result$value, c(30, 40, 50))

      # Test get_data
      all_data <- df_source$get_data()
      expect_equal(all_data, test_df)

      # Test test_query
      one_row <- df_source$test_query("SELECT * FROM test_table")
      expect_equal(nrow(one_row), 1)
    })

    it("returns correct schema", {
      df_source <- local_data_frame_source(
        new_mixed_types_df(),
        engine = "sqlite"
      )
      schema <- df_source$get_schema()

      expect_type(schema, "character")
      expect_match(schema, "Table:")
      expect_match(schema, "test_table")
      expect_match(schema, "id \\(INTEGER\\)")
      expect_match(schema, "name \\(TEXT\\)")
      # SQLite stores booleans as INTEGER (0/1)
      expect_match(schema, "active \\(INTEGER\\)")
    })
  })

  describe("engine parameter validation", {
    it("is case-insensitive", {
      skip_if_not_installed("duckdb")
      skip_if_not_installed("RSQLite")

      # Test various case combinations
      df1 <- local_data_frame_source(new_test_df(), engine = "DUCKDB")
      expect_equal(df1$get_db_type(), "DuckDB")

      df2 <- local_data_frame_source(new_test_df(), engine = "DuckDb")
      expect_equal(df2$get_db_type(), "DuckDB")

      df3 <- local_data_frame_source(new_test_df(), engine = "SQLite")
      expect_equal(df3$get_db_type(), "SQLite")

      df4 <- local_data_frame_source(new_test_df(), engine = "SQLITE")
      expect_equal(df4$get_db_type(), "SQLite")
    })

    it("errors on invalid engine name", {
      expect_snapshot(error = TRUE, {
        DataFrameSource$new(new_test_df(), "test_table", engine = "postgres")
      })

      expect_snapshot(error = TRUE, {
        DataFrameSource$new(new_test_df(), "test_table", engine = "invalid")
      })

      expect_snapshot(error = TRUE, {
        DataFrameSource$new(new_test_df(), "test_table", engine = "")
      })
    })

    it("respects getOption('querychat.DataFrameSource.engine')", {
      skip_if_not_installed("duckdb")
      skip_if_not_installed("RSQLite")

      # Test default (duckdb)
      withr::local_options(querychat.DataFrameSource.engine = NULL)
      df1 <- DataFrameSource$new(new_test_df(), "test_table")
      withr::defer(df1$cleanup())
      expect_equal(df1$get_db_type(), "DuckDB")

      # Test option set to sqlite
      withr::local_options(querychat.DataFrameSource.engine = "sqlite")
      df2 <- DataFrameSource$new(new_test_df(), "test_table")
      withr::defer(df2$cleanup())
      expect_equal(df2$get_db_type(), "SQLite")

      # Test explicit parameter overrides option
      withr::local_options(querychat.DataFrameSource.engine = "sqlite")
      df3 <- local_data_frame_source(new_test_df(), engine = "duckdb")
      expect_equal(df3$get_db_type(), "DuckDB")
    })
  })
})

describe("DBISource$new()", {
  it("creates proper R6 object for DBISource", {
    db <- local_sqlite_connection(new_users_df(), "users")

    db_source <- DBISource$new(db$conn, "users")
    expect_s3_class(db_source, "DBISource")
    expect_s3_class(db_source, "DataSource")
    expect_equal(db_source$table_name, "users")
  })

  it("errors with non-DBI connection", {
    expect_snapshot(error = TRUE, {
      DBISource$new(list(fake = "connection"), "test_table")
    })

    expect_snapshot(error = TRUE, {
      DBISource$new(NULL, "test_table")
    })

    expect_snapshot(error = TRUE, {
      DBISource$new("not a connection", "test_table")
    })
  })

  it("errors with invalid table_name types", {
    db <- local_sqlite_connection(new_test_df())

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, 123)
    })

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, c("table1", "table2"))
    })

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, list(name = "table"))
    })
  })

  it("errors when table does not exist", {
    db <- local_sqlite_connection(new_test_df(), "existing_table")

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, "non_existent_table")
    })
  })
})

describe("DataSource$get_schema()", {
  it("returns proper schema for DataFrameSource", {
    skip_if_no_dataframe_engine()

    df_source <- local_data_frame_source(new_mixed_types_df())

    schema <- df_source$get_schema()
    expect_type(schema, "character")
    expect_match(schema, "Table: test_table")
    expect_match(schema, "id \\(INTEGER\\)")
    expect_match(schema, "name \\(TEXT\\)")
    expect_match(schema, "active \\(BOOLEAN\\)")
    expect_match(schema, "Categorical values")

    expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
  })

  it("returns proper schema for DBISource", {
    db <- local_sqlite_connection(new_test_df())

    dbi_source <- DBISource$new(db$conn, "test_table")
    schema <- dbi_source$get_schema()
    expect_type(schema, "character")
    expect_match(schema, "Table: `test_table`")
    expect_match(schema, "id \\(INTEGER\\)")
    expect_match(schema, "name \\(TEXT\\)")

    expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
  })

  it("correctly reports min/max values for numeric columns", {
    skip_if_no_dataframe_engine()

    df_source <- local_data_frame_source(new_metrics_df())

    schema <- df_source$get_schema()

    expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
    expect_match(schema, "- score \\(FLOAT\\)\\n  Range: 10\\.5 to 30\\.1")
    expect_match(schema, "- count \\(FLOAT\\)\\n  Range: 50 to 200")
  })
})

describe("DataSource$get_db_type()", {
  it("returns correct database type for DataFrameSource", {
    skip_if_no_dataframe_engine()

    df_source <- local_data_frame_source(new_test_df())
    db_type <- df_source$get_db_type()
    expect_true(db_type %in% c("DuckDB", "SQLite"))
  })

  it("returns correct type for SQLite connections", {
    skip_if_not_installed("RSQLite")

    db <- local_sqlite_connection(new_test_df())
    db_source <- DBISource$new(db$conn, "test_table")

    expect_equal(db_source$get_db_type(), "SQLite")
  })
})

describe("DataSource$get_data()", {
  test_df <- new_test_df()

  it("returns all data for both DataFrameSource and DBISource", {
    skip_if_no_dataframe_engine()
    skip_if_not_installed("RSQLite")

    df_source <- local_data_frame_source(test_df)

    result <- df_source$get_data()
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 5)
    expect_equal(ncol(result), 3)

    db <- local_sqlite_connection(test_df)

    dbi_source <- DBISource$new(db$conn, "test_table")
    result <- dbi_source$get_data()
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 5)
    expect_equal(ncol(result), 3)
  })
})

describe("DataSource$execute_query()", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("RSQLite")

  test_df <- new_test_df(rows = 4)
  df_source <- local_data_frame_source(test_df)
  db <- local_sqlite_connection(test_df)
  dbi_source <- DBISource$new(db$conn, "test_table")

  it("executes queries for DataFrameSource", {
    result <- df_source$execute_query(
      "SELECT * FROM test_table WHERE value > 25"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
  })

  it("executes queries for DBISource", {
    result <- dbi_source$execute_query(
      "SELECT * FROM test_table WHERE value > 25"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
  })

  it("handles empty and null queries for DataFrameSource", {
    result_null <- df_source$execute_query(NULL)
    expect_equal(result_null, test_df)

    result_empty <- df_source$execute_query("")
    expect_equal(result_empty, test_df)
  })

  it("handles empty and null queries for DBISource", {
    result_null <- dbi_source$execute_query(NULL)
    expect_equal(result_null, test_df)

    result_empty <- dbi_source$execute_query("")
    expect_equal(result_empty, test_df)
  })

  it("handles filter and sort queries in DBISource", {
    test_users_df <- new_users_df()
    db <- local_sqlite_connection(test_users_df, "users")

    db_source <- DBISource$new(db$conn, "users")

    result <- db_source$execute_query("SELECT * FROM users WHERE age > 30")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(result$name, c("Charlie", "Eve"))

    all_data <- db_source$execute_query(NULL)
    expect_equal(all_data, test_users_df)

    ordered_result <- db_source$execute_query(
      "SELECT * FROM users ORDER BY age DESC"
    )
    expect_equal(ordered_result$name[1], "Charlie")
  })

  it("handles SQL with inline comments", {
    inline_comment_query <- "
    SELECT id, value -- This is a comment
    FROM test_table
    WHERE value > 25 -- Filter for higher values
    "

    result <- df_source$execute_query(inline_comment_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    multiple_comments_query <- "
    SELECT -- Get only these columns
      id, -- ID column
      value -- Value column
    FROM test_table -- Our test table
    WHERE value > 25 -- Only higher values
    "

    result <- df_source$execute_query(multiple_comments_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with multiline comments", {
    multiline_comment_query <- "
    /*
     * This is a multiline comment
     * that spans multiple lines
     */
    SELECT id, value
    FROM test_table
    WHERE value > 25
    "

    result <- df_source$execute_query(multiline_comment_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    embedded_multiline_query <- "
    SELECT id, /* comment between columns */ value
    FROM /* this is
         * a multiline
         * comment
         */ test_table
    WHERE value /* another comment */ > 25
    "

    result <- df_source$execute_query(embedded_multiline_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with trailing semicolons", {
    query_with_semicolon <- "
    SELECT id, value
    FROM test_table
    WHERE value > 25;
    "

    result <- df_source$execute_query(query_with_semicolon)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    query_with_multiple_semicolons <- "
    SELECT id, value
    FROM test_table
    WHERE value > 25;;;;
    "

    result <- df_source$execute_query(query_with_multiple_semicolons)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with mixed comments and semicolons", {
    complex_query <- "
    /*
     * This is a complex query with different comment styles
     */
    SELECT
      id, -- This is the ID column
      value /* Value column */
    FROM
      test_table -- Our test table
    WHERE
      /* Only get higher values */
      value > 25; -- End of query
    "

    result <- df_source$execute_query(complex_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    tricky_comment_query <- "
    SELECT id, value
    FROM test_table
    /* Comment with SQL-like syntax:
     * SELECT * FROM another_table;
     */
    WHERE value > 25 -- WHERE id = 'value; DROP TABLE test;'
    "

    result <- df_source$execute_query(tricky_comment_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with unusual whitespace patterns", {
    unusual_whitespace_query <- "

       SELECT   id,    value

      FROM     test_table

      WHERE    value>25

    "

    result <- df_source$execute_query(unusual_whitespace_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })
})

describe("DBISource$test_query()", {
  test_df <- new_users_df()
  db <- local_sqlite_connection(test_df, "test_table")
  dbi_source <- DBISource$new(db$conn, "test_table")

  it("correctly retrieves one row of data", {
    result <- dbi_source$test_query("SELECT * FROM test_table")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$id, 1)

    result <- dbi_source$test_query("SELECT * FROM test_table WHERE age > 29")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$age, 30)

    result <- dbi_source$test_query(
      "SELECT * FROM test_table ORDER BY age DESC"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$age, 35)

    result <- dbi_source$test_query(
      "SELECT * FROM test_table WHERE age > 100"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 0)
  })

  it("handles errors correctly", {
    expect_error(dbi_source$test_query("SELECT * WRONG SYNTAX"))

    expect_error(dbi_source$test_query("SELECT * FROM non_existent_table"))

    expect_error(dbi_source$test_query(
      "SELECT non_existent_column FROM test_table"
    ))
  })

  it("works with different data types", {
    db <- local_sqlite_connection(new_types_df(), "types_table")
    dbi_source <- DBISource$new(db$conn, "types_table")

    result <- dbi_source$test_query("SELECT * FROM types_table")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_type(result$text_col, "character")
    expect_type(result$num_col, "double")
    expect_type(result$int_col, "integer")
    expect_type(result$bool_col, "integer")
  })
})

describe("DataFrameSource$test_query()", {
  skip_if_no_dataframe_engine()

  test_df <- new_users_df()
  df_source <- local_data_frame_source(test_df, "test_table")

  it("correctly retrieves one row of data", {
    result <- df_source$test_query("SELECT * FROM test_table")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$id, 1)

    result <- df_source$test_query("SELECT * FROM test_table WHERE age > 29")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$age, 30)

    result <- df_source$test_query(
      "SELECT * FROM test_table ORDER BY age DESC"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$age, 35)

    result <- df_source$test_query(
      "SELECT * FROM test_table WHERE age > 100"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 0)
  })
})

describe("test_query() column validation", {
  skip_if_no_dataframe_engine()

  it("allows all columns through, regardless of order", {
    source <- local_data_frame_source(new_test_df())

    # Should succeed with all columns
    result <- source$test_query(
      "SELECT * FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), c("id", "name", "value"))

    # Should succeed with all columns in different order
    result <- source$test_query(
      "SELECT value, id, name FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(sort(names(result)), c("id", "name", "value"))
  })

  it("allows additional computed columns when require_all_columns=TRUE", {
    source <- local_data_frame_source(new_test_df())

    # Should succeed with all columns plus computed columns
    result <- source$test_query(
      "SELECT *, value * 2 as doubled FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_true(all(c("id", "name", "value", "doubled") %in% names(result)))
  })

  it("fails when columns are missing and require_all_columns=TRUE", {
    source <- local_data_frame_source(new_test_df())

    # Should fail when missing one column
    expect_error(
      source$test_query(
        "SELECT id, name FROM test_table",
        require_all_columns = TRUE
      ),
      class = "querychat_missing_columns_error"
    )

    # Should fail when missing multiple columns
    expect_error(
      source$test_query(
        "SELECT id FROM test_table",
        require_all_columns = TRUE
      ),
      class = "querychat_missing_columns_error"
    )
  })

  it("does not validate when require_all_columns=FALSE (default)", {
    source <- local_data_frame_source(new_test_df())

    # Should succeed with subset of columns when not validating
    result <- source$test_query("SELECT id FROM test_table")
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), "id")

    result <- source$test_query(
      "SELECT id FROM test_table",
      require_all_columns = FALSE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), "id")
  })

  it("provides helpful error message listing missing columns", {
    source <- local_data_frame_source(new_test_df())

    expect_snapshot(error = TRUE, {
      source$test_query(
        "SELECT id FROM test_table",
        require_all_columns = TRUE
      )
    })

    expect_snapshot(error = TRUE, {
      source$test_query(
        "SELECT id, name FROM test_table",
        require_all_columns = TRUE
      )
    })
  })

  it("works with DBISource as well", {
    db <- local_sqlite_connection(new_test_df(), "test_table")
    source <- DBISource$new(db$conn, "test_table")

    # Should succeed with all columns
    result <- source$test_query(
      "SELECT * FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), c("id", "name", "value"))

    # Should fail when missing columns
    expect_error(
      source$test_query(
        "SELECT id FROM test_table",
        require_all_columns = TRUE
      ),
      class = "querychat_missing_columns_error"
    )
  })

  it("handles empty result sets correctly", {
    source <- local_data_frame_source(new_test_df())

    # Query with no matches should still validate columns
    result <- source$test_query(
      "SELECT * FROM test_table WHERE id > 999",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 0)
    expect_equal(names(result), c("id", "name", "value"))
  })
})
