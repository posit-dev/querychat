library(testthat)
library(DBI)
library(RSQLite)
library(dplyr)
library(querychat)

test_that("get_lazy_data returns tbl objects", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")
  lazy_data <- get_lazy_data(df_source)
  expect_s3_class(lazy_data, "tbl")

  # Test with DBI source
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")
  lazy_data <- get_lazy_data(dbi_source)
  expect_s3_class(lazy_data, "tbl")

  # Test chaining with dplyr
  filtered_data <- lazy_data %>%
    dplyr::filter(value > 25) %>%
    dplyr::collect()
  expect_equal(nrow(filtered_data), 3) # Should return 3 rows (30, 40, 50)

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("get_lazy_data works with empty query", {
  # Test with data frame source
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  df_source <- querychat_data_source(test_df, table_name = "test_table")

  # Test with NULL query
  lazy_data_null <- get_lazy_data(df_source, NULL)
  expect_s3_class(lazy_data_null, "tbl")
  result_null <- dplyr::collect(lazy_data_null)
  expect_equal(nrow(result_null), 5)

  # Test with empty string query
  lazy_data_empty <- get_lazy_data(df_source, "")
  expect_s3_class(lazy_data_empty, "tbl")
  result_empty <- dplyr::collect(lazy_data_empty)
  expect_equal(nrow(result_empty), 5)

  # Test with DBI source
  temp_db <- tempfile(fileext = ".db")
  conn <- dbConnect(RSQLite::SQLite(), temp_db)
  dbWriteTable(conn, "test_table", test_df, overwrite = TRUE)

  dbi_source <- querychat_data_source(conn, "test_table")

  # Test with NULL query
  lazy_data_null <- get_lazy_data(dbi_source, NULL)
  expect_s3_class(lazy_data_null, "tbl")
  result_null <- dplyr::collect(lazy_data_null)
  expect_equal(nrow(result_null), 5)

  # Test with empty string query
  lazy_data_empty <- get_lazy_data(dbi_source, "")
  expect_s3_class(lazy_data_empty, "tbl")
  result_empty <- dplyr::collect(lazy_data_empty)
  expect_equal(nrow(result_empty), 5)

  # Clean up
  cleanup_source(df_source)
  dbDisconnect(conn)
  unlink(temp_db)
})

test_that("get_lazy_data handles problematic SQL with clean_sql", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    value = c(10, 20, 30, 40, 50),
    stringsAsFactors = FALSE
  )

  # Create data source
  df_source <- querychat_data_source(test_df, table_name = "test_table")

  # Test with inline comments
  inline_comment_query <- "
  SELECT id, value -- This is a comment
  FROM test_table 
  WHERE value > 25 -- Filter for higher values
  "

  lazy_result <- get_lazy_data(df_source, inline_comment_query)
  expect_s3_class(lazy_result, "tbl")
  result <- dplyr::collect(lazy_result)
  expect_equal(nrow(result), 3) # Should return 3 rows (30, 40, 50)
  expect_equal(ncol(result), 2)

  # Test with multiple inline comments
  multiple_comments_query <- "
  SELECT -- Get only these columns
    id, -- ID column
    value -- Value column
  FROM test_table -- Our test table
  WHERE value > 25 -- Only higher values
  "

  lazy_result <- get_lazy_data(df_source, multiple_comments_query)
  expect_s3_class(lazy_result, "tbl")
  result <- dplyr::collect(lazy_result)
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Test with trailing semicolons
  query_with_semicolon <- "
  SELECT id, value
  FROM test_table
  WHERE value > 25;
  "

  lazy_result <- get_lazy_data(df_source, query_with_semicolon)
  expect_s3_class(lazy_result, "tbl")
  result <- dplyr::collect(lazy_result)
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Test with multiple semicolons
  query_with_multiple_semicolons <- "
  SELECT id, value
  FROM test_table
  WHERE value > 25;;;;
  "

  lazy_result <- get_lazy_data(df_source, query_with_multiple_semicolons)
  expect_s3_class(lazy_result, "tbl")
  result <- dplyr::collect(lazy_result)
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Test with multiline comments
  multiline_comment_query <- "
  /* 
   * This is a multiline comment
   * that spans multiple lines
   */
  SELECT id, value
  FROM test_table
  WHERE value > 25
  "

  lazy_result <- get_lazy_data(df_source, multiline_comment_query)
  expect_s3_class(lazy_result, "tbl")
  result <- dplyr::collect(lazy_result)
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Test with a mix of comment styles and semicolons
  complex_query <- "
  /* 
   * This is a complex query with different comment styles
   */
  SELECT 
    id, -- This is the ID column
    value /* Value column */
  FROM 
    test_table -- Our test table
  WHERE 
    /* Only get higher values */
    value > 25; -- End of query
  "

  lazy_result <- get_lazy_data(df_source, complex_query)
  expect_s3_class(lazy_result, "tbl")
  result <- dplyr::collect(lazy_result)
  expect_equal(nrow(result), 3)
  expect_equal(ncol(result), 2)

  # Clean up
  cleanup_source(df_source)
})

