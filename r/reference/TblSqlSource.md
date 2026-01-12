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

### Method `new()`

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

    TblSqlSource$test_query(query, require_all_columns = FALSE)

#### Arguments

- `query`:

  SQL query string to test

- `require_all_columns`:

  If `TRUE`, validates that the result includes all original table
  columns (default: `FALSE`)

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
con <- DBI::dbConnect(duckdb::duckdb())
DBI::dbWriteTable(con, "mtcars", mtcars)

mtcars_source <- TblSqlSource$new(dplyr::tbl(con, "mtcars"))
mtcars_source$get_db_type()  # "DuckDB"
#> [1] "DuckDB"

result <- mtcars_source$execute_query("SELECT * FROM mtcars WHERE cyl > 4")

# Note, the result is not the *full* data frame, but a lazy SQL tibble
result
#> # Source:   SQL [?? x 11]
#> # Database: DuckDB 1.4.3 [unknown@Linux 6.11.0-1018-azure:R 4.5.2/:memory:]
#>      mpg   cyl  disp    hp  drat    wt  qsec    vs    am  gear  carb
#>    <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl>
#>  1  21       6  160    110  3.9   2.62  16.5     0     1     4     4
#>  2  21       6  160    110  3.9   2.88  17.0     0     1     4     4
#>  3  21.4     6  258    110  3.08  3.22  19.4     1     0     3     1
#>  4  18.7     8  360    175  3.15  3.44  17.0     0     0     3     2
#>  5  18.1     6  225    105  2.76  3.46  20.2     1     0     3     1
#>  6  14.3     8  360    245  3.21  3.57  15.8     0     0     3     4
#>  7  19.2     6  168.   123  3.92  3.44  18.3     1     0     4     4
#>  8  17.8     6  168.   123  3.92  3.44  18.9     1     0     4     4
#>  9  16.4     8  276.   180  3.07  4.07  17.4     0     0     3     3
#> 10  17.3     8  276.   180  3.07  3.73  17.6     0     0     3     3
#> # ℹ more rows

# You can chain this result into a dplyr pipeline
dplyr::count(result, cyl, gear)
#> # Source:   SQL [?? x 3]
#> # Database: DuckDB 1.4.3 [unknown@Linux 6.11.0-1018-azure:R 4.5.2/:memory:]
#>     cyl  gear     n
#>   <dbl> <dbl> <dbl>
#> 1     6     5     1
#> 2     8     5     2
#> 3     6     4     4
#> 4     8     3    12
#> 5     6     3     2

# Or collect the entire data frame into local memory
dplyr::collect(result)
#> # A tibble: 21 × 11
#>      mpg   cyl  disp    hp  drat    wt  qsec    vs    am  gear  carb
#>    <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl> <dbl>
#>  1  21       6  160    110  3.9   2.62  16.5     0     1     4     4
#>  2  21       6  160    110  3.9   2.88  17.0     0     1     4     4
#>  3  21.4     6  258    110  3.08  3.22  19.4     1     0     3     1
#>  4  18.7     8  360    175  3.15  3.44  17.0     0     0     3     2
#>  5  18.1     6  225    105  2.76  3.46  20.2     1     0     3     1
#>  6  14.3     8  360    245  3.21  3.57  15.8     0     0     3     4
#>  7  19.2     6  168.   123  3.92  3.44  18.3     1     0     4     4
#>  8  17.8     6  168.   123  3.92  3.44  18.9     1     0     4     4
#>  9  16.4     8  276.   180  3.07  4.07  17.4     0     0     3     3
#> 10  17.3     8  276.   180  3.07  3.73  17.6     0     0     3     3
#> # ℹ 11 more rows

# Finally, clean up when done with the database (closes the DB connection)
mtcars_source$cleanup()
```
