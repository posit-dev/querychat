library(shiny)
library(bslib)
library(querychat)
library(DBI)
library(RSQLite)

# Create a sample SQLite database for demonstration
# In a real app, you would connect to your existing database
temp_db <- tempfile(fileext = ".db")
conn <- dbConnect(RSQLite::SQLite(), temp_db)

# Create sample data in the database
iris_data <- iris
dbWriteTable(conn, "iris", iris_data, overwrite = TRUE)

# Disconnect temporarily - we'll reconnect in the app
dbDisconnect(conn)

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

# Create database source
# Note: In a production app, you would use your actual database credentials
db_conn <- dbConnect(RSQLite::SQLite(), temp_db)
iris_source <- database_source(db_conn, "iris")

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
    chat$df()
  }, options = list(pageLength = 10, scrollX = TRUE))
  
  output$sql_query <- renderText({
    query <- chat$sql()
    if (query == "") {
      "No filter applied - showing all data"
    } else {
      query
    }
  })
  
  # Clean up database connection when app stops
  session$onSessionEnded(function() {
    if (dbIsValid(db_conn)) {
      dbDisconnect(db_conn)
    }
    if (file.exists(temp_db)) {
      unlink(temp_db)
    }
  })
}

shinyApp(ui = ui, server = server)
