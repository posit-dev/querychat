#' Table Accessor
#'
#' @description
#' Accessor for a specific table's data source and per-table reactive state.
#' Returned by [QueryChat]'s `$table("name")` method.
#'
#' @export
TableAccessor <- R6::R6Class(
  "TableAccessor",
  private = list(
    querychat = NULL,
    .table_name = NULL
  ),
  public = list(
    #' @description Create a new TableAccessor.
    #' @param querychat The parent QueryChat instance.
    #' @param table_name The name of the table.
    initialize = function(querychat, table_name) {
      private$querychat <- querychat
      private$.table_name <- table_name
    },

    #' @description Return the current filtered data for this table.
    df = function() {
      vals <- private$querychat$.__enclos_env__$private$server_values
      if (is.null(vals)) {
        cli::cli_abort("Server not initialized. Call {.fn $server} first.")
      }
      vals$.tables[[private$.table_name]]$df()
    },

    #' @description Return the current SQL filter for this table.
    sql = function() {
      vals <- private$querychat$.__enclos_env__$private$server_values
      if (is.null(vals)) {
        cli::cli_abort("Server not initialized. Call {.fn $server} first.")
      }
      vals$.tables[[private$.table_name]]$sql()
    },

    #' @description Return the current filter title for this table.
    title = function() {
      vals <- private$querychat$.__enclos_env__$private$server_values
      if (is.null(vals)) {
        cli::cli_abort("Server not initialized. Call {.fn $server} first.")
      }
      vals$.tables[[private$.table_name]]$title()
    }
  ),
  active = list(
    #' @field table_name The name of this table.
    table_name = function() private$.table_name,

    #' @field data_source The DataSource for this table.
    data_source = function() {
      private$querychat$.__enclos_env__$private$.data_sources[[
        private$.table_name
      ]]
    }
  )
)
