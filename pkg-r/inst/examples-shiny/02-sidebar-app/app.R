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
- <span class="suggestion">Create a summary of measurements grouped by species and island</span>
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
  ),
  extra_instructions = paste(
    "When showing results, always explain what the data represents",
    "and highlight any interesting patterns you observe."
  )
)

# Define custom UI with sidebar
ui <- page_sidebar(
  title = "Palmer Penguins Chat Explorer",
  sidebar = qc$sidebar(),

  card(
    fill = FALSE,
    card_header("Current SQL Query"),
    verbatimTextOutput("sql_query")
  ),

  card(
    full_screen = TRUE,
    card_header(
      "Current Data View",
      tooltip(
        bsicons::bs_icon("question-circle-fill", class = "mx-1"),
        "The table below shows the current filtered data based on your chat queries"
      ),
      tooltip(
        bsicons::bs_icon("info-circle-fill"),
        "The penguins dataset contains measurements on 344 penguins."
      )
    ),
    DT::DTOutput("data_table"),
    card_footer(
      markdown(
        "Data source: [palmerpenguins package](https://allisonhorst.github.io/palmerpenguins/)"
      )
    )
  )
)

# Define server logic
server <- function(input, output, session) {
  # Initialize QueryChat server
  qc_vals <- qc$server()

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
    if (query == "") {
      "No filter applied - showing all data"
    } else {
      query
    }
  })
}

shinyApp(ui = ui, server = server)
