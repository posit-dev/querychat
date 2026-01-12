# Data Frame Source

A DataSource implementation that wraps a data frame using DuckDB or
SQLite for SQL query execution.

## Details

This class creates an in-memory database connection and registers the
provided data frame as a table. All SQL queries are executed against
this database table. See
[DBISource](https://posit-dev.github.io/querychat/reference/DBISource.md)
for the full description of available methods.

By default, DataFrameSource uses the first available engine from duckdb
(checked first) or RSQLite. You can explicitly set the `engine`
parameter to choose between `"duckdb"` or `"sqlite"`, or set the global
option `querychat.DataFrameSource.engine` to choose the default engine
for all DataFrameSource instances. At least one of these packages must
be installed.

## Super classes

[`querychat::DataSource`](https://posit-dev.github.io/querychat/reference/DataSource.md)
-\>
[`querychat::DBISource`](https://posit-dev.github.io/querychat/reference/DBISource.md)
-\> `DataFrameSource`

## Methods

### Public methods

- [`DataFrameSource$new()`](#method-DataFrameSource-new)

- [`DataFrameSource$clone()`](#method-DataFrameSource-clone)

Inherited methods

- [`querychat::DBISource$cleanup()`](https://posit-dev.github.io/querychat/reference/DBISource.html#method-cleanup)
- [`querychat::DBISource$execute_query()`](https://posit-dev.github.io/querychat/reference/DBISource.html#method-execute_query)
- [`querychat::DBISource$get_data()`](https://posit-dev.github.io/querychat/reference/DBISource.html#method-get_data)
- [`querychat::DBISource$get_db_type()`](https://posit-dev.github.io/querychat/reference/DBISource.html#method-get_db_type)
- [`querychat::DBISource$get_schema()`](https://posit-dev.github.io/querychat/reference/DBISource.html#method-get_schema)
- [`querychat::DBISource$test_query()`](https://posit-dev.github.io/querychat/reference/DBISource.html#method-test_query)

------------------------------------------------------------------------

### Method `new()`

Create a new DataFrameSource

#### Usage

    DataFrameSource$new(
      df,
      table_name,
      engine = getOption("querychat.DataFrameSource.engine", NULL)
    )

#### Arguments

- `df`:

  A data frame.

- `table_name`:

  Name to use for the table in SQL queries. Must be a valid table name
  (start with letter, contain only letters, numbers, and underscores)

- `engine`:

  Database engine to use: "duckdb" or "sqlite". Set the global option
  `querychat.DataFrameSource.engine` to specify the default engine for
  all instances. If NULL (default), uses the first available engine from
  duckdb or RSQLite (in that order).

#### Returns

A new DataFrameSource object

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
# Create a data frame source (uses first available: duckdb or sqlite)
df_source <- DataFrameSource$new(mtcars, "mtcars")

# Get database type
df_source$get_db_type()  # Returns "DuckDB" or "SQLite"
#> [1] "DuckDB"

# Execute a query
result <- df_source$execute_query("SELECT * FROM mtcars WHERE mpg > 25")

# Explicitly choose an engine
df_sqlite <- DataFrameSource$new(mtcars, "mtcars", engine = "sqlite")

# Clean up when done
df_source$cleanup()
df_sqlite$cleanup()
```
