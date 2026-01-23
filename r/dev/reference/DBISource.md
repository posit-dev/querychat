# DBI Source

DBI Source

DBI Source

## Details

A DataSource implementation for DBI database connections (SQLite,
PostgreSQL, MySQL, etc.). This class wraps a DBI connection and provides
SQL query execution against a single table in the database.

## Super class

[`querychat::DataSource`](https://posit-dev.github.io/querychat/dev/reference/DataSource.md)
-\> `DBISource`

## Methods

### Public methods

- [`DBISource$new()`](#method-DBISource-new)

- [`DBISource$get_db_type()`](#method-DBISource-get_db_type)

- [`DBISource$get_schema()`](#method-DBISource-get_schema)

- [`DBISource$execute_query()`](#method-DBISource-execute_query)

- [`DBISource$test_query()`](#method-DBISource-test_query)

- [`DBISource$get_data()`](#method-DBISource-get_data)

- [`DBISource$cleanup()`](#method-DBISource-cleanup)

- [`DBISource$clone()`](#method-DBISource-clone)

------------------------------------------------------------------------

### Method `new()`

Create a new DBISource

#### Usage

    DBISource$new(conn, table_name)

#### Arguments

- `conn`:

  A DBI connection object

- `table_name`:

  Name of the table in the database. Can be a character string or a
  [`DBI::Id()`](https://dbi.r-dbi.org/reference/Id.html) object for
  tables in catalogs/schemas

#### Returns

A new DBISource object

------------------------------------------------------------------------

### Method `get_db_type()`

Get the database type

#### Usage

    DBISource$get_db_type()

#### Returns

A string identifying the database type

------------------------------------------------------------------------

### Method `get_schema()`

Get schema information for the database table

#### Usage

    DBISource$get_schema(categorical_threshold = 20)

#### Arguments

- `categorical_threshold`:

  Maximum number of unique values for a text column to be considered
  categorical (default: 20)

#### Returns

A string describing the schema

------------------------------------------------------------------------

### Method `execute_query()`

Execute a SQL query

#### Usage

    DBISource$execute_query(query)

#### Arguments

- `query`:

  SQL query string. If NULL or empty, returns all data

#### Returns

A data frame with query results

------------------------------------------------------------------------

### Method `test_query()`

Test a SQL query by fetching only one row

#### Usage

    DBISource$test_query(query, require_all_columns = FALSE)

#### Arguments

- `query`:

  SQL query string

- `require_all_columns`:

  If `TRUE`, validates that the result includes all original table
  columns (default: `FALSE`)

#### Returns

A data frame with one row of results

------------------------------------------------------------------------

### Method `get_data()`

Get all data from the table

#### Usage

    DBISource$get_data()

#### Returns

A data frame containing all data

------------------------------------------------------------------------

### Method `cleanup()`

Disconnect from the database

#### Usage

    DBISource$cleanup()

#### Returns

NULL (invisibly)

------------------------------------------------------------------------

### Method `clone()`

The objects of this class are cloneable with this method.

#### Usage

    DBISource$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.

## Examples

``` r
# Connect to a database
con <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
DBI::dbWriteTable(con, "mtcars", mtcars)

# Create a DBI source
db_source <- DBISource$new(con, "mtcars")

# Get database type
db_source$get_db_type()  # Returns "SQLite"
#> [1] "SQLite"

# Execute a query
result <- db_source$execute_query("SELECT * FROM mtcars WHERE mpg > 25")

# Note: cleanup() will disconnect the connection
# If you want to keep the connection open, don't call cleanup()
db_source$cleanup()
```
