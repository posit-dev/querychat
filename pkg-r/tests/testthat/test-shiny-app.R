library(testthat)

test_that("app database example loads without errors", {
  skip_if_not_installed("DT")
  skip_if_not_installed("RSQLite")
  skip_if_not_installed("shinytest2")

  # Create a simplified test app with mocked ellmer
  test_app_dir <- withr::local_tempdir()
  test_app_file <- file.path(test_app_dir, "app.R")
  dir.create(dirname(test_app_file), showWarnings = FALSE)

  file.copy(test_path("apps/basic/app.R"), test_app_file)

  # Test that the app can be loaded without immediate errors
  expect_no_error({
    # Try to parse and evaluate the app code
    source(test_app_file, local = TRUE)
  })
})

test_that("database reactive functionality works correctly", {
  skip_if_not_installed("RSQLite")

  library(DBI)
  library(RSQLite)

  # Create test database
  temp_db <- withr::local_tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "iris", iris, overwrite = TRUE)
  dbDisconnect(conn)

  # Test database source creation
  db_conn <- dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(dbDisconnect(db_conn))

  iris_source <- create_data_source(db_conn, "iris")

  # Mock chat function
  mock_client <- ellmer::chat_openai(api_key = "boop")

  # Test QueryChat$new() with database source
  qc <- QueryChat$new(
    data_source = iris_source,
    table_name = "iris",
    greeting = "Test greeting",
    client = mock_client
  )

  expect_s3_class(qc$data_source, "dbi_source")
  expect_s3_class(qc$data_source, "querychat_data_source")

  # Test that we can get all data
  result_data <- execute_query(qc$data_source, NULL)
  expect_s3_class(result_data, "data.frame")
  expect_equal(nrow(result_data), 150)
  expect_equal(ncol(result_data), 5)

  # Test with a specific query
  query_result <- execute_query(
    qc$data_source,
    "SELECT \"Sepal.Length\", \"Sepal.Width\" FROM iris WHERE \"Species\" = 'setosa'"
  )
  expect_s3_class(query_result, "data.frame")
  expect_equal(nrow(query_result), 50)
  expect_equal(ncol(query_result), 2)
  expect_true(all(c("Sepal.Length", "Sepal.Width") %in% names(query_result)))
})
