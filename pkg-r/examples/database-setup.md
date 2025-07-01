# Database Setup Examples for querychat

This document provides examples of how to set up querychat with various database types using the new `database_source()` functionality.

## SQLite

```r
library(DBI)
library(RSQLite)
library(querychat)

# Connect to SQLite database
conn <- dbConnect(RSQLite::SQLite(), "path/to/your/database.db")

# Create database source
db_source <- database_source(conn, "your_table_name")

# Initialize querychat
config <- querychat_init(
  data_source = db_source,
  greeting = "Welcome! Ask me about your data.",
  data_description = "Description of your data..."
)
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

# Create database source
db_source <- database_source(conn, "your_table_name")

# Initialize querychat
config <- querychat_init(data_source = db_source)
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

# Create database source
db_source <- database_source(conn, "your_table_name")

# Initialize querychat
config <- querychat_init(data_source = db_source)
```

## Connection Management

When using database sources in Shiny apps, make sure to properly manage connections:

```r
server <- function(input, output, session) {
  # Your querychat server logic here
  chat <- querychat_server("chat", querychat_config)
  
  # Clean up connection when session ends
  session$onSessionEnded(function() {
    if (dbIsValid(conn)) {
      dbDisconnect(conn)
    }
  })
}
```

## Configuration Options

The `database_source()` function accepts a `categorical_threshold` parameter:

```r
# Columns with <= 50 unique values will be treated as categorical
db_source <- database_source(conn, "table_name", categorical_threshold = 50)
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