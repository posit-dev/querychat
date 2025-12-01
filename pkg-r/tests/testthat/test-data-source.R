library(testthat)
library(DBI)
library(RSQLite)
library(querychat)

test_that("DataFrameSource creates proper R6 object", {
  # Create a simple data frame
  test_df <- data.frame(
    id = 1:5,
    name = c("A", "B", "C", "D", "E"),
    value = c(10.5, 20.3, 15.7, 30.1, 25.9),
    stringsAsFactors = FALSE
  )

  # Test with explicit table name
  source <- DataFrameSource$new(test_df, "test_table")
  withr::defer(source$cleanup())

  expect_s3_class(source, "DataFrameSource")
  expect_s3_class(source, "DataSource")
  expect_equal(source$table_name, "test_table")
})

test_that("DBISource creates proper R6 object", {
  # Create temporary SQLite database
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))

  # Create test table
  test_data <- data.frame(
    id = 1:5,
    name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
    age = c(25, 30, 35, 28, 32),
    stringsAsFactors = FALSE
  )

  dbWriteTable(conn, "users", test_data, overwrite = TRUE)

  # Test DBI source creation
  db_source <- DBISource$new(conn, "users")
  expect_s3_class(db_source, "DBISource")
  expect_s3_class(db_source, "DataSource")
  expect_equal(db_source$table_name, "users")
})

test_that("get_schema methods return proper schema", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    name = c("A", "B", "C", "D", "E"),
    active = c(TRUE, FALSE, TRUE, TRUE, FALSE),
    stringsAsFactors = FALSE
  )

  df_source <- DataFrameSource$new(test_df, "test_table")
  withr::defer(df_source$cleanup())

  schema <- df_source$get_schema()
  expect_type(schema, "character")
  expect_match(schema, "Table: test_table")
  expect_match(schema, "id \\(INTEGER\\)")
  expect_match(schema, "name \\(TEXT\\)")
  expect_match(schema, "active \\(BOOLEAN\\)")
  expect_match(schema, "Categorical values") # Should list categorical values

  # Test min/max values in schema - specifically for the id column
  expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")

  # Test with DBI source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))

  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")
  schema <- dbi_source$get_schema()
  expect_type(schema, "character")
  expect_match(schema, "Table: `test_table`")
  expect_match(schema, "id \\(INTEGER\\)")
  expect_match(schema, "name \\(TEXT\\)")

  # Test min/max values in DBI source schema - specifically for the id column
  expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
})

test_that("execute_query works for both source types", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- DataFrameSource$new(test_df, "test_table")
  withr::defer(df_source$cleanup())
  result <- df_source$execute_query("SELECT * FROM test_table WHERE value > 25")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3) # Should return 3 rows (30, 40, 50)

  # Test with DBI source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")
  result <- dbi_source$execute_query("SELECT * FROM test_table WHERE value > 25")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3) # Should return 3 rows (30, 40, 50)
})

test_that("execute_query works with empty/null queries", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- DataFrameSource$new(test_df, "test_table")
  withr::defer(df_source$cleanup())

  # Test with NULL query
  result_null <- df_source$execute_query(NULL)
  expect_s3_class(result_null, "data.frame")
  expect_equal(nrow(result_null), 5) # Should return all rows
  expect_equal(ncol(result_null), 2) # Should return all columns

  # Test with empty string query
  result_empty <- df_source$execute_query("")
  expect_s3_class(result_empty, "data.frame")
  expect_equal(nrow(result_empty), 5) # Should return all rows
  expect_equal(ncol(result_empty), 2) # Should return all columns

  # Test with DBI source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))

  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")

  # Test with NULL query
  result_null <- dbi_source$execute_query(NULL)
  expect_s3_class(result_null, "data.frame")
  expect_equal(nrow(result_null), 5) # Should return all rows
  expect_equal(ncol(result_null), 2) # Should return all columns

  # Test with empty string query
  result_empty <- dbi_source$execute_query("")
  expect_s3_class(result_empty, "data.frame")
  expect_equal(nrow(result_empty), 5) # Should return all rows
  expect_equal(ncol(result_empty), 2) # Should return all columns
})


test_that("get_schema correctly reports min/max values for numeric columns", {
  # Create a dataframe with multiple numeric columns
  test_df <- data.frame(
    id = 1:5,
    score = c(10.5, 20.3, 15.7, 30.1, 25.9),
    count = c(100, 200, 150, 50, 75),
    stringsAsFactors = FALSE
  )

  df_source <- DataFrameSource$new(test_df, "test_metrics")
  withr::defer(df_source$cleanup())
  schema <- df_source$get_schema()

  # Check that each numeric column has the correct min/max values
  expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
  expect_match(schema, "- score \\(FLOAT\\)\\n  Range: 10\\.5 to 30\\.1")
  # Note: In the test output, count was detected as FLOAT rather than INTEGER
  expect_match(schema, "- count \\(FLOAT\\)\\n  Range: 50 to 200")
})

test_that("get_system_prompt generates appropriate system prompt", {
  test_df <- data.frame(
    id = 1:3,
    name = c("A", "B", "C"),
    stringsAsFactors = FALSE
  )

  df_source <- DataFrameSource$new(test_df, "test_table")
  withr::defer(df_source$cleanup())

  prompt <- get_system_prompt(
    df_source,
    data_description = "A test dataframe"
  )
  expect_type(prompt, "character")
  expect_true(nchar(prompt) > 0)
  expect_match(prompt, "A test dataframe")
  expect_match(prompt, "Table: test_table")
})

test_that("QueryChat$new() automatically handles data.frame inputs", {
  # Test that QueryChat$new() accepts data frames directly
  test_df <- data.frame(id = 1:3, name = c("A", "B", "C"))

  # Should work with data frame and auto-convert it
  qc <- QueryChat$new(
    data_source = test_df,
    table_name = "test_df",
    greeting = "Test greeting"
  )
  withr::defer(qc$cleanup())

  expect_s3_class(qc$data_source, "DataSource")
  expect_s3_class(qc$data_source, "DataFrameSource")

  # Should work with proper data source too
  df_source <- DataFrameSource$new(test_df, "test_table")
  withr::defer(df_source$cleanup())

  qc2 <- QueryChat$new(
    data_source = df_source,
    table_name = "test_table",
    greeting = "Test greeting"
  )
  expect_s3_class(qc2$data_source, "DataSource")
})

test_that("QueryChat$new() works with both source types", {
  # Test with data frame
  test_df <- data.frame(
    id = 1:3,
    name = c("A", "B", "C"),
    stringsAsFactors = FALSE
  )

  # Create data source and test with QueryChat$new()
  df_source <- DataFrameSource$new(test_df, "test_source")
  withr::defer(df_source$cleanup())

  qc <- QueryChat$new(
    data_source = df_source,
    table_name = "test_source",
    greeting = "Test greeting"
  )

  expect_s3_class(qc$data_source, "DataFrameSource")
  expect_equal(qc$data_source$table_name, "test_source")

  # Test with database connection
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))

  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")
  qc2 <- QueryChat$new(
    data_source = dbi_source,
    table_name = "test_table",
    greeting = "Test greeting"
  )
  expect_s3_class(qc2$data_source, "DBISource")
  expect_equal(qc2$data_source$table_name, "test_table")
})

test_that("get_data returns all data", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- DataFrameSource$new(test_df, "test_table")
  withr::defer(df_source$cleanup())

  result <- df_source$get_data()
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 5)
  expect_equal(ncol(result), 2)

  # Test with DBI source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")
  result <- dbi_source$get_data()
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 5)
  expect_equal(ncol(result), 2)
})
