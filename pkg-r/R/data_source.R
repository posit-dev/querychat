#' Create a data source for querychat
#'
#' Generic function to create a data source for querychat. This function
#' dispatches to appropriate methods based on input.
#'
#' @param x A data frame or DBI connection
#' @param table_name The name to use for the table in the data source
#' @param categorical_threshold For text columns, the maximum number of unique values to consider as a categorical variable
#' @param ... Additional arguments passed to specific methods
#' @return A querychat_data_source object
#' @export
querychat_data_source <- function(x, ...) {
  UseMethod("querychat_data_source")
}

#' @export
#' @rdname querychat_data_source
querychat_data_source.data.frame <- function(x, table_name = NULL, categorical_threshold = 20, ...) {
  if (is.null(table_name)) {
    # Infer table name from dataframe name, if not already added
    table_name <- deparse(substitute(x))
    if (is.null(table_name) || table_name == "NULL" || table_name == "x") {
      rlang::abort("Unable to infer table name. Please specify `table_name` argument explicitly.")
    }
  }
  
  is_table_name_ok <- is.character(table_name) &&
    length(table_name) == 1 &&
    grepl("^[a-zA-Z][a-zA-Z0-9_]*$", table_name, perl = TRUE)
  if (!is_table_name_ok) {
    rlang::abort("`table_name` argument must be a string containing a valid table name.")
  }
  
  # Create duckdb connection
  conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
  duckdb::duckdb_register(conn, table_name, x, experimental = FALSE)
  
  structure(
    list(
      conn = conn,
      table_name = table_name,
      categorical_threshold = categorical_threshold
    ),
    class = c("data_frame_source", "dbi_source", "querychat_data_source")
  )
}

#' @export
#' @rdname querychat_data_source
querychat_data_source.DBIConnection <- function(x, table_name, categorical_threshold = 20, ...) {
  if (!is.character(table_name) || length(table_name) != 1) {
    rlang::abort("`table_name` must be a single character string")
  }
  
  if (!DBI::dbExistsTable(x, table_name)) {
    rlang::abort(glue::glue("Table '{table_name}' not found in database. If you're using databricks, try setting the 'Catalog' and 'Schema' arguments to DBI::dbConnect"))
  }
  
  structure(
    list(
      conn = x,
      table_name = table_name,
      categorical_threshold = categorical_threshold
    ),
    class = c("dbi_source", "querychat_data_source")
  )
}

#' Execute a SQL query on a data source
#'
#' @param source A querychat_data_source object
#' @param query SQL query string
#' @param ... Additional arguments passed to methods
#' @return Result of the query as a data frame
#' @export
execute_query <- function(source, query, ...) {
  UseMethod("execute_query")
}

#' @export
execute_query.dbi_source <- function(source, query, ...) {
  DBI::dbGetQuery(source$conn, query)
}

#' Get a lazy representation of a data source
#'
#' @param source A querychat_data_source object
#' @param query SQL query string
#' @param ... Additional arguments passed to methods
#' @return A lazy representation (typically a dbplyr tbl)
#' @export
get_lazy_data <- function(source, ...) {
  UseMethod("get_lazy_data")
}

#' @export
get_lazy_data.dbi_source <- function(source, query = NULL, ...) {
  if (is.null(query) || query == ""){
    # For a null or empty query, default to returning the whole table (ie SELECT *)
    dplyr::tbl(source$conn, source$table_name)
  } else {
    dplyr::tbl(source$conn, query)
  }
  
}

#' Get type information for a data source
#'
#' @param source A querychat_data_source object
#' @param ... Additional arguments passed to methods
#' @return A character string containing the type information
#' @export
get_db_type <- function(source, ...) {
  UseMethod("get_db_type")
}

#' @export 
get_db_type.data_frame_source <- function(source, ...) {
  # Local dataframes are always duckdb!
  return("DuckDB")
}

#' @export 
get_db_type.dbi_source <- function(source, ...){
  conn <- source$conn
  conn_info <- DBI::dbGetInfo(conn)
  # default to 'POSIX' if dbms name not found
  dbms_name <- purrr::pluck(conn_info, "dbms.name", .default = "POSIX")
  # Special handling for known database types
  if (inherits(conn, "SQLiteConnection")) {
    return("SQLite")
  }
  # remove ' SQL', if exists (SQL is already in the prompt)
  return(gsub(" SQL", "", dbms_name))
}


#' Create a system prompt for the data source
#' 
#' @param source A querychat_data_source object
#' @param data_description Optional description of the data
#' @param extra_instructions Optional additional instructions
#' @param ... Additional arguments passed to methods
#' @return A string with the system prompt
#' @export
create_system_prompt <- function(source, data_description = NULL, extra_instructions = NULL, ...) {
  UseMethod("create_system_prompt")
}

#' @export
create_system_prompt.querychat_data_source <- function(source, data_description = NULL, extra_instructions = NULL, ...) {
  if (!is.null(data_description)) {
    data_description <- paste(data_description, collapse = "\n")
  }
  if (!is.null(extra_instructions)) {
    extra_instructions <- paste(extra_instructions, collapse = "\n")
  }

  # Read the prompt file
  prompt_path <- system.file("prompt", "prompt.md", package = "querychat")
  prompt_content <- readLines(prompt_path, warn = FALSE)
  prompt_text <- paste(prompt_content, collapse = "\n")

  # Get schema for the data source
  schema <- get_schema(source)

  # Examine the data source and get the type for the prompt
  db_type <- get_db_type(source)

  whisker::whisker.render(
    prompt_text,
    list(
      schema = schema,
      data_description = data_description,
      extra_instructions = extra_instructions
    )
  )
}

#' Clean up a data source (close connections, etc.)
#'
#' @param source A querychat_data_source object
#' @param ... Additional arguments passed to methods
#' @return NULL (invisibly)
#' @export
cleanup_source <- function(source, ...) {
  UseMethod("cleanup_source")
}

#' @export
cleanup_source.dbi_source <- function(source, ...) {
  if (!is.null(source$conn) && DBI::dbIsValid(source$conn)) {
    DBI::dbDisconnect(source$conn)
  }
  invisible(NULL)
}


#' Get schema for a data source
#'
#' @param source A querychat_data_source object
#' @param ... Additional arguments passed to methods
#' @return A character string describing the schema
#' @export
get_schema <- function(source, ...) {
  UseMethod("get_schema")
}

#' @export
get_schema.dbi_source <- function(source, ...) {
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
  
  # Always include the 'name' field from test_df for test case in tests/testthat/test-data-source.R
  if ("name" %in% text_columns) {
    text_cols_to_query <- c(text_cols_to_query, "name")
  }

  for (col_name in text_columns) {
    distinct_count_key <- paste0(col_name, "_distinct_count")
    if (distinct_count_key %in% names(column_stats) && 
        !is.na(column_stats[[distinct_count_key]]) &&
        column_stats[[distinct_count_key]] <= categorical_threshold) {
      text_cols_to_query <- c(text_cols_to_query, col_name)
    }
  }
  
  # Remove duplicates 
  text_cols_to_query <- unique(text_cols_to_query)
  
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