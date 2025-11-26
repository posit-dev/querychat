#' Create a data source for querychat
#'
#' An entrypoint for developers to create custom data sources for use with
#' querychat. Most users shouldn't use this function directly; instead, they
#' should pass their data to `QueryChat$new()`.
#'
#' @param x A data frame or DBI connection
#' @param table_name The name to use for the table in the data source. Can be:
#'   - A character string (e.g., "table_name")
#'   - Or, for tables contained within catalogs or schemas, a [DBI::Id()] object (e.g., `DBI::Id(schema = "schema_name", table = "table_name")`)
#' @return A querychat_data_source object
#' @keywords internal
#' @export
as_querychat_data_source <- function(x, table_name = NULL, ...) {
  UseMethod("as_querychat_data_source")
}

#' @export
as_querychat_data_source.data.frame <- function(x, table_name = NULL, ...) {
  if (is.null(table_name)) {
    # Infer table name from dataframe name, if not already added
    table_name <- deparse(substitute(x))
    if (is.null(table_name) || table_name == "NULL" || table_name == "x") {
      rlang::abort(
        "Unable to infer table name. Please specify `table_name` argument explicitly."
      )
    }
  }

  is_table_name_ok <- is.character(table_name) &&
    length(table_name) == 1 &&
    grepl("^[a-zA-Z][a-zA-Z0-9_]*$", table_name, perl = TRUE)
  if (!is_table_name_ok) {
    rlang::abort(
      "`table_name` argument must be a string containing a valid table name."
    )
  }

  # Create duckdb connection
  conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
  duckdb::duckdb_register(conn, table_name, x, experimental = FALSE)

  structure(
    list(conn = conn, table_name = table_name),
    class = c("data_frame_source", "dbi_source", "querychat_data_source")
  )
}

#' @export
as_querychat_data_source.DBIConnection <- function(x, table_name, ...) {
  # Handle different types of table_name inputs
  if (inherits(table_name, "Id")) {
    # DBI::Id object - keep as is
  } else if (is.character(table_name) && length(table_name) == 1) {
    # Character string - keep as is
  } else {
    # Invalid input
    rlang::abort(
      "`table_name` must be a single character string or a DBI::Id object"
    )
  }

  # Check if table exists
  if (!DBI::dbExistsTable(x, table_name)) {
    rlang::abort(paste0(
      "Table ",
      DBI::dbQuoteIdentifier(x, table_name),
      " not found in database. If you're using a table in a catalog or schema, pass a DBI::Id",
      " object to `table_name`"
    ))
  }

  structure(
    list(conn = x, table_name = table_name),
    class = c("dbi_source", "querychat_data_source")
  )
}

is_data_source <- function(x) {
  inherits(x, "querychat_data_source")
}

#' Execute an SQL query on a data source
#'
#' An entrypoint for developers to create custom data source objects for use
#' with querychat. Most users shouldn't use this function directly; instead,
#' they call the `$sql()` method on the [QueryChat] object to run queries.
#'
#' @param source A querychat_data_source object
#' @param query SQL query string
#' @param ... Additional arguments passed to methods
#' @return Result of the query as a data frame
#' @keywords internal
#' @export
execute_query <- function(source, query, ...) {
  UseMethod("execute_query")
}

#' @export
execute_query.dbi_source <- function(source, query, ...) {
  if (is.null(query) || query == "") {
    # For a null or empty query, default to returning the whole table (ie SELECT *)
    query <- paste0(
      "SELECT * FROM ",
      DBI::dbQuoteIdentifier(source$conn, source$table_name)
    )
  }
  # Execute the query directly
  DBI::dbGetQuery(source$conn, query)
}

#' Test a SQL query on a data source.
#'
#' An entrypoint for developers to create custom data sources for use with
#' querychat. Most users shouldn't use this function directly; instead, they
#' should call the `$sql()` method on the [QueryChat] object to run queries.
#'
#' @param source A querychat_data_source object
#' @param query SQL query string
#' @param ... Additional arguments passed to methods
#' @return Result of the query, limited to one row of data.
#' @keywords internal
#' @export
test_query <- function(source, query, ...) {
  UseMethod("test_query")
}

#' @export
test_query.dbi_source <- function(source, query, ...) {
  rs <- DBI::dbSendQuery(source$conn, query)
  df <- DBI::dbFetch(rs, n = 1)
  DBI::dbClearResult(rs)
  df
}


