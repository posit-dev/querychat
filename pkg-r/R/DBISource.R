#' DBI Source
#'
#' A DataSource implementation for DBI database connections (SQLite, PostgreSQL,
#' MySQL, etc.). This class wraps a DBI connection and provides SQL query
#' execution against a single table in the database.
#'
#' @examplesIf rlang::is_installed("RSQLite")
#' # Connect to a database
#' con <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
#' DBI::dbWriteTable(con, "mtcars", mtcars)
#'
#' # Create a DBI source
#' db_source <- DBISource$new(con, "mtcars")
#'
#' # Get database type
#' db_source$get_db_type()  # Returns "SQLite"
#'
#' # Execute a query
#' result <- db_source$execute_query("SELECT * FROM mtcars WHERE mpg > 25")
#'
#' # Note: cleanup() will disconnect the connection
#' # If you want to keep the connection open, don't call cleanup()
#' db_source$cleanup()
#'
#' @export
DBISource <- R6::R6Class(
  "DBISource",
  inherit = DataSource,
  private = list(
    conn = NULL,
    semantic_views = NULL
  ),
  public = list(
    #' @description
    #' Create a new DBISource
    #'
    #' @param conn A DBI connection object
    #' @param table_name Name of the table in the database. Can be a character
    #'   string or a [DBI::Id()] object for tables in catalogs/schemas
    #'
    #' @return A new DBISource object
    initialize = function(conn, table_name) {
      if (!inherits(conn, "DBIConnection")) {
        cli::cli_abort(
          "{.arg conn} must be a {.cls DBIConnection}, not {.obj_type_friendly {conn}}"
        )
      }

      # Validate table_name type
      if (inherits(table_name, "Id")) {
        # DBI::Id object - keep as is
      } else if (is.character(table_name) && length(table_name) == 1) {
        # Character string - keep as is
      } else {
        cli::cli_abort(
          "{.arg table_name} must be a single character string or a {.fn DBI::Id} object"
        )
      }

      # Check if table exists
      if (!DBI::dbExistsTable(conn, table_name)) {
        cli::cli_abort(
          c(
            "Table {.val {DBI::dbQuoteIdentifier(conn, table_name)}} not found in database",
            "i" = "If you're using a table in a catalog or schema, pass a {.fn DBI::Id} object to {.arg table_name}"
          )
        )
      }

      private$conn <- conn
      self$table_name <- table_name

      # Store original column names for validation
      private$colnames <- colnames(
        DBI::dbGetQuery(
          conn,
          sprintf(
            "SELECT * FROM %s LIMIT 0",
            DBI::dbQuoteIdentifier(conn, table_name)
          )
        )
      )
    },

    #' @description Get the database type
    #' @return A string identifying the database type
    get_db_type = function() {
      # Special handling for known database types
      if (inherits(private$conn, "duckdb_connection")) {
        return("DuckDB")
      }
      if (inherits(private$conn, "SQLiteConnection")) {
        return("SQLite")
      }

      # Default to 'POSIX' if dbms name not found
      conn_info <- DBI::dbGetInfo(private$conn)
      dbms_name <- getElement(conn_info, "dbms.name") %||% "POSIX"

      # Remove ' SQL', if exists (SQL is already in the prompt)
      gsub(" SQL", "", dbms_name)
    },

    #' @description
    #' Get schema information for the database table
    #'
    #' @param categorical_threshold Maximum number of unique values for a text
    #'   column to be considered categorical (default: 20)
    #' @return A string describing the schema
    get_schema = function(categorical_threshold = 20) {
      check_number_whole(categorical_threshold, min = 1)
      get_schema_impl(
        private$conn,
        self$table_name,
        categorical_threshold
      )
    },

    #' @description
    #' Get formatted DDL content for semantic views
    #' @return A string with DDL definitions, or empty string if none
    get_semantic_view_ddls = function() {
      # Discover Snowflake semantic views lazily (only on first call)
      if (is.null(private$semantic_views)) {
        if (is_snowflake_connection(private$conn)) {
          private$semantic_views <- discover_semantic_views_impl(private$conn)
        } else {
          private$semantic_views <- list()
        }
      }
      if (length(private$semantic_views) == 0) {
        return("")
      }
      format_semantic_view_ddls(private$semantic_views)
    },

    #' @description
    #' Execute a SQL query
    #'
    #' @param query SQL query string. If NULL or empty, returns all data
    #' @return A data frame with query results
    execute_query = function(query) {
      check_string(query, allow_null = TRUE, allow_empty = TRUE)
      if (is.null(query) || !nzchar(query)) {
        query <- paste0(
          "SELECT * FROM ",
          DBI::dbQuoteIdentifier(private$conn, self$table_name)
        )
      }

      check_query(query)
      DBI::dbGetQuery(private$conn, query)
    },

    #' @description
    #' Test a SQL query by fetching only one row
    #'
    #' @param query SQL query string
    #' @param require_all_columns If `TRUE`, validates that the result includes
    #'   all original table columns (default: `FALSE`)
    #' @return A data frame with one row of results
    test_query = function(query, require_all_columns = FALSE) {
      check_string(query)
      check_bool(require_all_columns)
      check_query(query)

      rs <- DBI::dbSendQuery(private$conn, query)
      df <- DBI::dbFetch(rs, n = 1)
      DBI::dbClearResult(rs)

      if (require_all_columns) {
        result_columns <- names(df)
        missing_columns <- setdiff(private$colnames, result_columns)

        if (length(missing_columns) > 0) {
          missing_list <- paste0("'", missing_columns, "'", collapse = ", ")
          cli::cli_abort(
            c(
              "Query result missing required columns: {missing_list}",
              "i" = "The query must return all original table columns (in any order)."
            ),
            class = "querychat_missing_columns_error"
          )
        }
      }

      df
    },

    #' @description
    #' Get all data from the table
    #'
    #' @return A data frame containing all data
    get_data = function() {
      self$execute_query(NULL)
    },

    #' @description
    #' Disconnect from the database
    #'
    #' @return NULL (invisibly)
    cleanup = function() {
      if (!is.null(private$conn) && DBI::dbIsValid(private$conn)) {
        DBI::dbDisconnect(private$conn)
      }
      invisible(NULL)
    }
  )
)

