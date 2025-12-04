# Test fixture constructors for data source tests

# Simple data frame with id, name, and value columns
new_test_df <- function(rows = 5) {
  data.frame(
    id = seq_len(rows),
    name = c("A", "B", "C", "D", "E")[seq_len(rows)],
    value = c(10, 20, 30, 40, 50)[seq_len(rows)],
    stringsAsFactors = FALSE
  )
}

# Data frame with multiple numeric columns for testing min/max ranges
new_metrics_df <- function() {
  data.frame(
    id = 1:5,
    score = c(10.5, 20.3, 15.7, 30.1, 25.9),
    count = c(100, 200, 150, 50, 75),
    stringsAsFactors = FALSE
  )
}

# Data frame with mixed types including boolean
new_mixed_types_df <- function() {
  data.frame(
    id = 1:5,
    name = c("A", "B", "C", "D", "E"),
    active = c(TRUE, FALSE, TRUE, TRUE, FALSE),
    stringsAsFactors = FALSE
  )
}

# Data frame for testing user data
new_users_df <- function() {
  data.frame(
    id = 1:5,
    name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
    age = c(25, 30, 35, 28, 32),
    stringsAsFactors = FALSE
  )
}

# Data frame with all data types for type testing
new_types_df <- function() {
  data.frame(
    id = 1:3,
    text_col = c("text1", "text2", "text3"),
    num_col = c(1.1, 2.2, 3.3),
    int_col = c(10L, 20L, 30L),
    bool_col = c(TRUE, FALSE, TRUE),
    stringsAsFactors = FALSE
  )
}

# Create a temporary SQLite connection with a test table
local_sqlite_connection <- function(
  data = new_test_df(),
  table_name = "test_table",
  env = parent.frame()
) {
  temp_db <- withr::local_tempfile(fileext = ".db", .local_envir = env)
  conn <- DBI::dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(DBI::dbDisconnect(conn), envir = env)

  DBI::dbWriteTable(conn, table_name, data, overwrite = TRUE)

  list(conn = conn, path = temp_db)
}

# Create a DataFrameSource with automatic cleanup
local_data_frame_source <- function(
  data,
  table_name = "test_table",
  env = parent.frame()
) {
  df_source <- DataFrameSource$new(data, table_name)
  withr::defer(df_source$cleanup(), envir = env)
  df_source
}
