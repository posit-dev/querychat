library(shiny)
library(bslib)
library(querychat)
library(palmerpenguins)

# Define a custom greeting for the penguins app
greeting <- "
# Welcome to the Palmer Penguins Explorer! 🐧

I can help you explore and analyze the Palmer Penguins dataset. Ask me questions
about the penguins, and I'll generate SQL queries to get the answers.

Try asking:
- <span class=\"suggestion\">Show me the first 10 rows of the penguins dataset</span>
- <span class=\"suggestion\">What's the average bill length by species?</span>
- <span class=\"suggestion\">Which species has the largest body mass?</span>
- <span class=\"suggestion\">Create a summary of measurements grouped by species and island</span>
"

# Create QueryChat object with custom options
qc <- QueryChat$new(
  penguins,
  "penguins",
  greeting = greeting,
  data_description = "The Palmer Penguins dataset contains measurements of bill dimensions, flipper length, body mass, sex, and species (Adelie, Chinstrap, and Gentoo) collected from three islands in the Palmer Archipelago, Antarctica.",
  extra_instructions = "When showing results, always explain what the data represents and highlight any interesting patterns you observe."
)

# Define custom UI with sidebar
ui <- page_sidebar(
  title = "Palmer Penguins Chat Explorer",
  sidebar = qc$sidebar(),

  h2("Current Data View"),
  p(
    "The table below shows the current filtered data based on your chat queries:"
  ),
  DT::DTOutput("data_table", fill = FALSE),

  h2("Current SQL Query"),
  verbatimTextOutput("sql_query"),

  h2("Dataset Information"),
  p("This dataset contains:"),
  tags$ul(
    tags$li("344 observations of penguins"),
    tags$li(
      "Columns: species, island, bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g, sex, year"
    )
  )
)

# Define server logic
server <- function(input, output, session) {
  # Initialize QueryChat server
  qc$server()

  # Render the data table
  output$data_table <- DT::renderDT(
    {
      qc$df()
    },
    options = list(pageLength = 10, scrollX = TRUE)
  )

  # Render the SQL query
  output$sql_query <- renderText({
    query <- qc$sql()
    if (query == "") {
      "No filter applied - showing all data"
    } else {
      query
    }
  })
}

shinyApp(ui = ui, server = server)
