library(testthat)
library(DBI)
library(RSQLite)
library(dplyr)
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
  expect_true(grepl("city \\(TEXT\\)", schema))  # Should have city column
  
  # Test query execution
  result <- execute_database_query(db_source, "SELECT * FROM users WHERE age > 30")
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 2)  # Charlie and Eve
  
  # Test get all data returns lazy dbplyr table
  all_data <- get_database_data(db_source)
  expect_s3_class(all_data, c("tbl_SQLiteConnection", "tbl_dbi", "tbl_sql", "tbl_lazy", "tbl"))
  
  # Test that it can be chained with dbplyr operations before collect()
  filtered_data <- all_data |>
    dplyr::filter(age > 30) |>
    dplyr::arrange(dplyr::desc(age)) |>
    dplyr::collect()
  
  expect_s3_class(filtered_data, "data.frame")
  expect_equal(nrow(filtered_data), 2)  # Charlie and Eve
  expect_equal(filtered_data$name, c("Charlie", "Eve"))
  
  # Test that the lazy table can be collected to get all data
  collected_data <- dplyr::collect(all_data)
  expect_s3_class(collected_data, "data.frame")
  expect_equal(nrow(collected_data), 5)
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

test_that("lazy dbplyr table behavior and chaining", {
  # Create temporary SQLite database with more complex data
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  
  # Create test table with varied data
  test_data <- data.frame(
    id = 1:10,
    name = paste0("User", 1:10),
    age = c(25, 30, 35, 28, 32, 45, 22, 38, 41, 29),
    department = rep(c("Sales", "Engineering", "Marketing"), length.out = 10),
    salary = c(50000, 75000, 85000, 60000, 80000, 120000, 45000, 90000, 110000, 65000),
    stringsAsFactors = FALSE
  )
  
  dbWriteTable(conn, "employees", test_data, overwrite = TRUE)
  
  # Create database source
  db_source <- database_source(conn, "employees")
  
  # Test that get_database_data returns a lazy table
  lazy_table <- get_database_data(db_source)
  expect_s3_class(lazy_table, c("tbl_SQLiteConnection", "tbl_dbi", "tbl_sql", "tbl_lazy", "tbl"))
  
  # Test complex chaining operations before collect()
  complex_result <- lazy_table |>
    dplyr::filter(age > 30, salary > 70000) |>
    dplyr::select(name, department, age, salary) |>
    dplyr::arrange(dplyr::desc(salary)) |>
    dplyr::mutate(senior = age > 35) |>
    dplyr::collect()
  
  expect_s3_class(complex_result, "data.frame")
  expect_true(nrow(complex_result) > 0)
  expect_true(all(complex_result$age > 30))
  expect_true(all(complex_result$salary > 70000))
  expect_true("senior" %in% names(complex_result))
  
  # Test grouping and summarizing operations
  summary_result <- lazy_table |>
    dplyr::group_by(department) |>
    dplyr::summarise(
      avg_age = mean(age, na.rm = TRUE),
      avg_salary = mean(salary, na.rm = TRUE),
      count = dplyr::n(),
      .groups = "drop"
    ) |>
    dplyr::collect()
  
  expect_s3_class(summary_result, "data.frame")
  expect_equal(nrow(summary_result), 3)  # Three departments
  expect_true(all(c("department", "avg_age", "avg_salary", "count") %in% names(summary_result)))
  
  # Test that the lazy table can be reused for different operations
  young_employees <- lazy_table |>
    dplyr::filter(age < 30) |>
    dplyr::collect()
  
  senior_employees <- lazy_table |>
    dplyr::filter(age >= 40) |>
    dplyr::collect()
  
  expect_s3_class(young_employees, "data.frame")
  expect_s3_class(senior_employees, "data.frame")
  expect_true(all(young_employees$age < 30))
  expect_true(all(senior_employees$age >= 40))
  
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