library(testthat)
library(DBI)
library(RSQLite)
library(querychat)

test_that("database_source creation and basic functionality", {
  # Create temporary SQLite database
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  
  # Create test table
  test_data <- data.frame(
    id = 1:5,
    name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
    age = c(25, 30, 35, 28, 32),
    city = c("NYC", "LA", "NYC", "Chicago", "LA"),
    stringsAsFactors = FALSE
  )
  
  dbWriteTable(conn, "users", test_data, overwrite = TRUE)
  
  # Test database_source creation
  db_source <- database_source(conn, "users")
  expect_s3_class(db_source, "database_source")
  expect_equal(db_source$table_name, "users")
  expect_equal(db_source$categorical_threshold, 20)
  
  # Test schema generation
  schema <- get_database_schema(db_source)
  expect_type(schema, "character")
  expect_true(grepl("Table: users", schema))
  expect_true(grepl("id \\(INTEGER\\)", schema))
  expect_true(grepl("name \\(TEXT\\)", schema))
  expect_true(grepl("Categorical values:", schema))  # Should show city values
  
  # Test query execution
  result <- execute_database_query(db_source, "SELECT * FROM users WHERE age > 30")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 2)  # Charlie and Eve
  
  # Test get all data
  all_data <- get_database_data(db_source)
  expect_s3_class(all_data, "data.frame")
  expect_equal(nrow(all_data), 5)
  expect_equal(ncol(all_data), 4)
  
  # Clean up
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("database_source error handling", {
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  
  # Test error for non-existent table
  expect_error(
    database_source(conn, "nonexistent_table"),
    "Table 'nonexistent_table' not found"
  )
  
  # Test error for invalid connection
  expect_error(
    database_source("not_a_connection", "table"),
    "must be a valid DBI connection object"
  )
  
  # Test error for invalid table name
  dbWriteTable(conn, "test", data.frame(x = 1:3), overwrite = TRUE)
  expect_error(
    database_source(conn, c("table1", "table2")),
    "must be a single character string"
  )
  
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("querychat_init with database_source", {
  # Create temporary SQLite database
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  
  # Create test table
  test_data <- data.frame(
    product = c("A", "B", "C"),
    sales = c(100, 150, 200),
    region = c("North", "South", "North"),
    stringsAsFactors = FALSE
  )
  
  dbWriteTable(conn, "sales", test_data, overwrite = TRUE)
  
  # Create database source
  db_source <- database_source(conn, "sales")
  
  # Test querychat_init with database source
  config <- querychat_init(
    data_source = db_source,
    greeting = "Test greeting",
    data_description = "Test sales data"
  )
  
  expect_s3_class(config, "querychat_config")
  expect_true(config$is_database_source)
  expect_equal(config$table_name, "sales")
  expect_null(config$df)  # Should be NULL for database sources
  expect_identical(config$db_source, db_source)
  expect_type(config$system_prompt, "character")
  expect_true(nchar(config$system_prompt) > 0)
  
  # Clean up
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("backwards compatibility with df argument", {
  test_df <- data.frame(x = 1:3, y = letters[1:3])
  
  # Test that using df argument still works but shows warning
  expect_warning(
    config <- querychat_init(df = test_df, tbl_name = "test"),
    "deprecated"
  )
  
  expect_s3_class(config, "querychat_config")
  expect_false(config$is_database_source)
  expect_equal(config$table_name, "test")
  
  # Test error when both df and data_source provided
  expect_error(
    querychat_init(data_source = test_df, df = test_df),
    "Cannot specify both"
  )
})