test_that("querychat_server has tbl output", {
  # Create a simple test dataframe
  test_df <- data.frame(
    id = 1:5,
    name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
    age = c(25, 30, 35, 28, 32),
    stringsAsFactors = FALSE
  )

  # Create a data source
  source <- querychat_data_source(test_df)

  # Create a mock current_query reactiveVal
  current_query_val <- "SELECT * FROM test_df WHERE age > 30"

  # Test that get_lazy_data works with this query directly
  lazy_result <- get_lazy_data(source, current_query_val)
  expect_s3_class(lazy_result, "tbl")

  # Collect the data from the lazy_result
  collected <- dplyr::collect(lazy_result)

  # Check that we get the expected results
  expect_equal(nrow(collected), 2) # Both Charlie and Eve are over 30
  expect_true("Charlie" %in% collected$name)
  expect_true("Eve" %in% collected$name)

  # Clean up
  cleanup_source(source)
})

test_that("get_lazy_data returns tbl that supports full dplyr verb chaining", {
  # Create a more complex test dataframe
  test_df <- data.frame(
    id = 1:10,
    name = c(
      "Alice",
      "Bob",
      "Charlie",
      "Diana",
      "Eve",
      "Frank",
      "Grace",
      "Henry",
      "Irene",
      "Jack"
    ),
    age = c(25, 30, 35, 28, 32, 40, 22, 45, 33, 27),
    department = c(
      "Sales",
      "IT",
      "HR",
      "IT",
      "Sales",
      "HR",
      "Sales",
      "IT",
      "HR",
      "Sales"
    ),
    salary = c(
      50000,
      65000,
      70000,
      62000,
      55000,
      75000,
      48000,
      80000,
      68000,
      52000
    ),
    stringsAsFactors = FALSE
  )

  # Create a data source
  source <- querychat_data_source(test_df)

  # Get a lazy tbl from the source
  lazy_tbl <- get_lazy_data(source)
  expect_s3_class(lazy_tbl, "tbl")

  # Test filter
  filtered <- lazy_tbl %>% dplyr::filter(age > 30)
  expect_s3_class(filtered, "tbl")

  # Test select
  selected <- filtered %>% dplyr::select(name, department, salary)
  expect_s3_class(selected, "tbl")

  # Test arrange
  arranged <- selected %>% dplyr::arrange(desc(salary))
  expect_s3_class(arranged, "tbl")

  # Test mutate
  mutated <- arranged %>% dplyr::mutate(bonus = salary * 0.1)
  expect_s3_class(mutated, "tbl")

  # Test group_by and summarize
  summarized <- lazy_tbl %>%
    dplyr::group_by(department) %>%
    dplyr::summarize(
      avg_age = mean(age, na.rm = TRUE),
      avg_salary = mean(salary, na.rm = TRUE),
      count = n()
    )
  expect_s3_class(summarized, "tbl")

  # Collect the results of the full chain
  result <- mutated %>% dplyr::collect()

  # Check that we got the expected results
  expect_equal(ncol(result), 4) # name, department, salary, bonus
  expect_true("bonus" %in% colnames(result))
  expect_equal(nrow(result), 5) # Five people over 30
  expect_equal(result$name[1], "Henry") # Highest salary should be first

  # Check the summarized results
  summary_result <- summarized %>% dplyr::collect()
  expect_equal(nrow(summary_result), 3) # Three departments
  expect_equal(sum(summary_result$count), 10) # Total count matches original

  # Clean up
  cleanup_source(source)
})

