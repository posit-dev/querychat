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
#' # Create a QueryChat object
#' qc <- QueryChat$new(mtcars, "mtcars")
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
#' - [as_querychat_data_source()]: (Advanced) Create custom data source objects
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
#' @importFrom rlang %||%
## usethis namespace: end
NULL
