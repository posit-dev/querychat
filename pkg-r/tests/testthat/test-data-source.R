library(testthat)
library(DBI)
library(RSQLite)
library(dplyr)
library(querychat)

test_that("querychat_data_source.data.frame creates proper S3 object", {
  # Create a simple data frame
  test_df <- data.frame(
    id = 1:5,
    name = c("A", "B", "C", "D", "E"),
    value = c(10.5, 20.3, 15.7, 30.1, 25.9),
    stringsAsFactors = FALSE
  )

  # Test with explicit table name
  source <- querychat_data_source(test_df, table_name = "test_table")
  expect_s3_class(source, "data_frame_source")
  expect_s3_class(source, "querychat_data_source")
  expect_equal(source$table_name, "test_table")
  expect_true(inherits(source$conn, "DBIConnection"))

  # Clean up
  cleanup_source(source)
})

test_that("querychat_data_source.DBIConnection creates proper S3 object", {
  # Create temporary SQLite database
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)

  # Create test table
  test_data <- data.frame(
    id = 1:5,
    name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
    age = c(25, 30, 35, 28, 32),
    stringsAsFactors = FALSE
  )

  dbWriteTable(conn, "users", test_data, overwrite = TRUE)

  # Test DBI source creation
  db_source <- querychat_data_source(conn, "users")
  expect_s3_class(db_source, "dbi_source")
  expect_s3_class(db_source, "querychat_data_source")
  expect_equal(db_source$table_name, "users")
  expect_equal(db_source$categorical_threshold, 20)

  # Clean up
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("get_schema methods return proper schema", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    name = c("A", "B", "C", "D", "E"),
    active = c(TRUE, FALSE, TRUE, TRUE, FALSE),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")
  schema <- get_schema(df_source)
  expect_type(schema, "character")
  expect_match(schema, "Table: test_table")
  expect_match(schema, "id \\(INTEGER\\)")
  expect_match(schema, "name \\(TEXT\\)")
  expect_match(schema, "active \\(BOOLEAN\\)")
  expect_match(schema, "Categorical values") # Should list categorical values

  # Test min/max values in schema - specifically for the id column
  expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")

  # Test with DBI source
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")
  schema <- get_schema(dbi_source)
  expect_type(schema, "character")
  expect_match(schema, "Table: test_table")
  expect_match(schema, "id \\(INTEGER\\)")
  expect_match(schema, "name \\(TEXT\\)")

  # Test min/max values in DBI source schema - specifically for the id column
  expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("execute_query works for both source types", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")
  result <- execute_query(
    df_source,
    "SELECT * FROM test_table WHERE value > 25"
  )
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3) # Should return 3 rows (30, 40, 50)

  # Test with DBI source
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")
  result <- execute_query(
    dbi_source,
    "SELECT * FROM test_table WHERE value > 25"
  )
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3) # Should return 3 rows (30, 40, 50)

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("execute_query works with empty/null queries", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")

  # Test with NULL query
  result_null <- execute_query(df_source, NULL)
  expect_s3_class(result_null, "data.frame")
  expect_equal(nrow(result_null), 5) # Should return all rows
  expect_equal(ncol(result_null), 2) # Should return all columns

  # Test with empty string query
  result_empty <- execute_query(df_source, "")
  expect_s3_class(result_empty, "data.frame")
  expect_equal(nrow(result_empty), 5) # Should return all rows
  expect_equal(ncol(result_empty), 2) # Should return all columns

  # Test with DBI source
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")

  # Test with NULL query
  result_null <- execute_query(dbi_source, NULL)
  expect_s3_class(result_null, "data.frame")
  expect_equal(nrow(result_null), 5) # Should return all rows
  expect_equal(ncol(result_null), 2) # Should return all columns

  # Test with empty string query
  result_empty <- execute_query(dbi_source, "")
  expect_s3_class(result_empty, "data.frame")
  expect_equal(nrow(result_empty), 5) # Should return all rows
  expect_equal(ncol(result_empty), 2) # Should return all columns

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("get_lazy_data returns tbl objects", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")
  lazy_data <- get_lazy_data(df_source)
  expect_s3_class(lazy_data, "tbl")

  # Test with DBI source
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")
  lazy_data <- get_lazy_data(dbi_source)
  expect_s3_class(lazy_data, "tbl")

  # Test chaining with dplyr
  filtered_data <- lazy_data %>%
    dplyr::filter(value > 25) %>%
    dplyr::collect()
  expect_equal(nrow(filtered_data), 3) # Should return 3 rows (30, 40, 50)

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("get_lazy_data works with empty query", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")

  # Test with NULL query
  lazy_data_null <- get_lazy_data(df_source, NULL)
  expect_s3_class(lazy_data_null, "tbl")
  result_null <- dplyr::collect(lazy_data_null)
  expect_equal(nrow(result_null), 5)

  # Test with empty string query
  lazy_data_empty <- get_lazy_data(df_source, "")
  expect_s3_class(lazy_data_empty, "tbl")
  result_empty <- dplyr::collect(lazy_data_empty)
  expect_equal(nrow(result_empty), 5)

  # Test with DBI source
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")

  # Test with NULL query
  lazy_data_null <- get_lazy_data(dbi_source, NULL)
  expect_s3_class(lazy_data_null, "tbl")
  result_null <- dplyr::collect(lazy_data_null)
  expect_equal(nrow(result_null), 5)

  # Test with empty string query
  lazy_data_empty <- get_lazy_data(dbi_source, "")
  expect_s3_class(lazy_data_empty, "tbl")
  result_empty <- dplyr::collect(lazy_data_empty)
  expect_equal(nrow(result_empty), 5)

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("get_schema correctly reports min/max values for numeric columns", {
  # Create a dataframe with multiple numeric columns
  test_df <- data.frame(
    id = 1:5,
    score = c(10.5, 20.3, 15.7, 30.1, 25.9),
    count = c(100, 200, 150, 50, 75),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_metrics")
  schema <- get_schema(df_source)

  # Check that each numeric column has the correct min/max values
  expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
  expect_match(schema, "- score \\(FLOAT\\)\\n  Range: 10\\.5 to 30\\.1")
  # Note: In the test output, count was detected as FLOAT rather than INTEGER
  expect_match(schema, "- count \\(FLOAT\\)\\n  Range: 50 to 200")

  # Clean up
  cleanup_source(df_source)
})

test_that("create_system_prompt generates appropriate system prompt", {
  test_df <- data.frame(
    id = 1:3,
    name = c("A", "B", "C"),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")
  prompt <- create_system_prompt(
    df_source,
    data_description = "A test dataframe"
  )
  expect_type(prompt, "character")
  expect_true(nchar(prompt) > 0)
  expect_match(prompt, "A test dataframe")
  expect_match(prompt, "Table: test_table")

  # Clean up
  cleanup_source(df_source)
})

test_that("querychat_init automatically handles data.frame inputs", {
  # Test that querychat_init accepts data frames directly
  test_df <- data.frame(id = 1:3, name = c("A", "B", "C"))

  # Should work with data frame and auto-convert it
  config <- querychat_init(data_source = test_df, greeting = "Test greeting")
  expect_s3_class(config, "querychat_config")
  expect_s3_class(config$data_source, "querychat_data_source")
  expect_s3_class(config$data_source, "data_frame_source")

  # Should work with proper data source too
  df_source <- querychat_data_source(test_df, table_name = "test_table")
  config <- querychat_init(data_source = df_source, greeting = "Test greeting")
  expect_s3_class(config, "querychat_config")

  # Clean up
  cleanup_source(df_source)
  cleanup_source(config$data_source)
})

test_that("querychat_init works with both source types", {
  # Test with data frame
  test_df <- data.frame(
    id = 1:3,
    name = c("A", "B", "C"),
    stringsAsFactors = FALSE
  )

  # Create data source and test with querychat_init
  df_source <- querychat_data_source(test_df, table_name = "test_source")
  config <- querychat_init(data_source = df_source, greeting = "Test greeting")
  expect_s3_class(config, "querychat_config")
  expect_s3_class(config$data_source, "data_frame_source")
  expect_equal(config$data_source$table_name, "test_source")

  # Test with database connection
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")
  config <- querychat_init(data_source = dbi_source, greeting = "Test greeting")
  expect_s3_class(config, "querychat_config")
  expect_s3_class(config$data_source, "dbi_source")
  expect_equal(config$data_source$table_name, "test_table")

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})
