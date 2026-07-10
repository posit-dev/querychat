# QueryChat convenience functions

Convenience functions for wrapping
[QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md)
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

querychat_app(
  data_source,
  table_name = missing_arg(),
  ...,
  id = NULL,
  greeting = NULL,
  client = NULL,
  tools = c("filter", "query"),
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  data_dict = NULL,
  cleanup = NA,
  history = NULL
)
```

## Arguments

- data_source:

  Either a data.frame or a database connection (e.g., DBI connection).

- table_name:

  A string specifying the table name to use in SQL queries.

- ...:

  Additional arguments (currently unused).

- id:

  Optional module ID for the QueryChat instance.

- greeting:

  Optional initial message to display to users.

- history:

  Conversation history configuration for the generated app. See
  [QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md)'s
  `$app()` method.

- client:

  Optional chat client.

- tools:

  Which querychat tools to include in the chat client.

- data_description:

  Optional description of the data.

- categorical_threshold:

  For text columns, the maximum number of unique values to consider as a
  categorical variable. Default is 20.

- extra_instructions:

  Optional additional instructions for the chat model.

- prompt_template:

  Optional path to or string of a custom prompt template.

- data_dict:

  Optional data dictionary. A path to a YAML file or a list of paths.

- cleanup:

  Whether or not to automatically run `$cleanup()` when the Shiny
  session/app stops.

## Value

A `QueryChat` object. See
[QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md)
for available methods.

Invisibly returns the chat object after the app stops.

## Examples

``` r
if (FALSE) { # rlang::is_interactive() && rlang::is_installed("RSQLite")
# Quick start - chat with mtcars dataset in one line
querychat_app(mtcars)
}
```
