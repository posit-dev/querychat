library(testthat)
library(DBI)
library(RSQLite)
library(querychat)

test_that("execute_query handles SQL with inline comments", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  # Create data source
  df_source <- create_data_source(test_df, table_name = "test_table")
  withr::defer(cleanup_source(df_source))

  # Test with inline comments
  inline_comment_query <- "
  SELECT id, value -- This is a comment
  FROM test_table
  WHERE value > 25 -- Filter for higher values
  "

  result <- execute_query(df_source, inline_comment_query)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3) # Should return 3 rows (30, 40, 50)
  expect_equal(ncol(result), 2)

  # Test with multiple inline comments
  multiple_comments_query <- "
  SELECT -- Get only these columns
    id, -- ID column
    value -- Value column
  FROM test_table -- Our test table
  WHERE value > 25 -- Only higher values
  "

  result <- execute_query(df_source, multiple_comments_query)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)
})

test_that("execute_query handles SQL with multiline comments", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  # Create data source
  df_source <- create_data_source(test_df, table_name = "test_table")
  withr::defer(cleanup_source(df_source))

  # Test with multiline comments
  multiline_comment_query <- "
  /*
   * This is a multiline comment
   * that spans multiple lines
   */
  SELECT id, value
  FROM test_table
  WHERE value > 25
  "

  result <- execute_query(df_source, multiline_comment_query)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Test with embedded multiline comments
  embedded_multiline_query <- "
  SELECT id, /* comment between columns */ value
  FROM /* this is
       * a multiline
       * comment
       */ test_table
  WHERE value /* another comment */ > 25
  "

  result <- execute_query(df_source, embedded_multiline_query)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)
})

test_that("execute_query handles SQL with trailing semicolons", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  # Create data source
  df_source <- create_data_source(test_df, table_name = "test_table")
  withr::defer(cleanup_source(df_source))

  # Test with trailing semicolon
  query_with_semicolon <- "
  SELECT id, value
  FROM test_table
  WHERE value > 25;
  "

  result <- execute_query(df_source, query_with_semicolon)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Test with multiple semicolons (which could happen with LLM-generated SQL)
  query_with_multiple_semicolons <- "
  SELECT id, value
  FROM test_table
  WHERE value > 25;;;;
  "

  result <- execute_query(df_source, query_with_multiple_semicolons)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)
})

test_that("execute_query handles SQL with mixed comments and semicolons", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  # Create data source
  df_source <- create_data_source(test_df, table_name = "test_table")
  withr::defer(cleanup_source(df_source))

  # Test with a mix of comment styles and semicolons
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

  result <- execute_query(df_source, complex_query)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Test with comments that contain SQL-like syntax
  tricky_comment_query <- "
  SELECT id, value
  FROM test_table
  /* Comment with SQL-like syntax:
   * SELECT * FROM another_table;
   */
  WHERE value > 25 -- WHERE id = 'value; DROP TABLE test;'
  "

  result <- execute_query(df_source, tricky_comment_query)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)
})

test_that("execute_query handles SQL with unusual whitespace patterns", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  # Create data source
  df_source <- create_data_source(test_df, table_name = "test_table")
  withr::defer(cleanup_source(df_source))

  # Test with unusual whitespace patterns (which LLMs might generate)
  unusual_whitespace_query <- "

     SELECT   id,    value

    FROM     test_table

    WHERE    value>25

  "

  result <- execute_query(df_source, unusual_whitespace_query)
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)
})
