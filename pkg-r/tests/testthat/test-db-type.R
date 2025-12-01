library(testthat)

test_that("get_db_type returns correct type for DataFrameSource", {
  # Create a simple data frame source
  df <- data.frame(x = 1:5, y = letters[1:5])
  df_source <- DataFrameSource$new(df, "test_table")
  withr::defer(df_source$cleanup())

  # Test that get_db_type returns "DuckDB"
  expect_equal(df_source$get_db_type(), "DuckDB")
})

test_that("get_db_type returns correct type for DBISource with SQLite", {
  skip_if_not_installed("RSQLite")

  # Create a SQLite database source
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- DBI::dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(DBI::dbDisconnect(conn))
  DBI::dbWriteTable(conn, "test_table", data.frame(x = 1:5, y = letters[1:5]))
  db_source <- DBISource$new(conn, "test_table")

  # Test that get_db_type returns the correct database type
  expect_equal(db_source$get_db_type(), "SQLite")
})

test_that("get_db_type is correctly used in get_system_prompt", {
  # Create a simple data frame source
  df <- data.frame(x = 1:5, y = letters[1:5])
  df_source <- DataFrameSource$new(df, "test_table")
  withr::defer(df_source$cleanup())

  # Generate system prompt
  sys_prompt <- get_system_prompt(df_source)

  # Check that "DuckDB" appears in the prompt content
  expect_true(grepl("DuckDB SQL", sys_prompt, fixed = TRUE))
})

test_that("get_db_type is used to customize prompt template", {
  # Create a simple data frame source
  df <- data.frame(x = 1:5, y = letters[1:5])
  df_source <- DataFrameSource$new(df, "test_table")
  withr::defer(df_source$cleanup())

  # Get the db_type
  db_type <- df_source$get_db_type()

  # Check that the db_type is correctly returned
  expect_equal(db_type, "DuckDB")

  # Verify the value is used in the system prompt
  # This is an indirect test that doesn't need mocking
  # We just check that the string appears somewhere in the system prompt
  prompt <- get_system_prompt(df_source)
  expect_true(grepl(db_type, prompt, fixed = TRUE))
})
