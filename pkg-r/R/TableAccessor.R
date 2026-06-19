#' Table Accessor
#'
#' @description
#' Accessor for a specific table's data source and per-table reactive state.
#' Returned by [QueryChat]'s `$table("name")` method (config-only) or by the
#' server return's `$table("name")` method (with reactive state).
#'
#' @export
TableAccessor <- R6::R6Class(
  "TableAccessor",
  private = list(
    .table_name = NULL,
    .data_source = NULL,
    .state = NULL
  ),
  public = list(
    #' @description Create a new TableAccessor.
    #' @param table_name The name of the table.
    #' @param data_source The DataSource for this table.
    #' @param state Optional list of per-table reactive state (`sql`, `title`,
    #'   `df`). When `NULL`, reactive methods raise an error.
    initialize = function(table_name, data_source, state = NULL) {
      private$.table_name <- table_name
      private$.data_source <- data_source
      private$.state <- state
    },

    #' @description Return the current filtered data for this table.
    df = function() {
      if (is.null(private$.state)) {
        cli::cli_abort(
          "Reactive methods are not available on {.code qc$table()}. Use the server return value: {.code qc_vals$table({.val {private$.table_name}})$df()}."
        )
      }
      private$.state$df()
    },

    #' @description Return the current SQL filter for this table.
    sql = function() {
      if (is.null(private$.state)) {
        cli::cli_abort(
          "Reactive methods are not available on {.code qc$table()}. Use the server return value: {.code qc_vals$table({.val {private$.table_name}})$sql()}."
        )
      }
      private$.state$sql()
    },

    #' @description Return the current filter title for this table.
    title = function() {
      if (is.null(private$.state)) {
        cli::cli_abort(
          "Reactive methods are not available on {.code qc$table()}. Use the server return value: {.code qc_vals$table({.val {private$.table_name}})$title()}."
        )
      }
      private$.state$title()
    }
  ),
  active = list(
    #' @field table_name The name of this table.
    table_name = function() private$.table_name,

    #' @field data_source The DataSource for this table.
    data_source = function() private$.data_source
  )
)
