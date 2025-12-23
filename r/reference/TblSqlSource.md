# Data Source: SQL Tibble

A DataSource implementation for lazy SQL tibbles connected to databases
via
[`dbplyr::tbl_sql()`](https://dbplyr.tidyverse.org/reference/tbl_sql.html)
or [`dplyr::sql()`](https://dplyr.tidyverse.org/reference/sql.html).

## Super classes

[`querychat::DataSource`](https://posit-dev.github.io/querychat/reference/DataSource.md)
-\>
[`querychat::DBISource`](https://posit-dev.github.io/querychat/reference/DBISource.md)
-\> `TblSqlSource`

## Public fields

- `table_name`:

  Name of the table to be used in SQL queries

## Methods

### Public methods

- [`TblSqlSource$new()`](#method-TblSqlSource-new)

- [`TblSqlSource$get_db_type()`](#method-TblSqlSource-get_db_type)

- [`TblSqlSource$get_schema()`](#method-TblSqlSource-get_schema)

- [`TblSqlSource$execute_query()`](#method-TblSqlSource-execute_query)

- [`TblSqlSource$test_query()`](#method-TblSqlSource-test_query)

- [`TblSqlSource$prep_query()`](#method-TblSqlSource-prep_query)

- [`TblSqlSource$get_data()`](#method-TblSqlSource-get_data)

- [`TblSqlSource$cleanup()`](#method-TblSqlSource-cleanup)

- [`TblSqlSource$clone()`](#method-TblSqlSource-clone)

------------------------------------------------------------------------

### Method [`new()`](https://rdrr.io/r/methods/new.html)

Create a new TblSqlSource

#### Usage

    TblSqlSource$new(tbl, table_name = missing_arg())

#### Arguments

- `tbl`:

  A
  [`dbplyr::tbl_sql()`](https://dbplyr.tidyverse.org/reference/tbl_sql.html)
  (or SQL tibble via
  [`dplyr::tbl()`](https://dplyr.tidyverse.org/reference/tbl.html)).

- `table_name`:

  Name of the table in the database. Can be a character string, or will
  be inferred from the `tbl` argument, if possible.

#### Returns

A new TblSqlSource object

------------------------------------------------------------------------

### Method `get_db_type()`

Get the database type

#### Usage

    TblSqlSource$get_db_type()

#### Returns

A string describing the database type (e.g., "DuckDB", "SQLite")

------------------------------------------------------------------------

### Method `get_schema()`

Get schema information about the table

#### Usage

    TblSqlSource$get_schema(categorical_threshold = 20)

#### Arguments

- `categorical_threshold`:

  Maximum number of unique values for a text column to be considered
  categorical

#### Returns

A string containing schema information formatted for LLM prompts

------------------------------------------------------------------------

### Method `execute_query()`

Execute a SQL query and return results

#### Usage

    TblSqlSource$execute_query(query)

#### Arguments

- `query`:

  SQL query string to execute

#### Returns

A data frame containing query results

------------------------------------------------------------------------

### Method `test_query()`

Test a SQL query by fetching only one row

#### Usage

    TblSqlSource$test_query(query)

#### Arguments

- `query`:

  SQL query string to test

#### Returns

A data frame containing one row of results (or empty if no matches)

------------------------------------------------------------------------

### Method `prep_query()`

Prepare a generic `SELECT * FROM ____` query to work with the SQL tibble

#### Usage

    TblSqlSource$prep_query(query)

#### Arguments

- `query`:

  SQL query as a string

#### Returns

A complete SQL query string

------------------------------------------------------------------------

### Method `get_data()`

Get the unfiltered data as a SQL tibble

#### Usage

    TblSqlSource$get_data()

#### Returns

A
[`dbplyr::tbl_sql()`](https://dbplyr.tidyverse.org/reference/tbl_sql.html)
containing the original, unfiltered data

------------------------------------------------------------------------

### Method `cleanup()`

Clean up resources (close connections, etc.)

#### Usage

    TblSqlSource$cleanup()

#### Returns

NULL (invisibly)

------------------------------------------------------------------------

### Method `clone()`

The objects of this class are cloneable with this method.

#### Usage

    TblSqlSource$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.

## Examples

``` r
if (FALSE) { # rlang::is_interactive() && rlang::is_installed("dbplyr") && rlang::is_installed("dplyr") && rlang::is_installed("duckdb")
con <- DBI::dbConnect(duckdb::duckdb())
DBI::dbWriteTable(con, "mtcars", mtcars)

mtcars_source <- TblSqlSource$new(dplyr::tbl(con, "mtcars"))
mtcars_source$get_db_type()  # "DuckDB"

result <- mtcars_source$execute_query("SELECT * FROM mtcars WHERE cyl > 4")

# Note, the result is not the *full* data frame, but a lazy SQL tibble
result

# You can chain this result into a dplyr pipeline
dplyr::count(result, cyl, gear)

# Or collect the entire data frame into local memory
dplyr::collect(result)

# Finally, clean up when done with the database (closes the DB connection)
mtcars_source$cleanup()
}
if (FALSE) { # rlang::is_interactive() && rlang::is_installed("dbplyr") && rlang::is_installed("dplyr") && rlang::is_installed("RSQLite")
con <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
DBI::dbWriteTable(con, "mtcars", mtcars)
source <- TblSqlSource$new(dplyr::tbl(con, "mtcars"))
}
```
