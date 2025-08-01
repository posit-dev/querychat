# Querychat Basic Database Example

This example demonstrates how to use querychat with a database connection. The app connects to a SQLite database containing the iris dataset and provides a chat interface for querying the data.

## Features

- SQLite database with iris dataset
- Natural language querying using the chat sidebar
- Display of query results in a table
- Display of the generated SQL query
- Basic information about the dataset

## How It Works

1. The app creates a temporary SQLite database and loads the iris dataset
2. A querychat data source is created with `querychat_data_source(conn, table_name = "iris")`
3. The chat interface is configured with `querychat_init()` and a custom greeting
4. Users can enter natural language queries in the chat sidebar
5. Results are displayed in a table and the corresponding SQL is shown

## Running This Example

To run this example:

1. Make sure you have all dependencies installed:
   - shiny, bslib, querychat, DBI, RSQLite

2. Run the app with:
   ```r
   shiny::runApp("path/to/basic-database")
   ```

3. Try asking questions in the chat sidebar like:
   - "Show me the first 10 rows of the iris dataset"
   - "What's the average sepal length by species?"
   - "Which species has the largest petals?"

## Connecting to Other Databases

This example uses an in-memory SQLite database for simplicity, but querychat works with any database supported by the DBI package:

- PostgreSQL (using RPostgreSQL or RPostgres)
- MySQL (using RMySQL)
- Microsoft SQL Server (using odbc)
- And more

Replace the connection setup with your preferred database, and querychat will handle the rest!