# Table Accessor

Accessor for a specific table's data source and per-table reactive
state. Returned by the server return value's `$table("name")` method.

## Active bindings

- `table_name`:

  The name of this table.

- `data_source`:

  The DataSource for this table.

## Methods

### Public methods

- [`TableAccessor$new()`](#method-TableAccessor-initialize)

- [`TableAccessor$df()`](#method-TableAccessor-df)

- [`TableAccessor$sql()`](#method-TableAccessor-sql)

- [`TableAccessor$title()`](#method-TableAccessor-title)

- [`TableAccessor$clone()`](#method-TableAccessor-clone)

------------------------------------------------------------------------

### `TableAccessor$new()`

Create a new TableAccessor.

#### Usage

    TableAccessor$new(table_name, data_source, state)

#### Arguments

- `table_name`:

  The name of the table.

- `data_source`:

  The DataSource for this table.

- `state`:

  List of per-table reactive state (`sql`, `title`, `df`).

------------------------------------------------------------------------

### `TableAccessor$df()`

Return the current filtered data for this table.

#### Usage

    TableAccessor$df()

------------------------------------------------------------------------

### `TableAccessor$sql()`

Return the current SQL filter for this table.

#### Usage

    TableAccessor$sql()

------------------------------------------------------------------------

### `TableAccessor$title()`

Return the current filter title for this table.

#### Usage

    TableAccessor$title()

------------------------------------------------------------------------

### `TableAccessor$clone()`

The objects of this class are cloneable with this method.

#### Usage

    TableAccessor$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.
