# Querychat Data Frame Example

This example demonstrates how to use querychat with a regular R data frame. The app uses the Titanic dataset and provides a chat interface for querying the data.

## Features

- Uses a simple data frame (no database required)
- Natural language querying using the chat sidebar
- Display of query results in a table
- Display of the generated SQL query
- Information about the dataset structure

## How It Works

1. The app prepares the Titanic dataset as a data frame
2. A querychat data source is created with `querychat_data_source(titanic_expanded)`
3. The chat interface is configured with `querychat_init()` and a custom greeting
4. Users can enter natural language queries in the chat sidebar
5. Results are displayed in a table, and the corresponding SQL is shown

## Under the Hood

Even though we're using a data frame, querychat still uses SQL for query execution:

- When using `querychat_data_source()` with a data frame, it creates a temporary in-memory DuckDB database
- Your natural language queries are converted to SQL
- SQL queries are executed against the DuckDB instance
- Results are returned as R data frames

This approach ensures consistent behavior between data frames and external databases.

## Running This Example

To run this example:

1. Make sure you have all dependencies installed:
   - shiny, bslib, querychat, dplyr, DT, tidyr

2. Run the app with:
   ```r
   shiny::runApp("path/to/basic-dataframe")
   ```

3. Try asking questions in the chat sidebar like:
   - "Show me the first 10 passengers"
   - "What was the survival rate by class?"
   - "Show me all children who survived"