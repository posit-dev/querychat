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

# Helper Functions -------------------------------------------------------------

#' Check if object is a DataSource
#'
#' @param x Object to check
#' @return TRUE if x is a DataSource, FALSE otherwise
#' @keywords internal
is_data_source <- function(x) {
  inherits(x, "DataSource")
}
