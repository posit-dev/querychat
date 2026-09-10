library(querychat)
library(palmerpenguins)

qc <- QueryChat$new(
  penguins,
  tools = c("update", "query", "visualize")
)

ui <- qc$page("querychat viz demo")

server <- function(input, output, session) {
  qc$server()
}

shiny::shinyApp(ui, server)