get_schema_impl <- function(
  conn,
  table_name,
  categorical_threshold = 20,
  columns = NULL,
  prep_query = identity
) {
  check_function(prep_query)

  # Get column information
  columns <- columns %||% DBI::dbListFields(conn, table_name)

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
  sample_data <- DBI::dbGetQuery(conn, prep_query(sample_query))

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
        result <- DBI::dbGetQuery(conn, prep_query(stats_query))
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
          result <- DBI::dbGetQuery(conn, prep_query(cat_query))
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

# nocov start
# Map R classes to SQL types
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
# nocov end

# Snowflake Semantic Views Support ----

#' Check if a connection is a Snowflake connection
#'
#' @param conn A DBI connection object
#' @return TRUE if the connection is to Snowflake
#' @noRd
is_snowflake_connection <- function(conn) {
  if (!inherits(conn, "DBIConnection")) {
    return(FALSE)
  }

  # Check for known Snowflake connection classes
  if (inherits(conn, "Snowflake")) {
    return(TRUE)
  }

  # Check dbms.name from connection info
  tryCatch(
    {
      conn_info <- DBI::dbGetInfo(conn)
      dbms_name <- tolower(conn_info[["dbms.name"]] %||% "")
      grepl("snowflake", dbms_name, ignore.case = TRUE)
    },
    error = function(e) FALSE
  )
}

#' Discover Semantic Views in Snowflake
#'
#' @param conn A DBI connection to Snowflake
#' @return A list of semantic views with name and ddl
#' @noRd
discover_semantic_views_impl <- function(conn) {
  # Check env var for early exit
  if (nzchar(Sys.getenv("QUERYCHAT_DISABLE_SEMANTIC_VIEWS", ""))) {
    return(list())
  }

  semantic_views <- list()

  # Check for semantic views in the current schema
  result <- DBI::dbGetQuery(conn, "SHOW SEMANTIC VIEWS")

  if (nrow(result) == 0) {
    cli::cli_inform(
      c("i" = "No semantic views found in current schema"),
      .frequency = "once",
      .frequency_id = "querychat_no_semantic_views"
    )
    return(list())
  }

  for (i in seq_len(nrow(result))) {
    row <- result[i, ]
    view_name <- row[["name"]]
    database_name <- row[["database_name"]]
    schema_name <- row[["schema_name"]]

    if (is.null(view_name) || is.na(view_name)) {
      next
    }

    # Build fully qualified name
    fq_name <- paste(database_name, schema_name, view_name, sep = ".")

    # Get the DDL for this semantic view
    ddl <- get_semantic_view_ddl(conn, fq_name)
    if (!is.null(ddl)) {
      semantic_views <- c(
        semantic_views,
        list(
          list(
            name = fq_name,
            ddl = ddl
          )
        )
      )
    }
  }

  semantic_views
}

#' Get the DDL for a Semantic View
#'
#' @param conn A DBI connection to Snowflake
#' @param fq_name Fully qualified name (database.schema.view_name)
#' @return The DDL text, or NULL if retrieval failed
#' @noRd
get_semantic_view_ddl <- function(conn, fq_name) {
  # Escape single quotes to prevent SQL injection
  safe_name <- gsub("'", "''", fq_name, fixed = TRUE)
  query <- sprintf("SELECT GET_DDL('SEMANTIC_VIEW', '%s')", safe_name)
  result <- DBI::dbGetQuery(conn, query)
  if (nrow(result) > 0 && ncol(result) > 0) {
    as.character(result[[1, 1]])
  } else {
    NULL
  }
}

#' Format Semantic View DDLs
#'
#' @param semantic_views A list of semantic view info (name and ddl)
#' @return A formatted string with just the DDL definitions
#' @noRd
format_semantic_view_ddls <- function(semantic_views) {
  lines <- character(0)

  for (sv in semantic_views) {
    lines <- c(
      lines,
      sprintf("### Semantic View: `%s`", sv$name),
      "",
      "```sql",
      sv$ddl,
      "```",
      ""
    )
  }

  paste(lines, collapse = "\n")
}
