#' Data Source Base Class
#'
#' @description
#' An abstract R6 class defining the interface that custom QueryChat data
#' sources must implement. This class should not be instantiated directly;
#' instead, use one of its concrete implementations like [DataFrameSource] or
#' [DBISource].
#'
#' @export
DataSource <- R6::R6Class(
  "DataSource",
  private = list(
    colnames = NULL
  ),
  public = list(
    #' @field table_name Name of the table to be used in SQL queries
    table_name = NULL,

    #' @description
    #' Get the database type
    #'
    #' @return A string describing the database type (e.g., "DuckDB", "SQLite")
    get_db_type = function() {
      cli::cli_abort(
        "{.fn get_db_type} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },

    #' @description
    #' Get schema information about the table
    #'
    #' @param categorical_threshold Maximum number of unique values for a text
    #'   column to be considered categorical
    #' @return A string containing schema information formatted for LLM prompts
    get_schema = function(categorical_threshold = 20) {
      cli::cli_abort(
        "{.fn get_schema} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },

    #' @description
    #' Execute a SQL query and return results
    #'
    #' @param query SQL query string to execute
    #' @return A data frame containing query results
    execute_query = function(query) {
      cli::cli_abort(
        "{.fn execute_query} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },

    #' @description
    #' Test a SQL query by fetching only one row
    #'
    #' @param query SQL query string to test
    #' @param require_all_columns If TRUE, validates that the result includes
    #'   all original table columns (default: FALSE)
    #' @return A data frame containing one row of results (or empty if no matches)
    test_query = function(query, require_all_columns = FALSE) {
      cli::cli_abort(
        "{.fn test_query} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },

    #' @description
    #' Get the unfiltered data as a data frame
    #'
    #' @return A data frame containing all data from the table
    get_data = function() {
      cli::cli_abort(
        "{.fn get_data} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },

    #' @description
    #' Clean up resources (close connections, etc.)
    #'
    #' @return NULL (invisibly)
    cleanup = function() {
      cli::cli_abort(
        "{.fn cleanup} must be implemented by subclass",
        class = "not_implemented_error"
      )
    }
  )
)


#' Data Frame Source
#'
#' @description
#' A DataSource implementation that wraps a data frame using DuckDB or SQLite
#' for SQL query execution.
#'
#' @details
#' This class creates an in-memory database connection and registers the
#' provided data frame as a table. All SQL queries are executed against this
#' database table. See [DBISource] for the full description of available
#' methods.
#'
#' By default, DataFrameSource uses the first available engine from duckdb
#' (checked first) or RSQLite. You can explicitly set the `engine` parameter to
#' choose between "duckdb" or "sqlite", or set the global option
#' `querychat.DataFrameSource.engine` to choose the default engine for all
#' DataFrameSource instances. At least one of these packages must be installed.
#'
#' @export
#' @examples
#' \dontrun{
#' # Create a data frame source (uses first available: duckdb or sqlite)
#' df_source <- DataFrameSource$new(mtcars, "mtcars")
#'
#' # Get database type
#' df_source$get_db_type()  # Returns "DuckDB" or "SQLite"
#'
#' # Execute a query
#' result <- df_source$execute_query("SELECT * FROM mtcars WHERE mpg > 25")
#'
#' # Explicitly choose an engine
#' df_sqlite <- DataFrameSource$new(mtcars, "mtcars", engine = "sqlite")
#'
#' # Clean up when done
#' df_source$cleanup()
#' df_sqlite$cleanup()
#' }
DataFrameSource <- R6::R6Class(
  "DataFrameSource",
  inherit = DBISource,
  private = list(
    conn = NULL
  ),
  public = list(
    #' @description
    #' Create a new DataFrameSource
    #'
    #' @param df A data frame.
    #' @param table_name Name to use for the table in SQL queries. Must be a
    #'   valid table name (start with letter, contain only letters, numbers,
    #'   and underscores)
    #' @param engine Database engine to use: "duckdb" or "sqlite". Set the
    #'   global option `querychat.DataFrameSource.engine` to specify the default
    #'   engine for all instances. If NULL (default), uses the first available
    #'   engine from duckdb or RSQLite (in that order).
    #' @return A new DataFrameSource object
    #' @examples
    #' \dontrun{
    #' source <- DataFrameSource$new(iris, "iris")
    #' }
    initialize = function(
      df,
      table_name,
      engine = getOption("querychat.DataFrameSource.engine", NULL)
    ) {
      check_data_frame(df)
      check_sql_table_name(table_name)

      engine <- engine %||% get_default_dataframe_engine()
      engine <- tolower(engine)
      arg_match(engine, c("duckdb", "sqlite"))

      self$table_name <- table_name
      private$colnames <- colnames(df)

      # Create in-memory connection and register the data frame
      if (engine == "duckdb") {
        check_installed("duckdb")

        private$conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")

        duckdb::duckdb_register(
          private$conn,
          table_name,
          df,
          experimental = FALSE
        )

        DBI::dbExecute(
          private$conn,
          r"(
-- extensions: lock down supply chain + auto behaviors
SET allow_community_extensions = false;
SET allow_unsigned_extensions = false;
SET autoinstall_known_extensions = false;
SET autoload_known_extensions = false;

-- external I/O: block file/database/network access from SQL
SET enable_external_access = false;
SET disabled_filesystems = 'LocalFileSystem';

-- freeze configuration so user SQL can't relax anything
SET lock_configuration = true;
        )"
        )
      } else if (engine == "sqlite") {
        check_installed("RSQLite")
        private$conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
        DBI::dbWriteTable(private$conn, table_name, df)
      }
    }
  )
)


#' DBI Source
#'
#' @description
#' A DataSource implementation for DBI database connections (SQLite, PostgreSQL,
#' MySQL, etc.).
#'
#' @details
#' This class wraps a DBI connection and provides SQL query execution against
#' a specified table in the database.
#'
#' @export
#' @examples
#' \dontrun{
#' # Connect to a database
#' conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
#' DBI::dbWriteTable(conn, "mtcars", mtcars)
#'
#' # Create a DBI source
#' db_source <- DBISource$new(conn, "mtcars")
#'
#' # Get database type
#' db_source$get_db_type()  # Returns "SQLite"
#'
#' # Execute a query
#' result <- db_source$execute_query("SELECT * FROM mtcars WHERE mpg > 25")
#'
#' # Note: cleanup() will disconnect the connection
#' # If you want to keep the connection open, don't call cleanup()
#' }
DBISource <- R6::R6Class(
  "DBISource",
  inherit = DataSource,
  private = list(
    conn = NULL
  ),
  public = list(
    #' @description
    #' Create a new DBISource
    #'
    #' @param conn A DBI connection object
    #' @param table_name Name of the table in the database. Can be a character
    #'   string or a [DBI::Id()] object for tables in catalogs/schemas
    #' @return A new DBISource object
    #' @examples
    #' \dontrun{
    #' conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    #' DBI::dbWriteTable(conn, "iris", iris)
    #' source <- DBISource$new(conn, "iris")
    #' }
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
        cli::cli_abort(c(
          "Table {.val {DBI::dbQuoteIdentifier(conn, table_name)}} not found in database",
          "i" = "If you're using a table in a catalog or schema, pass a {.fn DBI::Id} object to {.arg table_name}"
        ))
      }

      private$conn <- conn
      self$table_name <- table_name

      # Store original column names for validation
      private$colnames <- colnames(DBI::dbGetQuery(
        conn,
        sprintf(
          "SELECT * FROM %s LIMIT 0",
          DBI::dbQuoteIdentifier(conn, table_name)
        )
      ))
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
      get_schema_impl(private$conn, self$table_name, categorical_threshold)
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
      DBI::dbGetQuery(private$conn, query)
    },

    #' @description
    #' Test a SQL query by fetching only one row
    #'
    #' @param query SQL query string
    #' @param require_all_columns If TRUE, validates that the result includes
    #'   all original table columns (default: FALSE)
    #' @return A data frame with one row of results
    test_query = function(query, require_all_columns = FALSE) {
      check_string(query)
      check_bool(require_all_columns)

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


# Helper Functions -------------------------------------------------------------

#' Check if object is a DataSource
#'
#' @param x Object to check
#' @return TRUE if x is a DataSource, FALSE otherwise
#' @keywords internal
is_data_source <- function(x) {
  inherits(x, "DataSource")
}


get_default_dataframe_engine <- function() {
  if (is_installed("duckdb")) {
    return("duckdb")
  }
  if (is_installed("RSQLite")) {
    return("sqlite")
  }
  cli::cli_abort(c(
    "No compatible database engine installed for DataFrameSource",
    "i" = "Install either {.pkg duckdb} or {.pkg RSQLite}:",
    " " = "{.run install.packages(\"duckdb\")}",
    " " = "{.run install.packages(\"RSQLite\")}"
  ))
}


get_schema_impl <- function(conn, table_name, categorical_threshold = 20) {
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
