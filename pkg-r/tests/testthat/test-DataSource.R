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

  it("errors with non-DataSource input", {
    expect_snapshot(error = TRUE, {
      assemble_system_prompt(
        list(not = "a data source"),
        data_description = "Test"
      )
    })

    expect_snapshot(error = TRUE, {
      assemble_system_prompt(
        data.frame(x = 1:3),
        data_description = "Test"
      )
    })
  })

  it("works without extra_instructions", {
    prompt <- assemble_system_prompt(
      df_source,
      data_description = "A test dataframe",
      extra_instructions = NULL
    )

    expect_type(prompt, "character")
    expect_true(nchar(prompt) > 0)
    expect_match(prompt, "A test dataframe")
    expect_match(prompt, "Table: test_table")
  })

  it("accepts file paths for data_description", {
    temp_file <- withr::local_tempfile(fileext = ".txt")
    writeLines("This is a description from a file", temp_file)

    prompt <- assemble_system_prompt(
      df_source,
      data_description = temp_file
    )

    expect_type(prompt, "character")
    expect_match(prompt, "This is a description from a file")
  })

  it("accepts file paths for extra_instructions", {
    temp_file <- withr::local_tempfile(fileext = ".txt")
    writeLines("Extra instructions from file", temp_file)

    prompt <- assemble_system_prompt(
      df_source,
      extra_instructions = temp_file
    )

    expect_type(prompt, "character")
    expect_match(prompt, "Extra instructions from file")
  })

  it("accepts inline text for data_description", {
    prompt <- assemble_system_prompt(
      df_source,
      data_description = "Inline description text"
    )

    expect_type(prompt, "character")
    expect_match(prompt, "Inline description text")
  })

  it("accepts inline text for extra_instructions", {
    prompt <- assemble_system_prompt(
      df_source,
      extra_instructions = "Inline extra instructions"
    )

    expect_type(prompt, "character")
    expect_match(prompt, "Inline extra instructions")
  })

  it("works with both description and instructions as inline text", {
    prompt <- assemble_system_prompt(
      df_source,
      data_description = "Description here",
      extra_instructions = "Instructions here"
    )

    expect_type(prompt, "character")
    expect_match(prompt, "Description here")
    expect_match(prompt, "Instructions here")
  })

  it("accepts custom schema parameter", {
    custom_schema <- "Table: custom_table\nColumns:\n- id (INTEGER)\n- name (TEXT)"

    prompt <- assemble_system_prompt(
      df_source,
      schema = custom_schema
    )

    expect_type(prompt, "character")
    expect_match(prompt, "Table: custom_table")
    expect_match(prompt, "id \\(INTEGER\\)")
    expect_match(prompt, "name \\(TEXT\\)")
    # Should use custom schema, not auto-generated one
    expect_false(grepl("Table: test_table", prompt, fixed = TRUE))
  })

  it("auto-generates schema when schema parameter is NULL", {
    prompt_no_schema <- assemble_system_prompt(
      df_source,
      schema = NULL
    )

    # Should contain auto-generated schema from the source
    expect_type(prompt_no_schema, "character")
    expect_match(prompt_no_schema, "Table: test_table")
    expect_match(prompt_no_schema, "id \\(INTEGER\\)")
    expect_match(prompt_no_schema, "name \\(TEXT\\)")
  })

  it("allows custom categorical_threshold via source$get_schema()", {
    # Create a source with categorical data
    df_with_categories <- data.frame(
      id = 1:10,
      category = rep(c("A", "B", "C", "D", "E"), each = 2)
    )
    cat_source <- local_data_frame_source(df_with_categories)

    # With low threshold, categories should not be listed
    schema_low_threshold <- cat_source$get_schema(categorical_threshold = 3)
    prompt_low <- assemble_system_prompt(
      cat_source,
      schema = schema_low_threshold
    )
    expect_false(grepl("Categorical values:", prompt_low))

    # With high threshold, categories should be listed
    schema_high_threshold <- cat_source$get_schema(categorical_threshold = 10)
    prompt_high <- assemble_system_prompt(
      cat_source,
      schema = schema_high_threshold
    )
    expect_match(prompt_high, "Categorical values:")
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