#' Get type information for a data source
#'
#' An entrypoint for developers to create custom data sources for use with
#' querychat. Most users shouldn't use this function directly; instead, they
#' should call the `$set_system_prompt()` method on the [QueryChat] object.
#'
#' @param source A querychat_data_source object
#' @param ... Additional arguments passed to methods
#' @return A character string containing the type information
#' @keywords internal
#' @export
get_db_type <- function(source, ...) {
  UseMethod("get_db_type")
}

#' @export
get_db_type.default <- function(source, ...) {
  "standard"
}

#' @export
get_db_type.data_frame_source <- function(source, ...) {
  # Local dataframes are always duckdb!
  "DuckDB"
}

#' @export
get_db_type.dbi_source <- function(source, ...) {
  conn <- source$conn

  # Special handling for known database types
  if (inherits(conn, "duckdb_connection")) {
    return("DuckDB")
  }
  if (inherits(conn, "SQLiteConnection")) {
    return("SQLite")
  }

  # default to 'POSIX' if dbms name not found
  conn_info <- DBI::dbGetInfo(conn)
  dbms_name <- purrr::pluck(conn_info, "dbms.name", .default = "POSIX")

  # remove ' SQL', if exists (SQL is already in the prompt)
  gsub(" SQL", "", dbms_name)
}


#' Create a system prompt for the data source
#'
#' An entrypoint for developers to create custom data sources for use with
#' querychat. Most users shouldn't use this function directly; instead, they
#' should call the `$set_system_prompt()` method on the [QueryChat] object.
#'
#' @param source A querychat_data_source object
#' @param data_description Optional description of the data
#' @param extra_instructions Optional additional instructions
#' @param categorical_threshold For text columns, the maximum number of unique
#' values to consider as a categorical variable
#' @param ... Additional arguments passed to methods
#' @return A string with the system prompt
#' @keywords internal
#' @export
create_system_prompt <- function(
  source,
  data_description = NULL,
  extra_instructions = NULL,
  categorical_threshold = 20,
  ...
) {
  UseMethod("create_system_prompt")
}

#' @export
create_system_prompt.querychat_data_source <- function(
  source,
  data_description = NULL,
  extra_instructions = NULL,
  categorical_threshold = 20,
  ...
) {
  if (!is.null(data_description)) {
    data_description <- paste(data_description, collapse = "\n")
  }
  if (!is.null(extra_instructions)) {
    extra_instructions <- paste(extra_instructions, collapse = "\n")
  }

  # Read the prompt file
  prompt_path <- system.file("prompts", "prompt.md", package = "querychat")
  prompt_content <- readLines(prompt_path, warn = FALSE)
  prompt_text <- paste(prompt_content, collapse = "\n")

  # Get schema for the data source
  schema <- get_schema(source, categorical_threshold = categorical_threshold)

  # Examine the data source and get the type for the prompt
  db_type <- get_db_type(source)

  whisker::whisker.render(
    prompt_text,
    list(
      schema = schema,
      data_description = data_description,
      extra_instructions = extra_instructions,
      db_type = db_type,
      is_duck_db = identical(db_type, "DuckDB")
    )
  )
}

#' Clean up a data source (close connections, etc.)
#'
#' An entrypoint for developers to create custom data sources for use with
#' querychat. Most users shouldn't use this function directly; instead, they
#' should call the `$cleanup()` method on the [QueryChat] object.
#'
#' @param source A querychat_data_source object
#' @param ... Additional arguments passed to methods
#' @return NULL (invisibly)
#' @keywords internal
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
#' An entrypoint for developers to create custom data sources for use with
#' querychat. Most users shouldn't use this function directly; instead, they
#' should call the `$set_system_prompt()` method on the [QueryChat] object.
#'
#' @param source A querychat_data_source object
#' @param categorical_threshold For text columns, the maximum number of unique values to consider as a categorical variable
#' @param ... Additional arguments passed to methods
#' @return A character string describing the schema
#' @keywords internal
#' @export
get_schema <- function(source, categorical_threshold = 20, ...) {
  UseMethod("get_schema")
}

#' @export
get_schema.dbi_source <- function(source, categorical_threshold = 20, ...) {
  conn <- source$conn
  table_name <- source$table_name

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
