library(shiny)
library(bslib, warn.conflicts = FALSE)
library(querychat)
library(DBI)
library(RSQLite)

# Mock chat function to avoid LLM API calls
MockChat <- R6::R6Class(
  "MockChat",
  inherit = asNamespace("ellmer")[["Chat"]],
  public = list(
    stream_async = function(message, ...) {
      "Welcome! This is a mock response for testing."
    }
  )
)

# Create test database
temp_db <- tempfile(fileext = ".db")
conn <- dbConnect(RSQLite::SQLite(), temp_db)
dbWriteTable(conn, "iris", iris, overwrite = TRUE)
dbDisconnect(conn)

# Setup database source and QueryChat instance
db_conn <- dbConnect(RSQLite::SQLite(), temp_db)

# ellmer 0.5.0 moved model details out of `Provider` and into a new `Model`
# class: `Provider()` no longer takes `model` as its second positional
# argument, and `Chat$new()` now requires a separate `model` argument. `Model`
# doesn't exist before 0.5.0, so branch on its presence to support both.
mock_chat_client <- if (
  exists("Model", where = asNamespace("ellmer"), inherits = FALSE)
) {
  MockChat$new(
    ellmer::Provider("test", "test"),
    model = ellmer::Model(name = "test")
  )
} else {
  MockChat$new(ellmer::Provider("test", "test", "test"))
}

# Create QueryChat instance
qc <- QueryChat$new(
  data_source = db_conn,
  table_name = "iris",
  greeting = "Welcome to the test app!",
  client = mock_chat_client
)

ui <- page_sidebar(
  title = "Test Database App",
  sidebar = qc$sidebar(),
  h2("Data"),
  DT::DTOutput("data_table"),
  h3("SQL Query"),
  verbatimTextOutput("sql_query")
)

server <- function(input, output, session) {
  qc_vals <- qc$server()

  output$data_table <- DT::renderDT(
    {
      qc_vals$df()
    },
    options = list(pageLength = 5)
  )

  output$sql_query <- renderText({
    query <- qc_vals$sql()
    if (is.null(query) || !nzchar(query)) "No filter applied" else query
  })

  session$onSessionEnded(function() {
    if (DBI::dbIsValid(db_conn)) {
      DBI::dbDisconnect(db_conn)
    }
    unlink(temp_db)
  })
}

shinyApp(ui = ui, server = server)
