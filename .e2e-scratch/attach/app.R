library(querychat)
library(shiny)
library(bslib)

qc <- QueryChat$new(
  mtcars,
  "mtcars",
  greeting = "Ask me about mtcars. You can also attach files.",
  client = "anthropic/claude-haiku-4-5"
)

ui <- page_sidebar(
  title = "Attachment test",
  sidebar = qc$sidebar(allow_attachments = TRUE),
  DT::DTOutput("tbl")
)

server <- function(input, output, session) {
  vals <- qc$server()
  output$tbl <- DT::renderDT(vals$df())
}

shinyApp(ui, server)
