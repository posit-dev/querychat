#' Table Accessor
#'
#' @description
#' Accessor for a specific table's data source and per-table reactive state.
#' Returned by the server return value's `$table("name")` method.
#'
#' @export
#' @keywords internal
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
    #' @param state List of per-table reactive state (`sql`, `title`, `df`).
    initialize = function(table_name, data_source, state) {
      private$.table_name <- table_name
      private$.data_source <- data_source
      private$.state <- state
    },

    #' @description Return the current filtered data for this table.
    df = function() private$.state$df(),

    #' @description Return the current SQL filter for this table.
    sql = function() private$.state$sql(),

    #' @description Return the current filter title for this table.
    title = function() private$.state$title()
  ),
  active = list(
    #' @field table_name The name of this table.
    table_name = function() private$.table_name,

    #' @field data_source The DataSource for this table.
    data_source = function() private$.data_source
  )
)
