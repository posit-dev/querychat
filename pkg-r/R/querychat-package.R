#' querychat: Chat with Your Data Using Natural Language
#'
#' @description
#' querychat provides an interactive chat interface for querying data using
#' natural language. It translates your questions into SQL queries, executes
#' them against your data, and displays the results. The package works with
#' both data frames and database connections.
#'
#' @section Quick Start:
#' The easiest way to get started is with the [QueryChat] R6 class:
#'
#' ```r
#' library(querychat)
#'
#' # Create a QueryChat object (table name inferred from variable)
#' qc <- QueryChat$new(mtcars)
#'
#' # Option 1: Run a complete app with sensible defaults
#' qc$app()
#'
#' # Option 2: Build a custom Shiny app
#' ui <- page_sidebar(
#'   qc$sidebar(),
#'   dataTableOutput("data")
#' )
#'
#' server <- function(input, output, session) {
#'   qc$server()
#'   output$data <- renderDataTable(qc$df())
#' }
#'
#' shinyApp(ui, server)
#' ```
#'
#' @section Key Features:
#' - **Natural language queries**: Ask questions in plain English
#' - **SQL transparency**: See the generated SQL queries
#' - **Multiple data sources**: Works with data frames and database connections
#' - **Customizable**: Add data descriptions, extra instructions, and custom greetings
#' - **LLM agnostic**: Works with OpenAI, Anthropic, Google, and other providers via ellmer
#'
#' @section Main Components:
#' - [QueryChat]: The main R6 class for creating chat interfaces
#' - [DataSource], [DataFrameSource], [DBISource]: R6 classes for data sources
#'
#' @section Examples:
#' To see examples included with the package, run:
#'
#' ```r
#' shiny::runExample(package = "querychat")
#' ```
#'
#' This provides a list of available examples. To run a specific example, like
#' '01-hello-app', use:
#'
#' ```r
#' shiny::runExample("01-hello-app", package = "querychat")
#' ```
#'
#'
#' @keywords internal
"_PACKAGE"

## usethis namespace: start
#' @importFrom lifecycle deprecated
#' @importFrom R6 R6Class
#' @importFrom bslib sidebar
#' @import rlang
## usethis namespace: end
NULL

# @staticimports pkg:staticimports
#   read_utf8

# enable usage of <S7_object>@name in package code
#' @rawNamespace if (getRversion() < "4.3.0") importFrom("S7", "@")
NULL

release_bullets <- function() {
  c(
    "Run `staticimports::import()` to update static imports",
    "Enable `development.mode: auto` in `_pkgdown.yml` and remove this release bullet."
  )
}

suppress_rcmdcheck <- function() {
  S7::S7_class
  whisker::whisker.render
  # coro is used inside R6 method definitions (handoff_orchestrator.R), which
  # R CMD check's static analysis can't see in the installed package.
  coro::async
}

# On R < 4.3, `@` is imported from S7 (see the conditional importFrom above),
# so codetools reads S7 property accesses like `x@label` as regular calls and
# flags the property names as unbound globals ("no visible binding" NOTE).
utils::globalVariables(c(
  "arguments", "bundle_id", "bundled_files", "bundled_tables", "contents",
  "data", "data_instructions", "description", "directions",
  "editor_language", "error", "file_extension", "format_id", "freeform",
  "ggsql", "handoff_id", "handoff_type", "icon", "id",
  "install_instructions", "items", "label", "language", "name",
  "preview_html", "properties", "referenced_tables", "request",
  "run_instructions", "selected_ids", "sql", "system_prompt", "targets",
  "text", "thumbnail", "title", "turns", "type", "type_id", "value",
  "values"
))
