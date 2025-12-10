# Data Frame Source

A DataSource implementation that wraps a data frame using DuckDB for SQL
query execution.

## Details

This class creates an in-memory DuckDB connection and registers the
provided data frame as a table. All SQL queries are executed against
this DuckDB table.

## Super class

[`querychat::DataSource`](https://posit-dev.github.io/querychat/dev/reference/DataSource.md)
-\> `DataFrameSource`

## Methods

### Public methods

- [`DataFrameSource$new()`](#method-DataFrameSource-new)

- [`DataFrameSource$get_db_type()`](#method-DataFrameSource-get_db_type)

- [`DataFrameSource$get_schema()`](#method-DataFrameSource-get_schema)

- [`DataFrameSource$execute_query()`](#method-DataFrameSource-execute_query)

- [`DataFrameSource$test_query()`](#method-DataFrameSource-test_query)

- [`DataFrameSource$get_data()`](#method-DataFrameSource-get_data)

- [`DataFrameSource$cleanup()`](#method-DataFrameSource-cleanup)

- [`DataFrameSource$clone()`](#method-DataFrameSource-clone)

------------------------------------------------------------------------

### Method [`new()`](https://rdrr.io/r/methods/new.html)

Create a new DataFrameSource

#### Usage

    DataFrameSource$new(df, table_name)

#### Arguments

- `df`:

  A data frame.

- `table_name`:

  Name to use for the table in SQL queries. Must be a valid table name
  (start with letter, contain only letters, numbers, and underscores)

#### Returns

A new DataFrameSource object

#### Examples

    \dontrun{
    source <- DataFrameSource$new(iris, "iris")
    }

------------------------------------------------------------------------

### Method `get_db_type()`

Get the database type

#### Usage

    DataFrameSource$get_db_type()

#### Returns

The string "DuckDB"

------------------------------------------------------------------------

### Method `get_schema()`

Get schema information for the data frame

#### Usage

    DataFrameSource$get_schema(categorical_threshold = 20)

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

    DataFrameSource$execute_query(query)

#### Arguments

- `query`:

  SQL query string. If NULL or empty, returns all data

#### Returns

A data frame with query results

------------------------------------------------------------------------

### Method `test_query()`

Test a SQL query by fetching only one row

#### Usage

    DataFrameSource$test_query(query)

#### Arguments

- `query`:

  SQL query string

#### Returns

A data frame with one row of results

------------------------------------------------------------------------

### Method `get_data()`

Get all data from the table

#### Usage

    DataFrameSource$get_data()

#### Returns

A data frame containing all data

------------------------------------------------------------------------

### Method `cleanup()`

Close the DuckDB connection

#### Usage

    DataFrameSource$cleanup()

#### Returns

NULL (invisibly)

------------------------------------------------------------------------

### Method `clone()`

The objects of this class are cloneable with this method.

#### Usage

    DataFrameSource$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.

## Examples

``` r
if (FALSE) { # \dontrun{
# Create a data frame source
df_source <- DataFrameSource$new(mtcars, "mtcars")

# Get database type
df_source$get_db_type()  # Returns "DuckDB"

# Execute a query
result <- df_source$execute_query("SELECT * FROM mtcars WHERE mpg > 25")

# Clean up when done
df_source$cleanup()
} # }

## ------------------------------------------------
## Method `DataFrameSource$new`
## ------------------------------------------------

if (FALSE) { # \dontrun{
source <- DataFrameSource$new(iris, "iris")
} # }
```
