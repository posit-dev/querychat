#' Deprecated functions
#'
#' These functions have been replaced by the new `QueryChat` R6 class API.
#' Please update your code to use the new class-based approach.
#'
#' @name deprecated
#' @keywords internal
NULL

#' @rdname deprecated
#' @export
querychat_init <- function(...) {
  lifecycle::deprecate_stop(
    when = "0.1.0",
    what = "querychat_init()",
    with = "QueryChat$new()",
    details = c(
      "Old code:",
      "  config <- querychat_init(mtcars, greeting = 'Hello!')",
      "  ui <- page_sidebar(sidebar = querychat_sidebar('chat'), ...)",
      "  server <- function(input, output, session) {",
      "    chat <- querychat_server('chat', config)",
      "    output$data <- renderDataTable(chat$df())",
      "  }",
      "",
      "New code:",
      "  qc <- QueryChat$new(mtcars, 'mtcars', greeting = 'Hello!')",
      "  ui <- page_sidebar(sidebar = qc$sidebar(), ...)",
      "  server <- function(input, output, session) {",
      "    qc$server()",
      "    output$data <- renderDataTable(qc$df())",
      "  }",
      "",
      "See ?QueryChat for more information."
    )
  )
}

#' @rdname deprecated
#' @export
querychat_sidebar <- function(...) {
  lifecycle::deprecate_stop(
    when = "0.1.0",
    what = "querychat_sidebar()",
    with = "QueryChat$sidebar()",
    details = c(
      "Old code:",
      "  querychat_sidebar('chat')",
      "",
      "New code:",
      "  qc <- QueryChat$new(data, 'table_name')",
      "  qc$sidebar()",
      "",
      "See ?QueryChat for more information."
    )
  )
}

#' @rdname deprecated
#' @export
querychat_ui <- function(...) {
  lifecycle::deprecate_stop(
    when = "0.1.0",
    what = "querychat_ui()",
    with = "QueryChat$ui()",
    details = c(
      "Old code:",
      "  querychat_ui('chat')",
      "",
      "New code:",
      "  qc <- QueryChat$new(data, 'table_name')",
      "  qc$ui()",
      "",
      "See ?QueryChat for more information."
    )
  )
}

#' @rdname deprecated
#' @export
querychat_server <- function(...) {
  lifecycle::deprecate_stop(
    when = "0.1.0",
    what = "querychat_server()",
    with = "QueryChat$server()",
    details = c(
      "Old code:",
      "  chat <- querychat_server('chat', config)",
      "  output$data <- renderDataTable(chat$df())",
      "",
      "New code:",
      "  qc <- QueryChat$new(data, 'table_name')",
      "  qc$server()  # Must be called within server function",
      "  output$data <- renderDataTable(qc$df())",
      "",
      "See ?QueryChat for more information."
    )
  )
}

#' @rdname deprecated
#' @export
querychat_greeting <- function(...) {
  lifecycle::deprecate_stop(
    when = "0.1.0",
    what = "querychat_greeting()",
    with = "QueryChat$generate_greeting()",
    details = c(
      "Old code:",
      "  greeting <- querychat_greeting(config)",
      "",
      "New code:",
      "  qc <- QueryChat$new(data, 'table_name')",
      "  greeting <- qc$generate_greeting(echo = 'text')",
      "",
      "See ?QueryChat for more information."
    )
  )
}

#' @rdname deprecated
#' @export
querychat_data_source <- function(...) {
  lifecycle::deprecate_stop(
    when = "0.1.0",
    what = "querychat_data_source()",
    with = "QueryChat$new()",
    details = c(
      "Old code:",
      "  data_source <- querychat_data_source(db_connection, 'table_name')",
      "",
      "New code:",
      "  qc <- QueryChat$new(db_connection, 'table_name')",
      "",
      "See ?QueryChat for more information."
    )
  )
}
