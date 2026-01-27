#' Data Source: SQL Tibble
#'
#' @description
#' A DataSource implementation for lazy SQL tibbles connected to databases via
#' [dbplyr::tbl_sql()] or [dplyr::sql()].
#'
#' @examplesIf rlang::is_installed("dbplyr") && rlang::is_installed("dplyr") && rlang::is_installed("duckdb")
#' con <- DBI::dbConnect(duckdb::duckdb())
#' DBI::dbWriteTable(con, "mtcars", mtcars)
#'
#' mtcars_source <- TblSqlSource$new(dplyr::tbl(con, "mtcars"))
#' mtcars_source$get_db_type()  # "DuckDB"
#'
#' result <- mtcars_source$execute_query("SELECT * FROM mtcars WHERE cyl > 4")
#'
#' # Note, the result is not the *full* data frame, but a lazy SQL tibble
#' result
#'
#' # You can chain this result into a dplyr pipeline
#' dplyr::count(result, cyl, gear)
#'
#' # Or collect the entire data frame into local memory
#' dplyr::collect(result)
#'
#' # Finally, clean up when done with the database (closes the DB connection)
#' mtcars_source$cleanup()
#'
#' @export
TblSqlSource <- R6::R6Class(
  "TblSqlSource",
  inherit = DBISource,
  private = list(
    tbl = NULL,
    tbl_cte = NULL
  ),
  public = list(
    #' @field table_name Name of the table to be used in SQL queries
    table_name = NULL,

    #' @description
    #' Create a new TblSqlSource
    #'
    #' @param tbl A [dbplyr::tbl_sql()] (or SQL tibble via [dplyr::tbl()]).
    #' @param table_name Name of the table in the database. Can be a character
    #'   string, or will be inferred from the `tbl` argument, if possible.
    #'
    #' @return A new TblSqlSource object
    initialize = function(tbl, table_name = missing_arg()) {
      check_installed("dbplyr")
      check_installed("dplyr")

      if (!inherits(tbl, "tbl_sql")) {
        cli::cli_abort(
          "{.arg tbl} must be a SQL tibble connected to a database, not {.obj_type_friendly {tbl}}"
        )
      }

      private$conn <- dbplyr::remote_con(tbl)
      private$tbl <- tbl

      # Collect various signals to infer the table name
      obj_name <- deparse1(substitute(tbl))

      # Get the exact table name, if tbl directly references a single table
      remote_name <- dbplyr::remote_name(private$tbl)

      use_cte <- FALSE

      if (!is_missing(table_name)) {
        check_sql_table_name(table_name)
        self$table_name <- table_name
        use_cte <- !identical(table_name, remote_name)
      } else if (!is.null(remote_name)) {
        # Remote name is non-NULL when it points to a table, so we use that next
        self$table_name <- remote_name
        use_cte <- FALSE
      } else if (is_valid_sql_table_name(obj_name)) {
        self$table_name <- obj_name
        use_cte <- TRUE
      } else {
        id <- as.integer(runif(1) * 1e6)
        self$table_name <- sprintf("querychat_cte_%d", id)
        use_cte <- TRUE
      }

      if (use_cte) {
        # We received a complicated tbl expression, we'll have to use a CTE
        private$tbl_cte <- dbplyr::remote_query(private$tbl)
      }
    },

    #' @description
    #' Get the database type
    #'
    #' @return A string describing the database type (e.g., "DuckDB", "SQLite")
    get_db_type = function() {
      super$get_db_type()
    },

    #' @description
    #' Get schema information about the table
    #'
    #' @param categorical_threshold Maximum number of unique values for a text
    #'   column to be considered categorical
    #' @return A string containing schema information formatted for LLM prompts
    get_schema = function(categorical_threshold = 20) {
      get_schema_impl(
        private$conn,
        self$table_name,
        categorical_threshold,
        columns = colnames(private$tbl),
        prep_query = self$prep_query
      )
    },

    #' @description
    #' Execute a SQL query and return results
    #'
    #' @param query SQL query string to execute
    #' @param collect If `TRUE` (default), collects the results into a local data frame
    #'   using [dplyr::collect()]. If `FALSE`, returns a lazy SQL
    #'   tibble.
    #' @return A data frame (if `collect = TRUE`) or a lazy SQL tibble (if
    #'   `collect = FALSE`)
    execute_query = function(query, collect = TRUE) {
      sql_query <- self$prep_query(query)
      result <- dplyr::tbl(private$conn, dplyr::sql(sql_query))
      if (collect) {
        result <- dplyr::collect(result)
      }
      result
    },

    #' @description
    #' Test a SQL query by fetching only one row
    #'
    #' @param query SQL query string to test
    #' @param require_all_columns If `TRUE`, validates that the result includes
    #'   all original table columns (default: `FALSE`)
    #' @return A data frame containing one row of results (or empty if no matches)
    test_query = function(query, require_all_columns = FALSE) {
      super$test_query(
        query = self$prep_query(query),
        require_all_columns = require_all_columns
      )
    },

    #' @description
    #' Prepare a generic `SELECT * FROM ____` query to work with the SQL tibble
    #'
    #' @param query SQL query as a string
    #' @return A complete SQL query string
    prep_query = function(query) {
      check_string(query)

      if (is.null(private$tbl_cte)) {
        return(query)
      }

      sprintf(
        "WITH %s AS (\n%s\n)\n%s",
        DBI::dbQuoteIdentifier(private$conn, self$table_name),
        private$tbl_cte,
        query
      )
    },

    #' @description
    #' Get the unfiltered data as a SQL tibble
    #'
    #' @return A [dbplyr::tbl_sql()] containing the original, unfiltered data
    get_data = function() {
      private$tbl
    },

    #' @description
    #' Clean up resources (close connections, etc.)
    #'
    #' @return NULL (invisibly)
    cleanup = function() {
      super$cleanup()
    }
  )
)
