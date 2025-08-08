library(testthat)

test_that("app database example loads without errors", {
  skip_if_not_installed("DT")
  skip_if_not_installed("RSQLite")
  skip_if_not_installed("shinytest2")

  # Create a simplified test app with mocked ellmer
  test_app_file <- tempfile(fileext = ".R")

  test_app_content <- '

'

  writeLines(test_app_content, test_app_file)

  # Test that the app can be loaded without immediate errors
  expect_no_error({
    # Try to parse and evaluate the app code
    source(test_app_file, local = TRUE)
  })

  # Clean up
  unlink(test_app_file)
})

test_that("database reactive functionality works correctly", {
  skip_if_not_installed("RSQLite")

  library(DBI)
  library(RSQLite)

  # Create test database
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "iris", iris, overwrite = TRUE)
  dbDisconnect(conn)

  # Test database source creation
  db_conn <- dbConnect(RSQLite::SQLite(), temp_db)
  iris_source <- querychat_data_source(db_conn, "iris")

  # Mock chat function
  mock_client <- ellmer::chat_openai(api_key = "boop")

  # Test querychat_init with database source
  config <- querychat_init(
    data_source = iris_source,
    greeting = "Test greeting",
    client = mock_client
  )

  expect_s3_class(config$data_source, "dbi_source")
  expect_s3_class(config$data_source, "querychat_data_source")

  # Test that we can get all data
  result_data <- execute_query(config$data_source, NULL)
  expect_s3_class(result_data, "data.frame")
  expect_equal(nrow(result_data), 150)
  expect_equal(ncol(result_data), 5)

  # Test with a specific query
  query_result <- execute_query(
    config$data_source,
    "SELECT \"Sepal.Length\", \"Sepal.Width\" FROM iris WHERE \"Species\" = 'setosa'"
  )
  expect_s3_class(query_result, "data.frame")
  expect_equal(nrow(query_result), 50)
  expect_equal(ncol(query_result), 2)
  expect_true(all(c("Sepal.Length", "Sepal.Width") %in% names(query_result)))

  # Clean up
  dbDisconnect(db_conn)
  unlink(temp_db)
})
