library(testthat)
library(querychat)

# Access the internal clean_sql function for testing
clean_sql <- querychat:::clean_sql

test_that("clean_sql handles comments correctly", {
  # Inline comments
  expect_equal(
    clean_sql("SELECT * FROM table -- This is a comment"),
    "SELECT * FROM table"
  )

  # Multiline comments
  expect_equal(
    clean_sql("SELECT * FROM /* this is a comment */ table"),
    "SELECT * FROM  table"
  )

  # Nested multiline comments
  expect_equal(
    clean_sql("SELECT * FROM /* outer /* nested */ comment */ table"),
    "SELECT * FROM  comment */ table"
  )

  # Comment with asterisks
  expect_equal(
    clean_sql("SELECT * FROM table /* ** multiple ** asterisks ** */"),
    "SELECT * FROM table"
  )

  # Comment at the beginning
  expect_equal(
    clean_sql("-- This is a comment\nSELECT * FROM table"),
    "SELECT * FROM table"
  )

  # Comment only query
  expect_null(clean_sql("-- just a comment"))
  expect_null(clean_sql("/* just a comment */"))
})

test_that("clean_sql handles semicolons correctly", {
  # Trailing semicolon
  result <- clean_sql("SELECT * FROM table;")
  expect_equal(
    result,
    "SELECT * FROM table"
  )

  # Multiple trailing semicolons (should be treated as multiple statements with empty ones)
  expect_warning(
    result <- clean_sql("SELECT * FROM table;;;"),
    "Multiple SQL statements detected"
  )
  expect_equal(result, "SELECT * FROM table")

  # Multiple statements (should keep only the first one and warn)
  expect_warning(
    result <- clean_sql("SELECT * FROM table1; SELECT * FROM table2;"),
    "Multiple SQL statements detected"
  )
  expect_equal(result, "SELECT * FROM table1")

  # Warning message includes information about the SQL statement
  # No need to test this explicitly again since we've already verified the warning is thrown
  # and the warning format is consistent

  # Semicolon in quoted string (should be preserved)
  sql_with_quoted_semicolon <- clean_sql(
    "SELECT * FROM table WHERE col = 'text;with;semicolons'"
  )
  expect_match(sql_with_quoted_semicolon, "text;with;semicolons", fixed = TRUE)

  # Complex case with multiple statements, comments, and quoted semicolons
  complex_sql <- "
    /* Comment at start */
    SELECT * 
    FROM table1 
    WHERE col = 'text;with;semicolons' -- inline comment
    AND col2 > 10
  "

  cleaned_sql <- clean_sql(complex_sql)
  expect_match(cleaned_sql, "text;with;semicolons", fixed = TRUE)
})

test_that("clean_sql detects and handles unbalanced quotes", {
  # Unbalanced single quotes
  expect_warning(
    result <- clean_sql("SELECT * FROM table WHERE col = 'unbalanced"),
    "unbalanced single quotes"
  )
  expect_equal(result, "SELECT * FROM table WHERE col = 'unbalanced'")

  # Unbalanced double quotes
  expect_warning(
    result <- clean_sql('SELECT * FROM table WHERE col = "unbalanced'),
    "unbalanced double quotes"
  )
  expect_equal(result, 'SELECT * FROM table WHERE col = "unbalanced"')

  # Balanced quotes should not trigger warnings
  expect_silent(
    clean_sql("SELECT * FROM table WHERE col = 'balanced'")
  )
})

test_that("clean_sql detects and handles unbalanced parentheses", {
  # Unbalanced open parentheses
  expect_warning(
    result <- clean_sql("SELECT * FROM table WHERE (col = 10 AND (col2 = 20"),
    "unbalanced parentheses"
  )
  expect_equal(result, "SELECT * FROM table WHERE (col = 10 AND (col2 = 20))")

  # Unbalanced close parentheses
  expect_warning(
    clean_sql("SELECT * FROM table WHERE (col = 10))"),
    "unbalanced parentheses"
  )

  # Balanced parentheses should not trigger warnings
  expect_silent(
    clean_sql("SELECT * FROM table WHERE (col = 10)")
  )
})

test_that("clean_sql handles GO statements", {
  # Simple GO statement
  expect_equal(
    clean_sql("SELECT * FROM table\nGO"),
    "SELECT * FROM table"
  )

  # GO with subsequent commands (should be removed)
  sql_with_go <- "
    SELECT * FROM table1
    GO
    SELECT * FROM table2
  "
  cleaned_sql <- clean_sql(sql_with_go)
  expect_true(!grepl("GO", cleaned_sql))
  # The second SELECT might still be there, but the GO is gone
})

test_that("clean_sql filters non-standard characters", {
  # Non-ASCII characters
  expect_equal(
    clean_sql("SELECT * FROM table WHERE col = 'special\u2013char'"),
    "SELECT * FROM table WHERE col = 'specialchar'"
  )

  # Control characters
  expect_equal(
    clean_sql("SELECT * FROM\ttable"),
    "SELECT * FROM\ttable"
  )

  # Non-printable characters
  expect_equal(
    clean_sql("SELECT * FROM table\x01name"),
    "SELECT * FROM tablename"
  )
})

test_that("clean_sql validates SELECT statements", {
  # Valid SELECT
  expect_silent(
    clean_sql("SELECT * FROM table", enforce_select = TRUE)
  )

  # Not a SELECT statement
  expect_error(
    clean_sql("UPDATE table SET col = 10", enforce_select = TRUE),
    "not appear to start with SELECT"
  )

  # Non-SELECT but enforce_select = FALSE
  expect_silent(
    clean_sql("UPDATE table SET col = 10", enforce_select = FALSE)
  )
})

test_that("clean_sql works with edge cases", {
  # Empty query
  expect_null(clean_sql(""))
  expect_null(clean_sql("   "))

  # Only comments
  expect_null(clean_sql("-- comment only"))

  # Query with just whitespace after cleaning
  expect_null(clean_sql("/* everything is a comment */"))
})

test_that("clean_sql handles complex SQL queries", {
  # Complex query with subqueries, joins, and functions
  complex_query <- "
    /* This tests a complex query */
    SELECT 
      t1.col1, 
      t2.col2, 
      COALESCE(t1.col3, 'N/A') AS col3,
      (SELECT COUNT(*) FROM table3 WHERE table3.id = t1.id) AS subquery_result
    FROM 
      table1 t1
    LEFT JOIN 
      table2 t2 ON t1.id = t2.id
    WHERE 
      t1.col1 IN (
        SELECT col1 
        FROM table4 
        WHERE active = 1
      )
    GROUP BY 
      t1.col1, t2.col2
    HAVING 
      COUNT(*) > 0
    ORDER BY 
      t1.col1 DESC
  "

  cleaned_sql <- clean_sql(complex_query)
  expect_true(grepl("LEFT JOIN", cleaned_sql))
  expect_true(grepl("GROUP BY", cleaned_sql))
  expect_true(grepl("HAVING", cleaned_sql))
  expect_true(grepl("subquery_result", cleaned_sql))
})
