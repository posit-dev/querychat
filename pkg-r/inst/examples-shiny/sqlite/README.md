# Database Setup Examples for querychat

This document provides examples of how to set up querychat with various database types.

## SQLite

```r
library(DBI)
library(RSQLite)
library(querychat)

# Connect to SQLite database
conn <- dbConnect(RSQLite::SQLite(), "path/to/your/database.db")

# Create QueryChat instance
qc <- QueryChat$new(
  conn,
  "your_table_name",
  greeting = "Welcome! Ask me about your data.",
  data_description = "Description of your data..."
)

# Launch the app
qc$app()
```

## PostgreSQL

```r
library(DBI)
library(RPostgreSQL)  # or library(RPostgres)
library(querychat)

# Connect to PostgreSQL
conn <- dbConnect(
  RPostgreSQL::PostgreSQL(),  # or RPostgres::Postgres()
  dbname = "your_database",
  host = "localhost",
  port = 5432,
  user = "your_username",
  password = "your_password"
)

# Create QueryChat instance
qc <- QueryChat$new(conn, "your_table_name")

# Launch the app
qc$app()
```

## MySQL

```r
library(DBI)
library(RMySQL)
library(querychat)

# Connect to MySQL
conn <- dbConnect(
  RMySQL::MySQL(),
  dbname = "your_database",
  host = "localhost",
  user = "your_username",
  password = "your_password"
)

# Create QueryChat instance
qc <- QueryChat$new(conn, "your_table_name")

# Launch the app
qc$app()
```

## Connection Management

When using database sources in custom Shiny apps, make sure to properly manage connections:

```r
server <- function(input, output, session) {
  # Initialize QueryChat server
  qc$server()

  # Your custom outputs here
  output$table <- renderTable(qc$df())

  # Clean up connection when session ends
  session$onSessionEnded(function() {
    if (dbIsValid(conn)) {
      dbDisconnect(conn)
    }
  })
}
```

## Security Considerations

- Only SELECT queries are allowed - no INSERT, UPDATE, or DELETE operations
- All SQL queries are visible to users for transparency
- Use appropriate database user permissions (read-only recommended)
- Consider connection pooling for production applications
- Validate that users only have access to intended tables

## Error Handling

The database source implementation includes robust error handling:

- Validates table existence during creation
- Handles database connection issues gracefully
- Provides informative error messages for invalid queries
- Falls back gracefully when statistical queries fail

## Performance Tips

- Use appropriate database indexes for columns commonly used in queries
- Consider limiting row counts for very large tables
- Database connections are reused for better performance
- Schema information is cached to avoid repeated metadata queries