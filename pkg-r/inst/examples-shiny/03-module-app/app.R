library(shiny)
library(bslib)
library(querychat)
library(palmerpenguins)

# Define a custom greeting for the penguins app
greeting <- r"(
# Welcome to the Palmer Penguins Explorer! 🐧

I can help you explore and analyze the Palmer Penguins dataset. Ask me questions
about the penguins, and I'll generate SQL queries to get the answers.

Try asking:
- <span class="suggestion">Show me the first 10 rows of the penguins dataset</span>
- <span class="suggestion">What's the average bill length by species?</span>
- <span class="suggestion">Which species has the largest body mass?</span>
)"

# Create QueryChat object with custom options
qc <- QueryChat$new(
  penguins,
  greeting = greeting,
  data_description = paste(
    "The Palmer Penguins dataset contains measurements of bill",
    "dimensions, flipper length, body mass, sex, and species",
    "(Adelie, Chinstrap, and Gentoo) collected from three islands in",
    "the Palmer Archipelago, Antarctica."
  )
)

# Module UI function
# This demonstrates the standard Shiny module pattern where:
# - The module ID is wrapped with ns() in the UI function
# - The same ID (unwrapped) is used in the corresponding server function
module_ui <- function(id) {
  ns <- NS(id)
  layout_sidebar(
    sidebar = qc$sidebar(id = ns("qc-ui")), # Pass namespaced ID to QueryChat
    padding = 0,
    navset_card_tab(
      title = "Data Explorer",
      nav_panel(
        "Data View",
        DT::DTOutput(ns("data_table"))
      ),
      nav_panel(
        "SQL Query",
        verbatimTextOutput(ns("sql_query"))
      )
    )
  )
}

# Module server function
module_server <- function(id) {
  moduleServer(id, function(input, output, session) {
    # Initialize QueryChat server with the same ID (unwrapped)
    # This connects to the UI initialized with id = ns("qc-ui")
    qc_vals <- qc$server(id = "qc-ui")

    # Render the data table
    output$data_table <- DT::renderDT(
      {
        qc_vals$df()
      },
      fillContainer = TRUE,
      options = list(pageLength = 25, scrollX = TRUE)
    )

    # Render the SQL query
    output$sql_query <- renderText({
      query <- qc_vals$sql()
      if (is.null(query) || !nzchar(query)) {
        "No filter applied - showing all data"
      } else {
        query
      }
    })
  })
}

# Define UI with multiple module instances
ui <- page_sidebar(
  title = "QueryChat Modules Example",
  sidebar = sidebar(
    "This example demonstrates using QueryChat within Shiny modules.",
    markdown(
      "Each module instance has its own QueryChat sidebar and data explorer.

      **UI:** `qc$sidebar(id = ns(\"qc-ui\"))` wraps the ID with the namespace function

      **Server:** `qc$server(id = \"qc-ui\")` uses the unwrapped ID"
    )
  ),
  class = "p-0",
  navset_card_underline(
    wrapper = \(...) card_body(..., padding = 0, border_radius = 0),
    nav_panel("Explorer 1", module_ui("module1")),
    nav_panel("Explorer 2", module_ui("module2"))
  )
)

# Define server logic
server <- function(input, output, session) {
  # Initialize both module instances
  module_server("module1")
  module_server("module2")
}

shinyApp(ui = ui, server = server)
