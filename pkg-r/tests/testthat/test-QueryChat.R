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
  conn <- DBI::dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(DBI::dbDisconnect(conn))

  DBI::dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- DBISource$new(conn, "test_table")
  qc2 <- QueryChat$new(
    data_source = dbi_source,
    table_name = "test_table",
    greeting = "Test greeting"
  )
  expect_s3_class(qc2$data_source, "DBISource")
  expect_equal(qc2$data_source$table_name, "test_table")
})
