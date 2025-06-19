library(testthat)
library(DBI)
library(RSQLite)
library(dplyr)
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
  db_source <- querychat_data_source(conn, "users")
  
  # Test that we can execute queries
  result <- execute_query(db_source, "SELECT * FROM users WHERE age > 30")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 2)  # Charlie and Eve
  expect_equal(result$name, c("Charlie", "Eve"))
  
  # Test that we can get all data as lazy dbplyr table
  all_data <- get_lazy_data(db_source)
  expect_s3_class(all_data, c("tbl_SQLiteConnection", "tbl_dbi", "tbl_sql", "tbl_lazy", "tbl"))
  
  # Test that it can be chained with dbplyr operations before collect()
  filtered_data <- all_data |>
    dplyr::filter(age >= 30) |>
    dplyr::select(name, age) |>
    dplyr::collect()
  
  expect_s3_class(filtered_data, "data.frame")
  expect_equal(nrow(filtered_data), 3)  # Bob, Charlie, Eve
  
  # Test that the lazy table can be collected to get all data
  collected_data <- dplyr::collect(all_data)
  expect_s3_class(collected_data, "data.frame")
  expect_equal(nrow(collected_data), 5)
  expect_equal(ncol(all_data), 3)
  
  # Test ordering works
  ordered_result <- execute_query(db_source, "SELECT * FROM users ORDER BY age DESC")
  expect_equal(ordered_result$name[1], "Charlie")  # Oldest first
  
  # Clean up
  dbDisconnect(conn)
  unlink(temp_db)
})

