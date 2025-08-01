# Querychat R Examples

This directory contains examples demonstrating different ways to use the querychat R package. Each example is contained in its own folder with a complete Shiny application.

## Examples Overview

### [basic-dataframe](basic-dataframe/)
- **Description**: Simple example using querychat with a regular R data frame
- **Dataset**: Titanic passenger data
- **Key feature**: Shows how querychat works with standard data frames
- **To run**: `shiny::runApp("basic-dataframe")`

### [basic-database](basic-database/)
- **Description**: Simple example using querychat with a SQL database
- **Dataset**: Iris flower measurements
- **Key feature**: Shows how querychat connects to databases via DBI
- **To run**: `shiny::runApp("basic-database")`

### [chained-query](chained-query/)
- **Description**: Advanced example demonstrating query chaining functionality
- **Dataset**: Titanic passenger data in SQLite
- **Key feature**: Shows how to use `querychat_server$tbl()` to chain additional dplyr operations
- **To run**: `shiny::runApp("chained-query")`

## Key Concepts Demonstrated

### Data Sources

The examples demonstrate the two main ways to create a data source:

```r
# With a data frame
df_source <- querychat_data_source(your_dataframe)

# With a database connection
db_source <- querychat_data_source(conn, table_name = "your_table")
```

### Initialization

All examples use the same pattern for initialization:

```r
querychat_config <- querychat_init(
  data_source = your_source,
  greeting = greeting,
  data_description = "Description of your data",
  extra_instructions = "Additional instructions for the LLM"
)
```

### UI Integration

The examples show how to integrate querychat into a Shiny UI:

```r
ui <- bslib::page_sidebar(
  sidebar = querychat_sidebar("chat"),
  # Your main UI content here
)
```

### Server Logic

The server function follows this pattern:

```r
server <- function(input, output, session) {
  chat <- querychat_server("chat", querychat_config)
  
  # Access chat outputs:
  output$data_table <- DT::renderDT({
    chat$df()  # Direct data frame access
  })
  
  output$sql_query <- renderText({
    chat$sql()  # Access generated SQL
  })
  
  # Advanced: Use tbl() for query chaining
  output$chained_results <- DT::renderDT({
    chat$tbl() %>%
      filter(your_condition) %>%
      collect()
  })
}
```

## Running the Examples

To run any of these examples:

1. Make sure you have the querychat package installed:
   ```r
   devtools::install("path/to/querychat/pkg-r")
   ```

2. Install example-specific dependencies:
   ```r
   install.packages(c("shiny", "bslib", "DT", "dplyr", "DBI", "RSQLite"))
   ```

3. Run the specific example:
   ```r
   shiny::runApp("path/to/querychat/pkg-r/examples/example-name")
   ```

## Creating Your Own Apps

These examples are designed to be starting points for your own applications. The core concepts apply regardless of your specific data or use case.

For more advanced usage, explore:
- Custom LLM settings via the `create_chat_func` parameter
- Adding additional UI elements to work with querychat outputs
- Integrating with other Shiny packages and extensions
- Saving and restoring chat history