# QueryChat: Interactive Data Querying with Natural Language

`QueryChat` is an R6 class built on Shiny, shinychat, and ellmer to
enable interactive querying of data using natural language. It leverages
large language models (LLMs) to translate user questions into SQL
queries, execute them against a data source (data frame or database),
and various ways of accessing/displaying the results.

The `QueryChat` class takes your data (a data frame or database
connection) as input and provides methods to:

- Generate a chat UI for natural language queries (e.g., `$app()`,
  `$sidebar()`)

- Initialize server logic that returns session-specific reactive values
  (via `$server()`)

- Access reactive data, SQL queries, and titles through the returned
  server values (use `qc_vals$table("name")` for multi-table access)

## Usage in Shiny Apps

    library(querychat)

    # Create a QueryChat object
    qc <- QueryChat$new(mtcars)

    # Quick start: run a complete app
    qc$app()

    # Or build a custom Shiny app
    ui <- page_sidebar(
      qc$sidebar(),
      verbatimTextOutput("sql"),
      dataTableOutput("data")
    )

    server <- function(input, output, session) {
      qc_vals <- qc$server()

      output$sql <- renderText(qc_vals$sql())
      output$data <- renderDataTable(qc_vals$df())
    }

    shinyApp(ui, server)

## Public fields

- `greeting`:

  The greeting message displayed to users.

- `history`:

  Conversation history configuration.

- `id`:

  ID for the QueryChat instance.

- `id_override`:

  Whether the ID was explicitly set by the user.

- `tools`:

  The allowed tools for the chat client.

## Active bindings

- `greeter`:

  The QueryChatGreeter controlling greeting generation; access its
  `$tables` and `$prompt`.

- `system_prompt`:

  Get the system prompt.

- `data_source`:

  Removed. Use `$add_table()` and `$remove_table()` to manage tables.

## Methods

### Public methods

