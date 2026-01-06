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
