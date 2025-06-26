library(shiny)
library(bslib)
library(querychat)
library(DBI)
library(RSQLite)

# Create a sample SQLite database for demonstration
# In a real app, you would connect to your existing database
temp_db <- tempfile(fileext = ".db")
onStop(function() {
  if (file.exists(temp_db)) {
    unlink(temp_db)
  }
})

conn <- dbConnect(RSQLite::SQLite(), temp_db)
# The connection will automatically be closed when the app stops, thanks to
# querychat_init

# Create sample data in the database
iris_data <- iris
dbWriteTable(conn, "iris", iris_data, overwrite = TRUE)

# Define a custom greeting for the database app
greeting <- "
# Welcome to the Database Query Assistant! 📊

I can help you explore and analyze the iris dataset from the connected database. 
Ask me questions about the iris flowers, and I'll generate SQL queries to get the answers.

Try asking:
- Show me the first 10 rows of the iris dataset
- What's the average sepal length by species?
- Which species has the largest petals?
- Create a summary of measurements grouped by species
"

# Create data source using querychat_data_source
iris_source <- querychat_data_source(conn, table_name = "iris")

# Configure querychat for database
querychat_config <- querychat_init(
  data_source = iris_source,
  greeting = greeting,
  data_description = "This database contains the famous iris flower dataset with measurements of sepal and petal dimensions across three species (setosa, versicolor, and virginica).",
  extra_instructions = "When showing results, always explain what the data represents and highlight any interesting patterns you observe."
)

ui <- page_sidebar(
  title = "Database Query Chat",
  sidebar = querychat_sidebar("chat"),
  h2("Current Data View"),
  p("The table below shows the current filtered data based on your chat queries:"),
  DT::DTOutput("data_table"),
  br(),
  h3("Current SQL Query"),
  verbatimTextOutput("sql_query"),
  br(),
  h3("Dataset Information"),
  p("This demo database contains:"),
  tags$ul(
    tags$li("iris - Famous iris flower dataset (150 rows, 5 columns)"),
    tags$li("Columns: Sepal.Length, Sepal.Width, Petal.Length, Petal.Width, Species")
  )
)

server <- function(input, output, session) {
  chat <- querychat_server("chat", querychat_config)
  
  output$data_table <- DT::renderDT({
    df <- chat$df()
    # Collect data from lazy tbl if needed
    if (inherits(df, "tbl_lazy")) {
      dplyr::collect(df)
    } else {
      df
    }
  }, options = list(pageLength = 10, scrollX = TRUE))
  
  output$sql_query <- renderText({
    query <- chat$sql()
    if (query == "") {
      "No filter applied - showing all data"
    } else {
      query
    }
  })
}
  
shinyApp(ui = ui, server = server)
