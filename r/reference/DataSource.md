# Data Source Base Class

An abstract R6 class defining the interface that custom QueryChat data
sources must implement. This class should not be instantiated directly;
instead, use one of its concrete implementations like
[DataFrameSource](https://posit-dev.github.io/querychat/reference/DataFrameSource.md)
or
[DBISource](https://posit-dev.github.io/querychat/reference/DBISource.md).

## Public fields

- `table_name`:

  Name of the table to be used in SQL queries

## Methods

### Public methods

- [`DataSource$get_db_type()`](#method-DataSource-get_db_type)

- [`DataSource$get_schema()`](#method-DataSource-get_schema)

- [`DataSource$execute_query()`](#method-DataSource-execute_query)

- [`DataSource$test_query()`](#method-DataSource-test_query)

- [`DataSource$get_data()`](#method-DataSource-get_data)

- [`DataSource$cleanup()`](#method-DataSource-cleanup)

- [`DataSource$clone()`](#method-DataSource-clone)

------------------------------------------------------------------------

### Method `get_db_type()`

Get the database type

#### Usage

    DataSource$get_db_type()

#### Returns

A string describing the database type (e.g., "DuckDB", "SQLite")

------------------------------------------------------------------------

### Method `get_schema()`

Get schema information about the table

#### Usage

    DataSource$get_schema(categorical_threshold = 20)

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

    DataSource$execute_query(query)

#### Arguments

- `query`:

  SQL query string to execute

#### Returns

A data frame containing query results

------------------------------------------------------------------------

### Method `test_query()`

Test a SQL query by fetching only one row

#### Usage

    DataSource$test_query(query, require_all_columns = FALSE)

#### Arguments

- `query`:

  SQL query string to test

- `require_all_columns`:

  If TRUE, validates that the result includes all original table columns
  (default: FALSE)

#### Returns

A data frame containing one row of results (or empty if no matches)

------------------------------------------------------------------------

### Method `get_data()`

Get the unfiltered data as a data frame

#### Usage

    DataSource$get_data()

#### Returns

A data frame containing all data from the table

------------------------------------------------------------------------

### Method `cleanup()`

Clean up resources (close connections, etc.)

#### Usage

    DataSource$cleanup()

#### Returns

NULL (invisibly)

------------------------------------------------------------------------

### Method `clone()`

The objects of this class are cloneable with this method.

#### Usage

    DataSource$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.
