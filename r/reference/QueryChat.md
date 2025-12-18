# QueryChat: Interactive Data Querying with Natural Language

`QueryChat` is an R6 class built on Shiny, shinychat, and ellmer to
enable interactive querying of data using natural language. It leverages
large language models (LLMs) to translate user questions into SQL
queries, execute them against a data source (data frame or database),
and various ways of accessing/displaying the results.

## Details

The `QueryChat` class takes your data (a data frame or database
connection) as input and provides methods to:

- Generate a chat UI for natural language queries (e.g., `$app()`,
  `$sidebar()`)

- Initialize server logic that returns session-specific reactive values
  (via `$server()`)

- Access reactive data, SQL queries, and titles through the returned
  server values

## Usage

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

- `id`:

  ID for the QueryChat instance.

- `tools`:

  The allowed tools for the chat client.

## Active bindings

- `system_prompt`:

  Get the system prompt.

- `data_source`:

  Get the current data source.

## Methods

### Public methods

- [`QueryChat$new()`](#method-QueryChat-new)

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

### Method [`new()`](https://rdrr.io/r/methods/new.html)

Create a new QueryChat object.

#### Usage

    QueryChat$new(
      data_source,
      table_name = missing_arg(),
      ...,
      id = NULL,
      greeting = NULL,
      client = NULL,
      tools = c("update", "query"),
      data_description = NULL,
      categorical_threshold = 20,
      extra_instructions = NULL,
      prompt_template = NULL,
      cleanup = NA
    )

#### Arguments

- `data_source`:

  Either a data.frame or a database connection (e.g., DBI connection).

- `table_name`:

  A string specifying the table name to use in SQL queries. If
  `data_source` is a data.frame, this is the name to refer to it by in
  queries (typically the variable name). If not provided, will be
  inferred from the variable name for data.frame inputs. For database
  connections, this parameter is required.

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
  `"update"` includes the tools for updating and resetting the dashboard
  and `"query"` includes the tool for executing SQL queries. Use
  `tools = "update"` when you only want the dashboard updating tools, or
  when you want to disable the querying tool entirely to prevent the LLM
  from seeing any of the data in your dataset.

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

- `cleanup`:

  Whether or not to automatically run `$cleanup()` when the Shiny
  session/app stops. By default, cleanup only occurs if `QueryChat` gets
  created within a Shiny session. Set to `TRUE` to always clean up, or
  `FALSE` to never clean up automatically.

#### Returns

A new `QueryChat` object.

#### Examples

    \dontrun{
    # Basic usage
    qc <- QueryChat$new(mtcars)

    # With options
    qc <- QueryChat$new(
      mtcars,
      greeting = "Welcome to the mtcars explorer!",
      client = "openai/gpt-4o",
      data_description = "Motor Trend car road tests dataset"
    )

    # With database
    library(DBI)
    conn <- dbConnect(RSQLite::SQLite(), ":memory:")
    dbWriteTable(conn, "mtcars", mtcars)
    qc <- QueryChat$new(conn, "mtcars")
    }

------------------------------------------------------------------------

### Method `client()`

Create a chat client, complete with registered tools, for the current
data source.

#### Usage

    QueryChat$client(
      tools = NA,
      update_dashboard = function(query, title) {
     },
      reset_dashboard = function() {
     }
    )

#### Arguments

- `tools`:

  Which querychat tools to include in the chat client. `"update"`
  includes the tools for updating and resetting the dashboard and
  `"query"` includes the tool for executing SQL queries. By default,
  when `tools = NA`, the values provided at initialization are used.

- `update_dashboard`:

  Optional function to call with the `query` and `title` generated by
  the LLM for the `update_dashboard` tool.

- `reset_dashboard`:

  Optional function to call when the `reset_dashboard` tool is called.

------------------------------------------------------------------------

### Method `console()`

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

### Method `app()`

Create and run a Shiny gadget for chatting with data

Runs a Shiny gadget (designed for interactive use) that provides a
complete interface for chatting with your data using natural language.
If you're looking to deploy this app or run it through some other means,
see `$app_obj()`.

#### Usage

    QueryChat$app(..., bookmark_store = "url")

#### Arguments

- `...`:

  Arguments passed to `$app_obj()`.

- `bookmark_store`:

  The bookmarking storage method. Passed to
  [`shiny::enableBookmarking()`](https://rdrr.io/pkg/shiny/man/enableBookmarking.html).
  If `"url"` or `"server"`, the chat state (including current query)
  will be bookmarked. Default is `"url"`.

#### Returns

Invisibly returns a list of session-specific values:

- `df`: The final filtered data frame

- `sql`: The final SQL query string

- `title`: The final title

- `client`: The session-specific chat client instance

#### Examples

    \dontrun{
    library(querychat)

    qc <- QueryChat$new(mtcars)
    qc$app()
    }

------------------------------------------------------------------------

### Method `app_obj()`

A streamlined Shiny app for chatting with data

Creates a Shiny app designed for chatting with data, with:

- A sidebar containing the chat interface

- A card displaying the current SQL query

- A card displaying the filtered data table

- A reset button to clear the query

#### Usage

    QueryChat$app_obj(..., bookmark_store = "url")

#### Arguments

- `...`:

  Additional arguments (currently unused).

- `bookmark_store`:

  The bookmarking storage method. Passed to
  [`shiny::enableBookmarking()`](https://rdrr.io/pkg/shiny/man/enableBookmarking.html).
  If `"url"` or `"server"`, the chat state (including current query)
  will be bookmarked. Default is `"url"`.

#### Returns

A Shiny app object that can be run with
[`shiny::runApp()`](https://rdrr.io/pkg/shiny/man/runApp.html).

#### Examples

    \dontrun{
    library(querychat)

    qc <- QueryChat$new(mtcars)
    app <- qc$app_obj()
    shiny::runApp(app)
    }

------------------------------------------------------------------------

### Method [`sidebar()`](https://rstudio.github.io/bslib/reference/sidebar.html)

Create a sidebar containing the querychat UI.

This method generates a
[`bslib::sidebar()`](https://rstudio.github.io/bslib/reference/sidebar.html)
component containing the chat interface, suitable for use with
[`bslib::page_sidebar()`](https://rstudio.github.io/bslib/reference/page_sidebar.html)
or similar layouts.

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

  Optional ID for the QueryChat instance. If not provided, will use the
  ID provided at initialization. If using `$sidebar()` in a Shiny
  module, you'll need to provide `id = ns("your_id")` where `ns` is the
  namespacing function from
  [`shiny::NS()`](https://rdrr.io/pkg/shiny/man/NS.html).

#### Returns

A
[`bslib::sidebar()`](https://rstudio.github.io/bslib/reference/sidebar.html)
UI component.

#### Examples

    \dontrun{
    qc <- QueryChat$new(mtcars)

    ui <- page_sidebar(
      qc$sidebar(),
      # Main content here
    )
    }

------------------------------------------------------------------------

### Method `ui()`

Create the UI for the querychat chat interface.

This method generates the chat UI component. Typically you'll use
`$sidebar()` instead, which wraps this in a sidebar layout.

#### Usage

    QueryChat$ui(..., id = NULL)

#### Arguments

- `...`:

  Additional arguments passed to
  [`shinychat::chat_ui()`](https://posit-dev.github.io/shinychat/r/reference/chat_ui.html).

- `id`:

  Optional ID for the QueryChat instance. If not provided, will use the
  ID provided at initialization. If using `$ui()` in a Shiny module,
  you'll need to provide `id = ns("your_id")` where `ns` is the
  namespacing function from
  [`shiny::NS()`](https://rdrr.io/pkg/shiny/man/NS.html).

#### Returns

A UI component containing the chat interface.

#### Examples

    \dontrun{
    qc <- QueryChat$new(mtcars)

    ui <- fluidPage(
      qc$ui()
    )
    }

------------------------------------------------------------------------

### Method `server()`

Initialize the querychat server logic.

This method must be called within a Shiny server function. It sets up
the reactive logic for the chat interface and returns session-specific
reactive values.

#### Usage

    QueryChat$server(
      enable_bookmarking = FALSE,
      ...,
      id = NULL,
      session = shiny::getDefaultReactiveDomain()
    )

#### Arguments

- `enable_bookmarking`:

  Whether to enable bookmarking for the chat state. Default is `FALSE`.
  When enabled, the chat state (including current query, title, and chat
  history) will be saved and restored with Shiny bookmarks. This
  requires that the Shiny app has bookmarking enabled via
  [`shiny::enableBookmarking()`](https://rdrr.io/pkg/shiny/man/enableBookmarking.html)
  or the `enableBookmarking` parameter of
  [`shiny::shinyApp()`](https://rdrr.io/pkg/shiny/man/shinyApp.html).

- `...`:

  Ignored.

- `id`:

  Optional module ID for the QueryChat instance. If not provided, will
  use the ID provided at initialization. When used in Shiny modules,
  this `id` should match the `id` used in the corresponding UI function
  (i.e., `qc$ui(id = ns("your_id"))` pairs with
  `qc$server(id = "your_id")`).

- `session`:

  The Shiny session object.

#### Returns

A list containing session-specific reactive values and the chat client
with the following elements:

- `df`: Reactive expression returning the current filtered data frame

- `sql`: Reactive value for the current SQL query string

- `title`: Reactive value for the current title

- `client`: The session-specific chat client instance

#### Examples

    \dontrun{
    qc <- QueryChat$new(mtcars)

    server <- function(input, output, session) {
      qc_vals <- qc$server(enable_bookmarking = TRUE)

      output$data <- renderDataTable(qc_vals$df())
      output$query <- renderText(qc_vals$sql())
      output$title <- renderText(qc_vals$title() %||% "No Query")
    }
    }

------------------------------------------------------------------------

### Method `generate_greeting()`

Generate a welcome greeting for the chat.

By default, `QueryChat$new()` generates a greeting at the start of every
new conversation, which is convenient for getting started and
development, but also might add unnecessary latency and cost. Use this
method to generate a greeting once and save it for reuse.

#### Usage

    QueryChat$generate_greeting(echo = c("none", "output"))

#### Arguments

- `echo`:

  Whether to print the greeting to the console. Options are `"none"`
  (default, no output) or `"output"` (print to console).

#### Returns

The greeting string in Markdown format.

#### Examples

    \dontrun{
    # Create QueryChat object
    qc <- QueryChat$new(mtcars)

    # Generate a greeting and save it
    greeting <- qc$generate_greeting()
    writeLines(greeting, "mtcars_greeting.md")

    # Later, use the saved greeting
    qc2 <- QueryChat$new(mtcars, greeting = "mtcars_greeting.md")
    }

------------------------------------------------------------------------

### Method `cleanup()`

Clean up resources associated with the data source.

This method releases any resources (e.g., database connections)
associated with the data source. Call this when you are done using the
QueryChat object to avoid resource leaks.

Note: If `auto_cleanup` was set to `TRUE` in the constructor, this will
be called automatically when the Shiny app stops.

#### Usage

    QueryChat$cleanup()

#### Returns

Invisibly returns `NULL`. Resources are cleaned up internally.

------------------------------------------------------------------------

### Method `clone()`

The objects of this class are cloneable with this method.

#### Usage

    QueryChat$clone(deep = FALSE)

#### Arguments

- `deep`:

  Whether to make a deep clone.

## Examples

``` r
if (FALSE) { # \dontrun{
# Basic usage with a data frame
qc <- QueryChat$new(mtcars)
app <- qc$app()

# With a custom greeting
greeting <- "Welcome! Ask me about the mtcars dataset."
qc <- QueryChat$new(mtcars, greeting = greeting)

# With a specific LLM provider
qc <- QueryChat$new(mtcars, client = "anthropic/claude-sonnet-4-5")

# Generate a greeting for reuse
qc <- QueryChat$new(mtcars)
greeting <- qc$generate_greeting(echo = "text")
# Save greeting for next time
writeLines(greeting, "mtcars_greeting.md")
} # }

## ------------------------------------------------
## Method `QueryChat$new`
## ------------------------------------------------

if (FALSE) { # \dontrun{
# Basic usage
qc <- QueryChat$new(mtcars)

# With options
qc <- QueryChat$new(
  mtcars,
  greeting = "Welcome to the mtcars explorer!",
  client = "openai/gpt-4o",
  data_description = "Motor Trend car road tests dataset"
)

# With database
library(DBI)
conn <- dbConnect(RSQLite::SQLite(), ":memory:")
dbWriteTable(conn, "mtcars", mtcars)
qc <- QueryChat$new(conn, "mtcars")
} # }

## ------------------------------------------------
## Method `QueryChat$app`
## ------------------------------------------------

if (FALSE) { # \dontrun{
library(querychat)

qc <- QueryChat$new(mtcars)
qc$app()
} # }


## ------------------------------------------------
## Method `QueryChat$app_obj`
## ------------------------------------------------

if (FALSE) { # \dontrun{
library(querychat)

qc <- QueryChat$new(mtcars)
app <- qc$app_obj()
shiny::runApp(app)
} # }


## ------------------------------------------------
## Method `QueryChat$sidebar`
## ------------------------------------------------

if (FALSE) { # \dontrun{
qc <- QueryChat$new(mtcars)

ui <- page_sidebar(
  qc$sidebar(),
  # Main content here
)
} # }

## ------------------------------------------------
## Method `QueryChat$ui`
## ------------------------------------------------

if (FALSE) { # \dontrun{
qc <- QueryChat$new(mtcars)

ui <- fluidPage(
  qc$ui()
)
} # }

## ------------------------------------------------
## Method `QueryChat$server`
## ------------------------------------------------

if (FALSE) { # \dontrun{
qc <- QueryChat$new(mtcars)

server <- function(input, output, session) {
  qc_vals <- qc$server(enable_bookmarking = TRUE)

  output$data <- renderDataTable(qc_vals$df())
  output$query <- renderText(qc_vals$sql())
  output$title <- renderText(qc_vals$title() %||% "No Query")
}
} # }

## ------------------------------------------------
## Method `QueryChat$generate_greeting`
## ------------------------------------------------

if (FALSE) { # \dontrun{
# Create QueryChat object
qc <- QueryChat$new(mtcars)

# Generate a greeting and save it
greeting <- qc$generate_greeting()
writeLines(greeting, "mtcars_greeting.md")

# Later, use the saved greeting
qc2 <- QueryChat$new(mtcars, greeting = "mtcars_greeting.md")
} # }
```
