#' Database Data Source for querychat
#'
#' Create a data source that connects to external databases via DBI.
#' Supports PostgreSQL, MySQL, SQLite, and other DBI-compatible databases.
#'
#' @param conn A DBI connection object to the database
#' @param table_name Name of the table to query
#' @param categorical_threshold Maximum number of unique values for a text column 
#'   to be considered categorical (default: 20)
#'
#' @return A database data source object
#' @export
#' @examples
#' \dontrun{
#' # PostgreSQL example
#' library(RPostgreSQL)
#' conn <- DBI::dbConnect(RPostgreSQL::PostgreSQL(),
#'                        dbname = "mydb", host = "localhost", 
#'                        user = "user", password = "pass")
#' db_source <- database_source(conn, "my_table")
#' 
#' # SQLite example  
#' library(RSQLite)
#' conn <- DBI::dbConnect(RSQLite::SQLite(), "path/to/database.db")
#' db_source <- database_source(conn, "my_table")
#' }
database_source <- function(conn, table_name, categorical_threshold = 20) {
  if (!inherits(conn, "DBIConnection")) {
    rlang::abort("`conn` must be a valid DBI connection object")
  }
  
  if (!is.character(table_name) || length(table_name) != 1) {
    rlang::abort("`table_name` must be a single character string")
  }
  
  if (!DBI::dbExistsTable(conn, table_name)) {
    rlang::abort(glue::glue("Table '{table_name}' not found in database. If you're using databricks, try setting the 'Catalog' and 'Schema' arguments to DBI::dbConnect"))
  }
  
  structure(
    list(
      conn = conn,
      table_name = table_name,
      categorical_threshold = categorical_threshold,
      db_engine = "DBI"
    ),
    class = "database_source"
  )
}

#' Generate schema information for database source
#'
#' @param source A database_source object
#' @return A character string describing the schema
#' @export
get_database_schema <- function(source) {
  if (!inherits(source, "database_source")) {
    rlang::abort("`source` must be a database_source object")
  }
  
  conn <- source$conn
  table_name <- source$table_name
  categorical_threshold <- source$categorical_threshold
  
  # Get column information
  columns <- DBI::dbListFields(conn, table_name)
  
  schema_lines <- c(
    glue::glue("Table: {table_name}"),
    "Columns:"
  )
  
  # Build single query to get column statistics
  select_parts <- character(0)
  numeric_columns <- character(0)
  text_columns <- character(0)
  
  # Get sample of data to determine types
  sample_query <- glue::glue_sql("SELECT * FROM {`table_name`} LIMIT 1", .con = conn)
  sample_data <- DBI::dbGetQuery(conn, sample_query)
  
  for (col in columns) {
    col_class <- class(sample_data[[col]])[1]
    
    if (col_class %in% c("integer", "numeric", "double", "Date", "POSIXct", "POSIXt")) {
      numeric_columns <- c(numeric_columns, col)
      select_parts <- c(
        select_parts,
        glue::glue_sql("MIN({`col`}) as {`col`}_min", .con = conn),
        glue::glue_sql("MAX({`col`}) as {`col`}_max", .con = conn)
      )
    } else if (col_class %in% c("character", "factor")) {
      text_columns <- c(text_columns, col)
      select_parts <- c(
        select_parts, 
        glue::glue_sql("COUNT(DISTINCT {`col`}) as {`col`}_distinct_count", .con = conn)
      )
    }
  }
  
  # Execute statistics query
  column_stats <- list()
  if (length(select_parts) > 0) {
    tryCatch({
      stats_query <- glue::glue_sql("SELECT {select_parts*} FROM {`table_name`}", .con = conn)
      result <- DBI::dbGetQuery(conn, stats_query)
      if (nrow(result) > 0) {
        column_stats <- as.list(result[1, ])
      }
    }, error = function(e) {
      # Fall back to no statistics if query fails
    })
  }
  
  # Get categorical values for text columns below threshold
  categorical_values <- list()
  text_cols_to_query <- character(0)
  
  for (col_name in text_columns) {
    distinct_count_key <- paste0(col_name, "_distinct_count")
    if (distinct_count_key %in% names(column_stats) && 
        !is.na(column_stats[[distinct_count_key]]) &&
        column_stats[[distinct_count_key]] <= categorical_threshold) {
      text_cols_to_query <- c(text_cols_to_query, col_name)
    }
  }
  
  # Get categorical values
  if (length(text_cols_to_query) > 0) {
    for (col_name in text_cols_to_query) {
      tryCatch({
        cat_query <- glue::glue_sql(
          "SELECT DISTINCT {`col_name`} FROM {`table_name`} WHERE {`col_name`} IS NOT NULL ORDER BY {`col_name`}",
          .con = conn
        )
        result <- DBI::dbGetQuery(conn, cat_query)
        if (nrow(result) > 0) {
          categorical_values[[col_name]] <- result[[1]]
        }
      }, error = function(e) {
        # Skip categorical values if query fails
      })
    }
  }
  
  # Build schema description
  for (col in columns) {
    col_class <- class(sample_data[[col]])[1]
    sql_type <- r_class_to_sql_type(col_class)
    
    column_info <- glue::glue("- {col} ({sql_type})")
    
    # Add range info for numeric columns
    if (col %in% numeric_columns) {
      min_key <- paste0(col, "_min")
      max_key <- paste0(col, "_max")
      if (min_key %in% names(column_stats) && max_key %in% names(column_stats) &&
          !is.na(column_stats[[min_key]]) && !is.na(column_stats[[max_key]])) {
        range_info <- glue::glue("  Range: {column_stats[[min_key]]} to {column_stats[[max_key]]}")
        column_info <- paste(column_info, range_info, sep = "\n")
      }
    }
    
    # Add categorical values for text columns
    if (col %in% names(categorical_values)) {
      values <- categorical_values[[col]]
      if (length(values) > 0) {
        values_str <- paste0("'", values, "'", collapse = ", ")
        cat_info <- glue::glue("  Categorical values: {values_str}")
        column_info <- paste(column_info, cat_info, sep = "\n")
      }
    }
    
    schema_lines <- c(schema_lines, column_info)
  }
  
  paste(schema_lines, collapse = "\n")
}

#' Execute SQL query on database source
#'
#' @param source A database_source object  
#' @param query SQL query to execute
#' @return A data frame with query results
#' @export
execute_database_query <- function(source, query) {
  if (!inherits(source, "database_source")) {
    rlang::abort("`source` must be a database_source object")
  }
  
  DBI::dbGetQuery(source$conn, query)
}

#' Get lazy database table reference
#'
#' @param source A database_source object
#' @return A lazy dbplyr tbl object that can be further manipulated with dplyr verbs
#' @export  
get_database_data <- function(source) {
  if (!inherits(source, "database_source")) {
    rlang::abort("`source` must be a database_source object")
  }
  
  # Return a lazy tbl that can be chained with further dplyr operations
  dplyr::tbl(source$conn, source$table_name)
}

# Helper function to map R classes to SQL types
r_class_to_sql_type <- function(r_class) {
  switch(r_class,
    "integer" = "INTEGER",
    "numeric" = "FLOAT", 
    "double" = "FLOAT",
    "logical" = "BOOLEAN",
    "Date" = "DATE",
    "POSIXct" = "TIMESTAMP",
    "POSIXt" = "TIMESTAMP",
    "character" = "TEXT",
    "factor" = "TEXT",
    "TEXT" # default
  )
}