library(testthat)
library(DBI)
library(RSQLite)
library(querychat)

test_that("DataSource$test_query() correctly retrieves one row of data", {
  # Create a simple data frame
  test_df <- data.frame(
    id = 1:5,
    name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  # Setup DBI source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)

  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")
  withr::defer(dbi_source$cleanup())

  # Test basic query - should only return one row
  result <- dbi_source$test_query("SELECT * FROM test_table")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 1) # Should only return 1 row
  expect_equal(result$id, 1) # Should be first row

  # Test with WHERE clause
  result <- dbi_source$test_query("SELECT * FROM test_table WHERE value > 25")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 1) # Should only return 1 row
  expect_equal(result$value, 30) # Should return first row with value > 25

  # Test with ORDER BY - should get the highest value
  result <- dbi_source$test_query(
    "SELECT * FROM test_table ORDER BY value DESC"
  )
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 1)
  expect_equal(result$value, 50) # Should be the highest value

  # Test with query returning no results
  result <- dbi_source$test_query("SELECT * FROM test_table WHERE value > 100")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 0) # Should return empty data frame
})

test_that("DataSource$test_query() handles errors correctly", {
  # Setup DBI source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))

  # Create a test table
  test_df <- data.frame(
    id = 1:3,
    value = c(10, 20, 30),
    stringsAsFactors = FALSE
  )
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")

  # Test with invalid SQL
  expect_error(dbi_source$test_query("SELECT * WRONG SYNTAX"))

  # Test with non-existent table
  expect_error(dbi_source$test_query("SELECT * FROM non_existent_table"))

  # Test with non-existent column
  expect_error(dbi_source$test_query(
    "SELECT non_existent_column FROM test_table"
  ))
})

test_that("DataSource$test_query() works with different data types", {
  # Create a data frame with different data types
  test_df <- data.frame(
    id = 1:3,
    text_col = c("text1", "text2", "text3"),
    num_col = c(1.1, 2.2, 3.3),
    int_col = c(10L, 20L, 30L),
    bool_col = c(TRUE, FALSE, TRUE),
    stringsAsFactors = FALSE
  )

  # Setup DBI source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(conn))

  dbWriteTable(conn, "types_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "types_table")

  # Test query with different column types
  result <- dbi_source$test_query("SELECT * FROM types_table")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 1)
  expect_type(result$text_col, "character")
  expect_type(result$num_col, "double")
  expect_type(result$int_col, "integer")
  expect_type(result$bool_col, "integer") # SQLite stores booleans as integers
})
