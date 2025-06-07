library(testthat)
library(DBI)
library(RSQLite)
library(dbplyr)
library(querychat)

# Helper function to create a test querychat server
create_test_querychat_server <- function(conn) {
  # Create a test chat configuration
  system_prompt <- "You are a helpful query assistant."
  
  # Create a temporary Shiny session
  session <- shiny::Session$new()
  session$input <- list()
  session$output <- list()
  
  # Initialize querychat server
  querychat_config <- list(
    conn = conn,
    system_prompt = system_prompt
  )
  
  # Create a mock module server
  server <- function(input, output, session) {
    querychat_server("test", querychat_config)
  }
  
  # Call the server
  server(session$input, session$output, session)
  
  # Return the session and config
  list(session = session, config = querychat_config)
}

test_that("querychat_server returns lazy dbplyr tbl", {
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
  
  # Create test server
  test_env <- create_test_querychat_server(conn)
  query_func <- test_env$config$query
  
  # Test that query returns a lazy tbl
  result <- query_func("SELECT * FROM users WHERE age > 30")
  expect_s3_class(result, "tbl")
  expect_s3_class(result, "tbl_dbi")
  
  # Test that the query hasn't been executed yet
  # We can check this by modifying the table and seeing if the result changes
  dbExecute(conn, "UPDATE users SET age = age + 10")
  result_after_update <- query_func("SELECT * FROM users WHERE age > 30")
  expect_equal(nrow(result), nrow(result_after_update))  # Still same number of rows
  
  # Test that we can chain dbplyr operations
  chained_result <- result |> 
    filter(age > 30) |> 
    arrange(desc(age))
  expect_s3_class(chained_result, "tbl")
  expect_s3_class(chained_result, "tbl_dbi")
  
  # Test that collect() executes the query
  collected_result <- collect(chained_result)
  expect_s3_class(collected_result, "data.frame")
  expect_equal(nrow(collected_result), 3)  # Charlie, Diana, and Eve after update
  
  # Clean up
  dbDisconnect(conn)
  unlink(temp_db)
})

# Run the tests
testthat::test_file("test_querychat_server.R")
