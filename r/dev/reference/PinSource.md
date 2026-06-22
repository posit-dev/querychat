# Pin Source

A DataSource implementation that reads data from a
[pins](https://pins.rstudio.com/) board. When the `"duckdb"` engine is
used and the pin type is one DuckDB can read natively (parquet, CSV,
JSON), the data is loaded directly from the cached pin files into DuckDB
without deserializing into R. For other pin types (e.g. RDS), or when
the `"sqlite"` engine is used, the data is deserialized via `pin_read()`
and must produce a data frame (or tibble), which is then registered with
the chosen engine just like
[DataFrameSource](https://posit-dev.github.io/querychat/dev/reference/DataFrameSource.md).

When loaded into DuckDB, the connection's external file access is locked
down so that LLM-generated SQL cannot reach the filesystem.

If the pin has a title, description, or tags,
[QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md)
uses them as the default `data_description`, which you can override.

## Lazy queries with pins

`PinSource` materializes the full dataset into DuckDB. For large parquet
pins where you want lazy query execution, read the pin files yourself
and pass a `tbl_sql` to
[`querychat()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
instead:

    paths <- pins::pin_download(board, "my_pin")
    con <- DBI::dbConnect(duckdb::duckdb())
    DBI::dbExecute(
      con,
      sprintf("CREATE VIEW my_pin AS SELECT * FROM read_parquet('%s')", paths[1])
    )
    qc <- querychat(dplyr::tbl(con, "my_pin"))

The pin files are still downloaded to a local cache — `pin_download()`
always fetches them. But rather than loading everything into memory,
DuckDB reads the parquet file lazily through dbplyr.

This approach skips the security lockdown that `PinSource` applies, so
LLM-generated SQL can access files on the local system.

## Super classes

[`DataSource`](https://posit-dev.github.io/querychat/dev/reference/DataSource.md)
-\>
[`DBISource`](https://posit-dev.github.io/querychat/dev/reference/DBISource.md)
-\> `PinSource`

## Methods

### Public methods

- [`PinSource$new()`](#method-PinSource-initialize)

- [`PinSource$get_data_description()`](#method-PinSource-get_data_description)

- [`PinSource$clone()`](#method-PinSource-clone)

Inherited methods

- [`DBISource$cleanup()`](https://posit-dev.github.io/querychat/dev/reference/DBISource.html#method-cleanup)
- [`DBISource$execute_query()`](https://posit-dev.github.io/querychat/dev/reference/DBISource.html#method-execute_query)
- [`DBISource$get_data()`](https://posit-dev.github.io/querychat/dev/reference/DBISource.html#method-get_data)
- [`DBISource$get_db_type()`](https://posit-dev.github.io/querychat/dev/reference/DBISource.html#method-get_db_type)
- [`DBISource$get_schema()`](https://posit-dev.github.io/querychat/dev/reference/DBISource.html#method-get_schema)
- [`DBISource$get_semantic_views_description()`](https://posit-dev.github.io/querychat/dev/reference/DBISource.html#method-get_semantic_views_description)
- [`DBISource$test_query()`](https://posit-dev.github.io/querychat/dev/reference/DBISource.html#method-test_query)

------------------------------------------------------------------------

### `PinSource$new()`

Create a new PinSource

#### Usage

    PinSource$new(
      board,
      name,
      ...,
      table_name = name,
      version = NULL,
      engine = getOption("querychat.DataFrameSource.engine", NULL)
    )

#### Arguments

- `board`:

  A pins board object (e.g. from
  [`pins::board_folder()`](https://pins.rstudio.com/reference/board_folder.html)
  or
  [`pins::board_connect()`](https://pins.rstudio.com/reference/board_connect.html)).

- `name`:

  Name of the pin to read.

- `...`:

  Not used; included for extensibility.

- `table_name`:

  Name to use for the table in SQL queries. Defaults to the pin name.

- `version`:

  Pin version to read. If `NULL` (default), reads the latest version.

- `engine`:

  Database engine to use: `"duckdb"` or `"sqlite"`. Set the global
  option `querychat.DataFrameSource.engine` to specify the default
  engine. If `NULL` (default), uses the first available engine from
  duckdb or RSQLite (in that order). Parquet, CSV, and JSON pins are
  read most efficiently with the `"duckdb"` engine; with `"sqlite"` they
  are deserialized via `pin_read()` instead.

#### Returns

A new PinSource object

------------------------------------------------------------------------

### `PinSource$get_data_description()`

Get a human-readable description of the pin for use in the system
prompt.

#### Usage

    PinSource$get_data_description()

#### Returns

A string with the pin title, description, and tags, or an empty string
if none are set.

------------------------------------------------------------------------

### `PinSource$clone()`

The objects of this class are cloneable with this method.

#### Usage

    PinSource$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.

## Examples

``` r
if (rlang::is_installed(c("pins", "duckdb"))) {
  # Create a temporary board and pin some data
  board <- pins::board_temp()
  pins::pin_write(board, mtcars, "mtcars", type = "parquet")

  # Create a PinSource
  ps <- PinSource$new(board, "mtcars")

  # Query the pinned data
  ps$execute_query("SELECT * FROM mtcars WHERE mpg > 25")

  ps$cleanup()
}
#> Creating new version '20260622T150102Z-c0340'
#> Writing to pin 'mtcars'
```
