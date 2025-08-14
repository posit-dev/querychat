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

# Setup database source
db_conn <- dbConnect(RSQLite::SQLite(), temp_db)
iris_source <- querychat_data_source(db_conn, "iris")

# Configure querychat with mock
querychat_config <- querychat_init(
  data_source = iris_source,
  greeting = "Welcome to the test app!",
  client = MockChat$new(ellmer::Provider("test", "test", "test"))
)

ui <- page_sidebar(
  title = "Test Database App",
  sidebar = querychat_sidebar("chat"),
  h2("Data"),
  DT::DTOutput("data_table"),
  h3("SQL Query"),
  verbatimTextOutput("sql_query")
)

server <- function(input, output, session) {
  chat <- querychat_server("chat", querychat_config)

  output$data_table <- DT::renderDT(
    {
      chat$df()
    },
    options = list(pageLength = 5)
  )

  output$sql_query <- renderText({
    query <- chat$sql()
    if (query == "") "No filter applied" else query
  })

  session$onSessionEnded(function() {
    if (DBI::dbIsValid(db_conn)) {
      DBI::dbDisconnect(db_conn)
    }
    unlink(temp_db)
  })
}

shinyApp(ui = ui, server = server)
