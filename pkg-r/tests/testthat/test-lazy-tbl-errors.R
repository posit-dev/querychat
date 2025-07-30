library(testthat)
library(DBI)
library(RSQLite)
library(dplyr)
library(querychat)

test_that("get_lazy_data properly propagates errors without fallback", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )
  
  # Create a data source
  df_source <- querychat_data_source(test_df, table_name = "test_table")
  
  # Invalid SQL query with syntax error
  invalid_query <- "SELECT * FROM test_table WHERE non_existent_column = 'value'"
  
  # Check that the error is propagated rather than falling back to the full table
  expect_error(get_lazy_data(df_source, invalid_query))
  
  # Clean up
  cleanup_source(df_source)
})

test_that("get_lazy_data errors on empty query after cleaning", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )
  
  # Create a data source
  df_source <- querychat_data_source(test_df, table_name = "test_table")
  
  # Query that will be empty after cleaning (only comments)
  comment_only_query <- "-- This is just a comment\n/* Another comment */"
  
  # Check that an error is raised instead of falling back to the full table
  expect_error(get_lazy_data(df_source, comment_only_query), "empty query")
  
  # Clean up
  cleanup_source(df_source)
})