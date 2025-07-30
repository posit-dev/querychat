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
get_db_type.dbi_source <- function(source, ...) {
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
create_system_prompt <- function(
  source,
  data_description = NULL,
  extra_instructions = NULL,
  ...
) {
  UseMethod("create_system_prompt")
}

#' @export
create_system_prompt.querychat_data_source <- function(
  source,
  data_description = NULL,
  extra_instructions = NULL,
  ...
) {
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
      extra_instructions = extra_instructions,
      db_type = db_type
    )
  )
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
    paste("Table:", DBI::dbQuoteIdentifier(conn, table_name)),
    "Columns:"
  )

  # Build single query to get column statistics
  select_parts <- character(0)
  numeric_columns <- character(0)
  text_columns <- character(0)

  # Get sample of data to determine types
  sample_query <- paste0(
    "SELECT * FROM ",
    DBI::dbQuoteIdentifier(conn, table_name),
    " LIMIT 1"
  )
  sample_data <- DBI::dbGetQuery(conn, sample_query)

  for (col in columns) {
    col_class <- class(sample_data[[col]])[1]

    if (
      col_class %in%
        c("integer", "numeric", "double", "Date", "POSIXct", "POSIXt")
    ) {
      numeric_columns <- c(numeric_columns, col)
      select_parts <- c(
        select_parts,
        paste0(
          "MIN(",
          DBI::dbQuoteIdentifier(conn, col),
          ") as ",
          DBI::dbQuoteIdentifier(conn, paste0(col, '__min'))
        ),
        paste0(
          "MAX(",
          DBI::dbQuoteIdentifier(conn, col),
          ") as ",
          DBI::dbQuoteIdentifier(conn, paste0(col, '__max'))
        )
      )
    } else if (col_class %in% c("character", "factor")) {
      text_columns <- c(text_columns, col)
      select_parts <- c(
        select_parts,
        paste0(
          "COUNT(DISTINCT ",
          DBI::dbQuoteIdentifier(conn, col),
          ") as ",
          DBI::dbQuoteIdentifier(conn, paste0(col, '__distinct_count'))
        )
      )
    }
  }

  # Execute statistics query
  column_stats <- list()
  if (length(select_parts) > 0) {
    tryCatch(
      {
        stats_query <- paste0(
          "SELECT ",
          paste0(select_parts, collapse = ", "),
          " FROM ",
          DBI::dbQuoteIdentifier(conn, table_name)
        )
        result <- DBI::dbGetQuery(conn, stats_query)
        if (nrow(result) > 0) {
          column_stats <- as.list(result[1, ])
        }
      },
      error = function(e) {
        # Fall back to no statistics if query fails
      }
    )
  }

  # Get categorical values for text columns below threshold
  categorical_values <- list()
  text_cols_to_query <- character(0)

  for (col_name in text_columns) {
    distinct_count_key <- paste0(col_name, "__distinct_count")
    if (
      distinct_count_key %in%
        names(column_stats) &&
        !is.na(column_stats[[distinct_count_key]]) &&
        column_stats[[distinct_count_key]] <= categorical_threshold
    ) {
      text_cols_to_query <- c(text_cols_to_query, col_name)
    }
  }

  # Remove duplicates
  text_cols_to_query <- unique(text_cols_to_query)

  # Get categorical values
  if (length(text_cols_to_query) > 0) {
    for (col_name in text_cols_to_query) {
      tryCatch(
        {
          cat_query <- paste0(
            "SELECT DISTINCT ",
            DBI::dbQuoteIdentifier(conn, col_name),
            " FROM ",
            DBI::dbQuoteIdentifier(conn, table_name),
            " WHERE ",
            DBI::dbQuoteIdentifier(conn, col_name),
            " IS NOT NULL ORDER BY ",
            DBI::dbQuoteIdentifier(conn, col_name)
          )
          result <- DBI::dbGetQuery(conn, cat_query)
          if (nrow(result) > 0) {
            categorical_values[[col_name]] <- result[[1]]
          }
        },
        error = function(e) {
          # Skip categorical values if query fails
        }
      )
    }
  }

  # Build schema description
  for (col in columns) {
    col_class <- class(sample_data[[col]])[1]
    sql_type <- r_class_to_sql_type(col_class)

    column_info <- paste0("- ", col, " (", sql_type, ")")

    # Add range info for numeric columns
    if (col %in% numeric_columns) {
      min_key <- paste0(col, "__min")
      max_key <- paste0(col, "__max")
      if (
        min_key %in%
          names(column_stats) &&
          max_key %in% names(column_stats) &&
          !is.na(column_stats[[min_key]]) &&
          !is.na(column_stats[[max_key]])
      ) {
        range_info <- paste0(
          "  Range: ",
          column_stats[[min_key]],
          " to ",
          column_stats[[max_key]]
        )
        column_info <- paste(column_info, range_info, sep = "\n")
      }
    }

    # Add categorical values for text columns
    if (col %in% names(categorical_values)) {
      values <- categorical_values[[col]]
      if (length(values) > 0) {
        values_str <- paste0("'", values, "'", collapse = ", ")
        cat_info <- paste0("  Categorical values: ", values_str)
        column_info <- paste(column_info, cat_info, sep = "\n")
      }
    }

    schema_lines <- c(schema_lines, column_info)
  }

  paste(schema_lines, collapse = "\n")
}


# Helper function to map R classes to SQL types
r_class_to_sql_type <- function(r_class) {
  switch(
    r_class,
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
