library(shiny)
library(bslib)
library(querychat)
library(DBI)
library(RSQLite)
library(palmerpenguins)

# Create a sample SQLite database for demonstration
# In a real app, you would connect to your existing database
temp_db <- tempfile(fileext = ".db")
onStop(function() {
  if (file.exists(temp_db)) {
    unlink(temp_db)
  }
})

conn <- dbConnect(RSQLite::SQLite(), temp_db)

# Create sample data in the database
dbWriteTable(conn, "penguins", palmerpenguins::penguins, overwrite = TRUE)

# Define a custom greeting for the database app
greeting <- "
# Welcome to the Database Query Assistant! 🐧

I can help you explore and analyze the Palmer Penguins dataset from the connected database.
Ask me questions about the penguins, and I'll generate SQL queries to get the answers.

Try asking:
- <span class=\"suggestion\">Show me the first 10 rows of the penguins dataset</span>
- <span class=\"suggestion\">What's the average bill length by species?</span>
- <span class=\"suggestion\">Which species has the largest body mass?</span>
- <span class=\"suggestion\">Create a summary of measurements grouped by species and island</span>
"

# Create QueryChat object with database connection
qc <- QueryChat$new(
  conn,
  "penguins",
  greeting = greeting,
  data_description = "This database contains the Palmer Penguins dataset with measurements of bill dimensions, flipper length, body mass, sex, and species (Adelie, Chinstrap, and Gentoo) collected from three islands in the Palmer Archipelago, Antarctica.",
  extra_instructions = "When showing results, always explain what the data represents and highlight any interesting patterns you observe."
)

ui <- page_sidebar(
  title = "Database Query Chat",
  sidebar = qc$sidebar(),

  h2("Current Data View"),
  p(
    "The table below shows the current filtered data based on your chat queries:"
  ),
  DT::DTOutput("data_table", fill = FALSE),

  h2("Current SQL Query"),
  verbatimTextOutput("sql_query"),

  h2("Dataset Information"),
  p("This demo database contains:"),
  tags$ul(
    tags$li("penguins - Palmer Penguins dataset (344 rows, 8 columns)"),
    tags$li(
      "Columns: species, island, bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g, sex, year"
    )
  )
)

server <- function(input, output, session) {
  qc$server()

  output$data_table <- DT::renderDT(
    {
      qc$df()
    },
    options = list(pageLength = 10, scrollX = TRUE)
  )

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
