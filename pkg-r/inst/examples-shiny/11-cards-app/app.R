library(shiny)
library(bslib)
library(querychat)
library(palmerpenguins)

qc <- QueryChat$new(
  penguins,
  tools = c("update", "query", "visualize", "cards"),
  data_description = paste(
    "The Palmer Penguins dataset contains measurements of bill",
    "dimensions, flipper length, body mass, sex, and species",
    "(Adelie, Chinstrap, and Gentoo) collected from three islands in",
    "the Palmer Archipelago, Antarctica."
  )
)

ui <- page_sidebar(
  title = "querychat cards demo",
  sidebar = qc$sidebar(width = 400, open = TRUE, position = "right"),
  qc$ui_cards()
)

server <- function(input, output, session) {
  qc$server()
}

shinyApp(ui, server)
