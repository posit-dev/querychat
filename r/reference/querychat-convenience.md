# QueryChat convenience functions

Convenience functions for wrapping
[QueryChat](https://posit-dev.github.io/querychat/reference/QueryChat.md)
creation (i.e., `querychat()`) and app launching (i.e.,
`querychat_app()`).

## Usage

``` r
querychat(
  data_source,
  table_name = missing_arg(),
  ...,
  id = NULL,
  greeting = NULL,
  client = NULL,
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  cleanup = NA
)

querychat_app(
  data_source,
  table_name = missing_arg(),
  ...,
  id = NULL,
  greeting = NULL,
  client = NULL,
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  cleanup = TRUE,
  bookmark_store = "url"
)
```

## Arguments

- data_source:

  Either a data.frame or a database connection (e.g., DBI connection).

- table_name:

  A string specifying the table name to use in SQL queries. If
  `data_source` is a data.frame, this is the name to refer to it by in
  queries (typically the variable name). If not provided, will be
  inferred from the variable name for data.frame inputs. For database
  connections, this parameter is required.

- ...:

  Additional arguments (currently unused).

- id:

  Optional module ID for the QueryChat instance. If not provided, will
  be auto-generated from `table_name`. The ID is used to namespace the
  Shiny module.

- greeting:

  Optional initial message to display to users. Can be a character
  string (in Markdown format) or a file path. If not provided, a
  greeting will be generated at the start of each conversation using the
  LLM, which adds latency and cost. Use `$generate_greeting()` to create
  a greeting to save and reuse.

- client:

  Optional chat client. Can be:

  - An [ellmer::Chat](https://ellmer.tidyverse.org/reference/Chat.html)
    object

  - A string to pass to
    [`ellmer::chat()`](https://ellmer.tidyverse.org/reference/chat-any.html)
    (e.g., `"openai/gpt-4o"`)

  - `NULL` (default): Uses the `querychat.client` option, the
    `QUERYCHAT_CLIENT` environment variable, or defaults to
    [`ellmer::chat_openai()`](https://ellmer.tidyverse.org/reference/chat_openai.html)

- data_description:

  Optional description of the data in plain text or Markdown. Can be a
  string or a file path. This provides context to the LLM about what the
  data represents.

- categorical_threshold:

  For text columns, the maximum number of unique values to consider as a
  categorical variable. Default is 20.

- extra_instructions:

  Optional additional instructions for the chat model in plain text or
  Markdown. Can be a string or a file path.

- prompt_template:

  Optional path to or string of a custom prompt template file. If not
  provided, the default querychat template will be used. See the package
  prompts directory for the default template format.

- cleanup:

  Whether or not to automatically run `$cleanup()` when the Shiny
  session/app stops. By default, cleanup only occurs if `QueryChat` gets
  created within a Shiny session. Set to `TRUE` to always clean up, or
  `FALSE` to never clean up automatically.

- bookmark_store:

  The bookmarking storage method. Passed to
  [`shiny::enableBookmarking()`](https://rdrr.io/pkg/shiny/man/enableBookmarking.html).
  If `"url"` or `"server"`, the chat state (including current query)
  will be bookmarked. Default is `"url"`.

## Value

A `QueryChat` object. See
[QueryChat](https://posit-dev.github.io/querychat/reference/QueryChat.md)
for available methods.

Invisibly returns the chat object after the app stops.

## Examples

``` r
if (FALSE) { # \dontrun{
# Quick start - chat with mtcars dataset in one line
querychat_app(mtcars)

# Add options
querychat_app(
  mtcars,
  greeting = "Welcome to the mtcars explorer!",
  client = "openai/gpt-4o"
)

# Chat with a database table (table_name required)
library(DBI)
conn <- dbConnect(RSQLite::SQLite(), ":memory:")
dbWriteTable(conn, "mtcars", mtcars)
querychat_app(conn, "mtcars")

# Create QueryChat class object
qc <- querychat(mtcars)

# Run the app later
qc$app()

} # }
```
