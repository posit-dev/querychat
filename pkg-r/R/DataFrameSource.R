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
#' choose between `"duckdb"` or `"sqlite"`, or set the global option
#' `querychat.DataFrameSource.engine` to choose the default engine for all
#' DataFrameSource instances. At least one of these packages must be installed.
#'
#' @examplesIf rlang::is_installed("duckdb") || rlang::is_installed("RSQLite")
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
#'
#' @export
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
    #'
    #' @return A new DataFrameSource object
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
