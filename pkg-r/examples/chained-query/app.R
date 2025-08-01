library(shiny)
library(bslib)
library(querychat)
library(DBI)
library(RSQLite)
library(dplyr)
library(DT)
library(ggplot2)
library(plotly)

# Create a sample SQLite database with Titanic dataset
temp_db <- tempfile(fileext = ".db")
onStop(function() {
  if (file.exists(temp_db)) {
    unlink(temp_db)
  }
})

conn <- dbConnect(RSQLite::SQLite(), temp_db)

# Load Titanic dataset and prepare it for the database
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

# Write to SQLite database
dbWriteTable(conn, "titanic", titanic_expanded, overwrite = TRUE)

# Load greeting from external markdown file
greeting <- readLines("greeting.md", warn = FALSE)
greeting <- paste(greeting, collapse = "\n")

# Create data source using querychat_data_source
titanic_source <- querychat_data_source(conn, table_name = "titanic")

# Configure querychat for database
querychat_config <- querychat_init(
  data_source = titanic_source,
  greeting = greeting,
  data_description = "This database contains information about Titanic passengers with columns for passenger ID, class (1st, 2nd, 3rd, or Crew), sex (Male or Female), age category (Adult or Child), and survival (Yes or No).",
  extra_instructions = "When showing results, always explain survival patterns across different demographic groups."
)

ui <- bslib::page_sidebar(
  title = "Titanic Query Chaining Demo",
  sidebar = querychat_sidebar("chat"),
  
  # Main content
  bslib::layout_column_wrap(
    width = 1/2,
    card(
      card_header("Passenger Count Summary"),
      card_body(plotlyOutput("passenger_chart"))
    ),
    card(
      card_header("Survival Rate by Class"),
      card_body(plotlyOutput("class_survival_chart"))
    )
  ),
  
  bslib::layout_column_wrap(
    width = 1,
    card(
      card_header("Query Results"),
      card_body(
        p("Basic results from chat query:"),
        DTOutput("data_table")
      )
    )
  ),
  
  hr(),
  
  card(
    card_header("Current SQL Query"),
    card_body(textOutput("sql_query"))
  ),
  
  hr(),
  
  card(
    card_header("About This Example"),
    card_body(
      p("This example demonstrates how to use querychat_server$tbl() to chain additional dplyr operations after a natural language query."),
      p("The chat sidebar generates a base query, then we apply additional transformations programmatically.")
    )
  )
)

server <- function(input, output, session) {
  # Initialize querychat
  chat <- querychat_server("chat", querychat_config)
  
  # Create high-level passenger counts chart
  output$passenger_chart <- renderPlotly({
    # Get base data from current query or all passengers if no query
    base_data <- chat$tbl() %>%
      group_by(Class, Sex) %>%
      summarize(Count = n(), .groups = "drop") %>%
      collect()
      
    p <- ggplot(base_data, aes(x = Class, y = Count, fill = Sex)) +
      geom_col(position = "dodge") +
      theme_minimal() +
      labs(title = "Passenger Count by Class and Sex",
           x = "Passenger Class", 
           y = "Count")
    
    ggplotly(p)
  })
  
  # Create survival rate by class chart
  output$class_survival_chart <- renderPlotly({
    survival_data <- chat$tbl() %>%
      group_by(Class) %>%
      summarize(
        Total = n(),
        Survived = sum(Survived == "Yes"),
      ) %>%
      mutate(
        SurvivalRate = Survived / n()
      ) %>%
      collect()
    
    p <- ggplot(survival_data, aes(x = Class, y = SurvivalRate, fill = Class)) +
      geom_col() +
      theme_minimal() +
      labs(title = "Survival Rate by Class",
           x = "Passenger Class",
           y = "Survival Rate (%)") +
      scale_y_continuous(limits = c(0, 100))
    
    ggplotly(p)
  })
  
  # Basic query results from chat
  output$data_table <- DT::renderDT({
    df <- chat$tbl() %>% collect()
    df
  }, options = list(pageLength = 5))
  
  
  # Show the current SQL query
  output$sql_query <- renderText({
    query <- chat$sql()
    if (query == "") {
      "No query yet - try asking a question about the Titanic data!"
    } else {
      query
    }
  })
}

shiny::shinyApp(ui = ui, server = server)