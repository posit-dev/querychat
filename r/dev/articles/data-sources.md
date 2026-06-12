# Data Sources

`querychat` supports several different data sources, including:

1.  Data frames
2.  DBI database connections (e.g., SQLite, PostgreSQL, MySQL, DuckDB)
3.  [Pins](https://pins.rstudio.com/) boards
4.  Custom `DataSource` interfaces

The sections below describe how to use each type of data source with
`querychat`.

## Data frames

You can use any data frame as a data source in `querychat`. Simply pass
it to
[`querychat()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md):

``` r

library(querychat)
library(palmerpenguins)

qc <- querychat(mtcars)
qc$app()  # Launch the app
```

Behind the scenes, `querychat` creates an in-memory DuckDB database and
registers your data frame as a table for SQL query execution.

## Database connections

You can also connect `querychat` directly to a table in any database
supported by [DBI](https://dbi.r-dbi.org/). This includes popular
databases like SQLite, DuckDB, PostgreSQL, MySQL, and many more.

Assuming you have a database set up and accessible, you can create a DBI
connection and pass it to
[`querychat()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md).
Below are some examples for common databases.

### DuckDB

``` r

library(DBI)
library(duckdb)
library(querychat)

# Connect to a DuckDB database file
con <- dbConnect(duckdb::duckdb(), dbdir = "my_database.duckdb")

qc <- querychat(con, "my_table")
qc$app()  # Launch the app

# Don't forget to disconnect when done
# dbDisconnect(con)
```

### SQLite

``` r

library(DBI)
library(RSQLite)
library(querychat)

# Connect to a SQLite database file
con <- dbConnect(RSQLite::SQLite(), "my_database.db")

qc <- querychat(con, "my_table")
qc$app()  # Launch the app

# Don't forget to disconnect when done
# dbDisconnect(con)
```

### PostgreSQL

``` r

library(DBI)
library(RPostgres)
library(querychat)

# Connect to PostgreSQL
con <- dbConnect(
  RPostgres::Postgres(),
  host = "localhost",
  port = 5432,
  dbname = "mydatabase",
  user = "myuser",
  password = "mypassword"
)

qc <- querychat(con, "my_table")
qc$app()  # Launch the app

# Don't forget to disconnect when done
# dbDisconnect(con)
```

### MySQL

``` r

library(DBI)
library(RMariaDB)
library(querychat)

# Connect to MySQL
con <- dbConnect(
  RMariaDB::MariaDB(),
  host = "localhost",
  port = 3306,
  dbname = "mydatabase",
  user = "myuser",
  password = "mypassword"
)

qc <- querychat(con, "my_table")
qc$app()  # Launch the app

# Don't forget to disconnect when done
# dbDisconnect(con)
```

## Creating a database from a data frame

If you don’t have a database set up, you can easily create a local
DuckDB database from a data frame:

``` r

library(DBI)
library(duckdb)

con <- dbConnect(duckdb::duckdb(), dbdir = "my_database.duckdb")

# Write a data frame to the database
dbWriteTable(con, "penguins", penguins)

# Or from CSV
duckdb::duckdb_read_csv(con, "my_table", "path/to/your/file.csv")
```

Then you can connect to this database using the DuckDB example above.

## Pins

You can pass a [pins](https://pins.rstudio.com/) board directly to
[`querychat()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
with the pin name as `table_name`:

``` r

library(pins)
library(querychat)

board <- board_connect()

qc <- querychat(board, "my_pin")
qc$app()
```

The pin is read and loaded into an in-memory DuckDB database, the same
as data frames. For parquet, CSV, and JSON pins, the cached files go
straight into DuckDB without R deserialization. Other pin types
(e.g. RDS) go through
[`pin_read()`](https://pins.rstudio.com/reference/pin_read.html) first.

If the pin has a title, description, or tags, querychat uses them as the
default `data_description`, which you can override.

Pin names with special characters (like `"user.name/my_pin"`) are
sanitized into valid SQL table names. To control the table name
yourself, use `PinSource`:

``` r

ps <- PinSource$new(board, "user.name/my_pin", table_name = "my_data")
qc <- querychat(ps)
```

### Lazy queries with pins

By default, the full dataset is materialized into DuckDB. For large
parquet pins, you can skip that step by reading the pin files yourself
and passing a `tbl_sql`:

``` r

library(pins)
library(dplyr)
library(duckdb)
library(querychat)

board <- board_connect()
paths <- pin_download(board, "my_pin")

con <- dbConnect(duckdb::duckdb())
DBI::dbExecute(
  con,
  sprintf("CREATE VIEW my_pin AS SELECT * FROM read_parquet('%s')", paths[1])
)

qc <- querychat(tbl(con, "my_pin"))
qc$app()
```

The pin files are still downloaded to a local cache —
[`pin_download()`](https://pins.rstudio.com/reference/pin_download.html)
always fetches them. But rather than loading everything into memory,
DuckDB reads the parquet file lazily through dbplyr. This is not the
same as a database-backed source, where data never leaves the server.

This approach skips the security lockdown that `PinSource` applies, so
LLM-generated SQL can access files on the local system.

## Custom sources

If you have a custom data source that doesn’t fit into the above
categories, you can implement the `DataSource` interface. See the
[DataSource
reference](https://posit-dev.github.io/querychat/dev/reference/DataSource.md)
for more details on implementing this interface.
