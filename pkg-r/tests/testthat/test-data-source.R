describe("DataSource$new()", {
  it("creates proper R6 object for DataFrameSource", {
    test_df <- new_test_df()

    source <- DataFrameSource$new(test_df, "test_table")
    withr::defer(source$cleanup())

    expect_s3_class(source, "DataFrameSource")
    expect_s3_class(source, "DataSource")
    expect_equal(source$table_name, "test_table")
  })

  it("creates proper R6 object for DBISource", {
    db <- local_sqlite_connection(new_users_df(), "users")

    db_source <- DBISource$new(db$conn, "users")
    expect_s3_class(db_source, "DBISource")
    expect_s3_class(db_source, "DataSource")
    expect_equal(db_source$table_name, "users")
  })
})

describe("DataSource$get_schema()", {
  it("returns proper schema for DataFrameSource", {
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
    df_source <- local_data_frame_source(new_metrics_df())

    schema <- df_source$get_schema()

    expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
    expect_match(schema, "- score \\(FLOAT\\)\\n  Range: 10\\.5 to 30\\.1")
    expect_match(schema, "- count \\(FLOAT\\)\\n  Range: 50 to 200")
  })
})

describe("assemble_system_prompt()", {
  df_source <- local_data_frame_source(new_test_df(3))

  it("generates appropriate system prompt", {
    prompt <- assemble_system_prompt(
      df_source,
      data_description = "A test dataframe"
    )
    expect_type(prompt, "character")
    expect_true(nchar(prompt) > 0)
    expect_match(prompt, "A test dataframe")
    expect_match(prompt, "Table: test_table")
  })

  it("uses db_type to customize prompt template", {
    sys_prompt <- assemble_system_prompt(df_source)

    expect_equal(df_source$get_db_type(), "DuckDB")
    expect_true(grepl("DuckDB SQL Tips", sys_prompt, fixed = TRUE))
  })
})

describe("DataSource$get_db_type()", {
  it("returns DuckDB for DataFrameSource", {
    df_source <- local_data_frame_source(new_test_df())
    expect_equal(df_source$get_db_type(), "DuckDB")
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

describe("DataSource$test_query()", {
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
