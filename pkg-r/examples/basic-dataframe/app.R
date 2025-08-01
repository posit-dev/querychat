library(shiny)
library(bslib)
library(querychat)
library(dplyr)
library(DT)

# Prepare the Titanic dataset
titanic_data <- datasets::Titanic
titanic_df <- as.data.frame(titanic_data)

# Rename and restructure the data to match a typical passenger list
names(titanic_df) <- c("Class", "Sex", "Age", "Survived", "Count")

# Expand the data to have one row per passenger
titanic_expanded <- tidyr::uncount(titanic_df, Count)

# Add a passenger ID column
titanic_expanded$PassengerId <- 1:nrow(titanic_expanded)

# Reorder columns to have ID first
titanic_expanded <- titanic_expanded[, c("PassengerId", "Class", "Sex", "Age", "Survived")]

# Load greeting from external markdown file
greeting_path <- file.path(getwd(), "greeting.md")
greeting <- readLines(greeting_path, warn = FALSE)
greeting <- paste(greeting, collapse = "\n")

# Create data source using querychat_data_source with data frame
titanic_source <- querychat_data_source(titanic_expanded)

# Configure querychat
querychat_config <- querychat_init(
  data_source = titanic_source,
  greeting = greeting,
  data_description = "This is the Titanic dataset with information about passengers with columns for passenger ID, class (1st, 2nd, 3rd, or Crew), sex (Male or Female), age category (Adult or Child), and survival (Yes or No).",
  extra_instructions = "When showing results, always explain survival patterns across different demographic groups."
)

ui <- bslib::page_sidebar(
  title = "Titanic Dataset Query Chat",
  sidebar = querychat_sidebar("chat"),
  
  bslib::layout_column_wrap(
    width = 1,
    card(
      card_header("Dataset Overview"),
      card_body(
        p("This example demonstrates using querychat with a data frame (rather than a database)."),
        p("Ask questions about the Titanic dataset in the chat sidebar.")
      )
    )
  ),
  
  bslib::layout_column_wrap(
    width = 1,
    card(
      card_header("Query Results"),
      card_body(
        p("The table below shows the results from your chat queries:"),
        DT::DTOutput("data_table", fill = FALSE)
      )
    )
  ),
  
  bslib::layout_column_wrap(
    width = 1,
    card(
      card_header("Generated SQL Query"),
      card_body(
        p("Even though we're using a data frame, querychat translates natural language to SQL under the hood:"),
        verbatimTextOutput("sql_query")
      )
    )
  ),
  
  bslib::layout_column_wrap(
    width = 1,
    card(
      card_header("Dataset Information"),
      card_body(
        p("The Titanic dataset contains:"),
        tags$ul(
          tags$li(strong("PassengerId:"), "Unique identifier for each passenger"),
          tags$li(strong("Class:"), "Passenger class (1st, 2nd, 3rd, or Crew)"),
          tags$li(strong("Sex:"), "Passenger sex (Male or Female)"),
          tags$li(strong("Age:"), "Age category (Adult or Child)"),
          tags$li(strong("Survived:"), "Whether the passenger survived (Yes or No)")
        )
      )
    )
  )
)

server <- function(input, output, session) {
  # Initialize querychat
  chat <- querychat_server("chat", querychat_config)
  
  # Display query results
  output$data_table <- DT::renderDT({
    df <- chat$df()
    df
  }, options = list(pageLength = 10, scrollX = TRUE))
  
  # Display the SQL query
  output$sql_query <- renderText({
    query <- chat$sql()
    if (query == "") {
      "No filter applied - showing all data"
    } else {
      query
    }
  })
}

shiny::shinyApp(ui = ui, server = server)