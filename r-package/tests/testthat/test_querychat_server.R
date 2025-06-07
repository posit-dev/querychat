library(testthat)
library(DBI)
library(RSQLite)
library(dbplyr)
library(querychat)

test_that("database source query functionality", {
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
  
  # Create database source
  db_source <- database_source(conn, "users")
  
  # Test that we can execute queries
  result <- execute_database_query(db_source, "SELECT * FROM users WHERE age > 30")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 2)  # Charlie and Eve
  expect_equal(result$name, c("Charlie", "Eve"))
  
  # Test that we can get all data
  all_data <- get_database_data(db_source)
  expect_s3_class(all_data, "data.frame")
  expect_equal(nrow(all_data), 5)
  expect_equal(ncol(all_data), 3)
  
  # Test ordering works
  ordered_result <- execute_database_query(db_source, "SELECT * FROM users ORDER BY age DESC")
  expect_equal(ordered_result$name[1], "Charlie")  # Oldest first
  
  # Clean up
  dbDisconnect(conn)
  unlink(temp_db)
})