test_that("get_lazy_data with query supports full dplyr verb chaining", {
  # Create a test dataframe
  test_df <- data.frame(
    id = 1:10,
    name = c(
      "Alice",
      "Bob",
      "Charlie",
      "Diana",
      "Eve",
      "Frank",
      "Grace",
      "Henry",
      "Irene",
      "Jack"
    ),
    age = c(25, 30, 35, 28, 32, 40, 22, 45, 33, 27),
    department = c(
      "Sales",
      "IT",
      "HR",
      "IT",
      "Sales",
      "HR",
      "Sales",
      "IT",
      "HR",
      "Sales"
    ),
    salary = c(
      50000,
      65000,
      70000,
      62000,
      55000,
      75000,
      48000,
      80000,
      68000,
      52000
    ),
    stringsAsFactors = FALSE
  )

  # Create a data source
  source <- querychat_data_source(test_df)

  # Get a lazy tbl with a base query
  query <- "SELECT * FROM test_df WHERE department = 'IT'"
  lazy_tbl <- get_lazy_data(source, query)
  expect_s3_class(lazy_tbl, "tbl")

  # Test a complex chain of operations
  result <- lazy_tbl %>%
    dplyr::filter(age >= 30) %>%
    dplyr::select(id, name, age, salary, department) %>% # Include department for the test below
    dplyr::mutate(
      bonus = case_when(
        salary >= 70000 ~ salary * 0.15,
        salary >= 60000 ~ salary * 0.10,
        TRUE ~ salary * 0.05
      )
    ) %>%
    dplyr::arrange(desc(bonus)) %>%
    dplyr::collect()

  # Check the results
  expect_equal(nrow(result), 2) # Bob and Henry from IT, over 30
  expect_equal(ncol(result), 6) # id, name, age, salary, department, bonus
  expect_equal(result$name[1], "Henry") # Should be first with highest bonus
  expect_true(all(result$department %in% c("IT"))) # Only IT department

  # Clean up
  cleanup_source(source)
})

test_that("get_lazy_data handles complex SQL queries with dplyr chaining", {
  # Create test dataframe
  test_df <- data.frame(
    id = 1:10,
    name = c(
      "Alice",
      "Bob",
      "Charlie",
      "Diana",
      "Eve",
      "Frank",
      "Grace",
      "Henry",
      "Irene",
      "Jack"
    ),
    age = c(25, 30, 35, 28, 32, 40, 22, 45, 33, 27),
    department = c(
      "Sales",
      "IT",
      "HR",
      "IT",
      "Sales",
      "HR",
      "Sales",
      "IT",
      "HR",
      "Sales"
    ),
    salary = c(
      50000,
      65000,
      70000,
      62000,
      55000,
      75000,
      48000,
      80000,
      68000,
      52000
    ),
    stringsAsFactors = FALSE
  )

  # Create a data source
  source <- querychat_data_source(test_df)

  # Complex query with comments, subqueries, and functions
  complex_query <- "
  /* This is a complex query with subqueries and functions */
  SELECT 
    id, 
    name, 
    age, 
    department,
    salary, -- original salary
    ROUND(salary * 1.05) AS projected_salary -- with 5% increase
  FROM test_df
  WHERE 
    age > (SELECT AVG(age) FROM test_df) -- only above average age
    AND department IN ('IT', 'HR') -- only certain departments
  ORDER BY salary DESC; -- sort by salary
  "

  # Get lazy tbl with complex query
  lazy_tbl <- get_lazy_data(source, complex_query)
  expect_s3_class(lazy_tbl, "tbl")

  # Chain dplyr operations
  result <- lazy_tbl %>%
    dplyr::filter(projected_salary > 70000) %>%
    dplyr::mutate(bonus_eligible = projected_salary > 75000) %>%
    dplyr::select(name, department, projected_salary, bonus_eligible) %>%
    dplyr::collect()

  # Check results
  expect_s3_class(result, "data.frame")
  expect_true(all(result$projected_salary > 70000))
  expect_true("bonus_eligible" %in% colnames(result))
  expect_true(all(result$department %in% c("IT", "HR")))

  # Clean up
  cleanup_source(source)
})