- [`QueryChat$new()`](#method-QueryChat-initialize)

- [`QueryChat$add_table()`](#method-QueryChat-add_table)

- [`QueryChat$add_tables()`](#method-QueryChat-add_tables)

- [`QueryChat$remove_table()`](#method-QueryChat-remove_table)

- [`QueryChat$table_names()`](#method-QueryChat-table_names)

- [`QueryChat$client()`](#method-QueryChat-client)

- [`QueryChat$console()`](#method-QueryChat-console)

- [`QueryChat$app()`](#method-QueryChat-app)

- [`QueryChat$app_obj()`](#method-QueryChat-app_obj)

- [`QueryChat$sidebar()`](#method-QueryChat-sidebar)

- [`QueryChat$ui()`](#method-QueryChat-ui)

- [`QueryChat$server()`](#method-QueryChat-server)

- [`QueryChat$generate_greeting()`](#method-QueryChat-generate_greeting)

- [`QueryChat$cleanup()`](#method-QueryChat-cleanup)

- [`QueryChat$clone()`](#method-QueryChat-clone)

------------------------------------------------------------------------

### `QueryChat$new()`

Create a new QueryChat object.

#### Usage

    QueryChat$new(
      data_source,
      table_name = missing_arg(),
      ...,
      id = NULL,
      greeting = NULL,
      history = NULL,
      client = NULL,
      tools = c("filter", "query"),
      data_description = NULL,
      categorical_threshold = 20,
      extra_instructions = NULL,
      prompt_template = NULL,
      data_dict = NULL,
      cleanup = NA
    )

#### Arguments

- `data_source`:

  Either a data.frame, a database connection (e.g., DBI connection), or
  `NULL` to defer setting the data source until later. When `NULL`, the
  data source must be added via `$add_table()` or passed to `$server()`
  before calling methods that require data access.

- `table_name`:

  A string specifying the table name to use in SQL queries. If
  `data_source` is a data.frame, this is the name to refer to it by in
  queries (typically the variable name). If not provided, will be
  inferred from the variable name for data.frame inputs. For database
  connections or `NULL` data sources, this parameter is required.

- `...`:

  Additional arguments (currently unused).

- `id`:

  Optional module ID for the QueryChat instance. If not provided, will
  be auto-generated from `table_name`. The ID is used to namespace the
  Shiny module.

- `greeting`:

  Optional initial message to display to users. Can be a character
  string (in Markdown format) or a file path. If not provided, a
  greeting will be generated at the start of each conversation using the
  LLM, which adds latency and cost. Use `$generate_greeting()` to create
  a greeting to save and reuse.

- `history`:

  Conversation history configuration: `NULL` (default; resolves to
  `TRUE` when `$server()`/`$app()` is called and nothing else was set),
  `TRUE`/`FALSE`, or a
  [`shinychat::history_options()`](https://posit-dev.github.io/shinychat/r/reference/history_options.html)
  object. Passed straight through to
  `shinychat::chat_server(history = )`.

- `client`:

  Optional chat client. Can be:

  - An [ellmer::Chat](https://ellmer.tidyverse.org/reference/Chat.html)
    object

  - A string to pass to
    [`ellmer::chat()`](https://ellmer.tidyverse.org/reference/chat-any.html)
    (e.g., `"openai/gpt-4o"`)

  - `NULL` (default): Uses the `querychat.client` option, the
    `QUERYCHAT_CLIENT` environment variable, or defaults to
    [`ellmer::chat_openai()`](https://ellmer.tidyverse.org/reference/chat_openai.html)

- `tools`:

  Which querychat tools to include in the chat client, by default.
  `"filter"` includes the tools for filtering and resetting the
  dashboard and `"query"` includes the tool for executing SQL queries.
  Use `tools = "filter"` when you only want the dashboard filtering
  tools, or when you want to disable the querying tool entirely to
  prevent the LLM from seeing any of the data in your dataset. The
  legacy name `"update"` is still accepted as an alias for `"filter"`.

- `data_description`:

  Optional description of the data in plain text or Markdown. Can be a
  string or a file path. This provides context to the LLM about what the
  data represents.

- `categorical_threshold`:

  For text columns, the maximum number of unique values to consider as a
  categorical variable. Default is 20.

- `extra_instructions`:

  Optional additional instructions for the chat model in plain text or
  Markdown. Can be a string or a file path.

- `prompt_template`:

  Optional path to or string of a custom prompt template file. If not
  provided, the default querychat template will be used. See the package
  prompts directory for the default template format.

- `data_dict`:

  Optional data dictionary. A path to a YAML file, or a list of YAML
  file paths. See
  [`read_data_dict()`](https://posit-dev.github.io/querychat/dev/reference/read_data_dict.md)
  for the expected format.

- `cleanup`:

  Whether or not to automatically run `$cleanup()` when the Shiny
  session/app stops. By default, cleanup only occurs if `QueryChat` gets
  created within a Shiny session. Set to `TRUE` to always clean up, or
  `FALSE` to never clean up automatically.

#### Returns

A new `QueryChat` object.

------------------------------------------------------------------------

### `QueryChat$add_table()`

Add a table to this QueryChat instance.

#### Usage

    QueryChat$add_table(
      data_source,
      table_name,
      replace = FALSE,
      include_in_greeting = FALSE
    )

#### Arguments

- `data_source`:

  A data frame, database connection, or DataSource object.

- `table_name`:

  The SQL table name for this data source.

- `replace`:

  Whether to replace an existing table with this name. Default is
  `FALSE`.

- `include_in_greeting`:

  Whether to include this table in the greeting context. Default is
  `FALSE`.

#### Returns

Invisibly returns `self` for chaining.

------------------------------------------------------------------------

### `QueryChat$add_tables()`

Add multiple tables from a DBI connection in a single call.

Unlike calling `$add_table()` repeatedly, this method builds the system
prompt exactly once after all tables have been staged, avoiding N-1
spurious intermediate rebuilds.

#### Usage

    QueryChat$add_tables(
      conn,
      tables = NULL,
      replace = FALSE,
      include_in_greeting = FALSE
    )

#### Arguments

- `conn`:

  A DBI connection. Only DBI connections are supported; pass individual
  data frames or other sources via `$add_table()`.

- `tables`:

  Table names to register. When `NULL`, all tables returned by
  `DBI::dbListTables(conn)` are used.

- `replace`:

  Whether to replace existing tables with the same name. Default is
  `FALSE`.

- `include_in_greeting`:

  Whether to include added tables in the greeting context. `TRUE`
  includes all tables; `FALSE` (default) includes none; a character
  vector includes only those named tables (intersected with the tables
  being added). Any other type raises an error.

#### Returns

Invisibly returns `self` for chaining.

------------------------------------------------------------------------

### `QueryChat$remove_table()`

Remove a table from this QueryChat instance.

#### Usage

    QueryChat$remove_table(table_name)

#### Arguments

- `table_name`:

  The name of the table to remove.

#### Returns

Invisibly returns `self` for chaining.

------------------------------------------------------------------------

### `QueryChat$table_names()`

Return the names of all registered tables.

#### Usage

    QueryChat$table_names()

------------------------------------------------------------------------

### `QueryChat$client()`

Create a chat client, complete with registered tools, for the current
data source.

#### Usage

    QueryChat$client(
      tools = NA,
      update_dashboard = function(query, title, table) {
     },
      reset_dashboard = function(table) {
     },
      visualize = function(data) {
     },
      session = NULL
    )

#### Arguments

- `tools`:

  Which querychat tools to include in the chat client. `"filter"`
  includes the tools for filtering and resetting the dashboard and
  `"query"` includes the tool for executing SQL queries. By default,
  when `tools = NA`, the values provided at initialization are used. The
  legacy name `"update"` is still accepted as an alias for `"filter"`.

- `update_dashboard`:

  Optional function to call with the `query`, `title`, and `table`
  generated by the LLM for the `update_dashboard` tool.

- `reset_dashboard`:

  Optional function to call when the `reset_dashboard` tool is called.
  Takes a `table` argument.

- `visualize`:

  Optional function to call with a list containing `ggsql`, `title`, and
  `widget_id` when a visualization succeeds.

- `session`:

  A Shiny session object. Required when `"visualize"` is in `tools` and
  you want interactive chart rendering. When `NULL` (the default),
  visualizations still execute but are not rendered as Shiny outputs.

------------------------------------------------------------------------

### `QueryChat$console()`

Launch a console-based chat interface with the data source.

#### Usage

    QueryChat$console(new = FALSE, ..., tools = "query")

#### Arguments

- `new`:

  Whether to create a new chat client instance or continue the
  conversation from the last console chat session (the default).

- `...`:

  Additional arguments passed to the `$client()` method.

- `tools`:

  Which querychat tools to include in the chat client. See `$client()`
  for details. Ignored when not creating a new chat client. By default,
  only the `"query"` tool is included, regardless of the `tools` set at
  initialization.

------------------------------------------------------------------------

### `QueryChat$app()`

Create and run a Shiny gadget for chatting with data

#### Usage

    QueryChat$app(..., history = NULL)

#### Arguments

- `...`:

  Arguments passed to `$app_obj()`.

- `history`:

  Conversation history configuration for the generated app. Defaults to
  `shinychat::history_options(restore_mode = "bookmark")` when neither
  this nor `$new()`'s `history` was set, since `$app()`'s whole purpose
  is a single, shareable demo. When the resolved value has
  `restore_mode = "bookmark"`, the generated app automatically enables
  Shiny's own server-side bookmarking.

#### Returns

Invisibly returns a list of session-specific values.

------------------------------------------------------------------------

### `QueryChat$app_obj()`

A streamlined Shiny app for chatting with data

#### Usage

    QueryChat$app_obj(..., history = NULL)

#### Arguments

- `...`:

  Additional arguments (currently unused).

- `history`:

  Conversation history configuration for the generated app. See
  `$app()`.

#### Returns

A Shiny app object that can be run with
[`shiny::runApp()`](https://rdrr.io/pkg/shiny/man/runApp.html).

------------------------------------------------------------------------

### `QueryChat$sidebar()`

Create a sidebar containing the querychat UI.

#### Usage

    QueryChat$sidebar(
      ...,
      width = 400,
      height = "100%",
      fillable = TRUE,
      id = NULL
    )

#### Arguments

- `...`:

  Additional arguments passed to
  [`bslib::sidebar()`](https://rstudio.github.io/bslib/reference/sidebar.html).

- `width`:

  Width of the sidebar in pixels. Default is 400.

- `height`:

  Height of the sidebar. Default is "100%".

- `fillable`:

  Whether the sidebar should be fillable. Default is `TRUE`.

- `id`:

  Optional ID for the QueryChat instance.

#### Returns

A
[`bslib::sidebar()`](https://rstudio.github.io/bslib/reference/sidebar.html)
UI component.

------------------------------------------------------------------------

### `QueryChat$ui()`

Create the UI for the querychat chat interface.

#### Usage

    QueryChat$ui(..., id = NULL)

#### Arguments

- `...`:

  Additional arguments passed to
  [`shinychat::chat_ui()`](https://posit-dev.github.io/shinychat/r/reference/chat_ui.html).

- `id`:

  Optional ID for the QueryChat instance.

#### Returns

A UI component containing the chat interface.

------------------------------------------------------------------------

### `QueryChat$server()`

Initialize the querychat server logic.

#### Usage

    QueryChat$server(
      data_source = NULL,
      client = NULL,
      history = NULL,
      enable_bookmarking = NULL,
      ...,
      id = NULL,
      session = shiny::getDefaultReactiveDomain()
    )

#### Arguments

- `data_source`:

  Optional data source for backward compatibility. If provided, calls
  `$add_table()` before initializing server logic.

- `client`:

  Optional chat client override for this session.

- `history`:

  Conversation history configuration for this call. Overrides the value
  set on `$new()`. Resolves to `TRUE` when neither this nor the
  constructor's `history` was set.

- `enable_bookmarking`:

  **\[deprecated\]** Use
  `history = shinychat::history_options(restore_mode = "bookmark")`
  instead (set on `$new()`, or passed here).

- `...`:

  Ignored.

- `id`:

  Optional module ID override.

- `session`:

  The Shiny session object.

#### Returns

A list containing session-specific reactive values and the chat client.
For single-table usage, includes `df`, `sql`, `title` directly. For
multi-table, use `qc_vals$table("name")` to get a
[TableAccessor](https://posit-dev.github.io/querychat/dev/reference/TableAccessor.md)
with per-table reactive state. Also includes `table_names()` to list
tables. `current_table()` returns the name of the most recently queried
table, or `NULL` before any query.

------------------------------------------------------------------------

### `QueryChat$generate_greeting()`

Generate a welcome greeting for the chat.

#### Usage

    QueryChat$generate_greeting(echo = c("none", "output"))

#### Arguments

- `echo`:

  Whether to print the greeting to the console.

#### Returns

The greeting string in Markdown format.

------------------------------------------------------------------------

### `QueryChat$cleanup()`

Clean up resources associated with the data source.

#### Usage

    QueryChat$cleanup()

#### Returns

Invisibly returns `NULL`. Resources are cleaned up internally.

------------------------------------------------------------------------

### `QueryChat$clone()`

The objects of this class are cloneable with this method.

#### Usage

    QueryChat$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.

## Examples

``` r
# Basic usage with a data frame
qc <- QueryChat$new(mtcars)
if (FALSE) { # \dontrun{
app <- qc$app()
} # }

# With a custom greeting
greeting <- "Welcome! Ask me about the mtcars dataset."
qc <- QueryChat$new(mtcars, greeting = greeting)

# With a specific LLM provider
qc <- QueryChat$new(mtcars, client = "anthropic/claude-sonnet-4-5")

# Generate a greeting for reuse (requires internet/API access)
if (FALSE) { # \dontrun{
qc <- QueryChat$new(mtcars)
greeting <- qc$generate_greeting(echo = "text")
# Save greeting for next time
writeLines(greeting, "mtcars_greeting.md")
} # }

# Or specify greeting and additional options at initialization
qc <- QueryChat$new(
  mtcars,
  greeting = "Welcome to the mtcars explorer!",
  client = "openai/gpt-4o",
  data_description = "Motor Trend car road tests dataset"
)
# Create a QueryChat object from a database connection
# 1. Set up the database connection
con <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")

# 2. (For this demo) Create a table in the database
DBI::dbWriteTable(con, "mtcars", mtcars)

# 3. Pass the connection and table name to `QueryChat`
qc <- QueryChat$new(con, "mtcars")
```
