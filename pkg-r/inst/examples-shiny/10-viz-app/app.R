library(shiny)
library(bslib)
library(querychat)
library(palmerpenguins)

qc <- QueryChat$new(
  penguins,
  tools = c("update", "query", "visualize"),
  data_description = paste(
    "The Palmer Penguins dataset contains measurements of bill",
    "dimensions, flipper length, body mass, sex, and species",
    "(Adelie, Chinstrap, and Gentoo) collected from three islands in",
    "the Palmer Archipelago, Antarctica."
  )
)

ui <- page_sidebar(
  title = "querychat viz demo",
  sidebar = qc$sidebar(width = 400, open = TRUE, position = "right"),
  card(
    full_screen = TRUE,
    card_header("Data"),
    DT::DTOutput("dt")
  )
)

server <- function(input, output, session) {
  qc_vals <- qc$server()
  output$dt <- DT::renderDT(qc_vals$df(), fillContainer = TRUE)
}

shinyApp(ui, server)
