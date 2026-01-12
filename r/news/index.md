# Changelog

## querychat 0.2.0

- The update tool now requires that the SQL query returns all columns
  from the original data source, ensuring that the dashboard can display
  the complete data frame after filtering or sorting. If the query does
  not return all columns, an informative error message will be provided.
  ([\#180](https://github.com/posit-dev/querychat/issues/180))

- Obvious SQL keywords that lead to data modification (e.g., `INSERT`,
  `UPDATE`, `DELETE`, `DROP`, etc.) are now prohibited in queries run
  via the query tool or update tool, to prevent accidental data changes.
  If such keywords are detected, an informative error message will be
  provided. ([\#180](https://github.com/posit-dev/querychat/issues/180))

- [`querychat()`](https://posit-dev.github.io/querychat/reference/querychat-convenience.md)
  and `QueryChat$new()` now use either [duckdb](https://r.duckdb.org/)
  or `{SQLite}` for the in-memory database backend for data frames,
  depending on which package is installed. If both are installed,
  [duckdb](https://r.duckdb.org/) will be preferred. You can explicitly
  choose the `engine` in `DataFrameSource$new()` or set
  `querychat.DataFrameSource.engine` option to choose a global default.
  ([\#178](https://github.com/posit-dev/querychat/issues/178))

- `QueryChat$sidebar()`, `QueryChat$ui()`, and `QueryChat$server()` now
  support an optional `id` parameter to enable use within Shiny modules.
  When used in a module UI function, pass `id = ns("your_id")` where
  `ns` is the namespacing function from
  [`shiny::NS()`](https://rdrr.io/pkg/shiny/man/NS.html). In the
  corresponding module server function, pass the unwrapped ID to
  `QueryChat$server(id = "your_id")`. This enables multiple independent
  QueryChat instances from the same QueryChat object.
  ([\#172](https://github.com/posit-dev/querychat/issues/172))

- `QueryChat$client()` can now create standalone querychat-enabled chat
  clients with configurable tools and callbacks, enabling use outside of
  Shiny applications.
  ([\#168](https://github.com/posit-dev/querychat/issues/168))

- `QueryChat$console()` was added to launch interactive console-based
  chat sessions with your data source, with persistent conversation
  state across invocations.
  ([\#168](https://github.com/posit-dev/querychat/issues/168))

- The tools used in a `QueryChat` chatbot are now configurable. Use the
  new `tools` parameter of
  [`querychat()`](https://posit-dev.github.io/querychat/reference/querychat-convenience.md)
  or `QueryChat$new()` to select either or both `"query"` or `"update"`
  tools. Choose `tools = "update"` if you only want QueryChat to be able
  to update the dashboard (useful when you want to be 100% certain that
  the LLM will not see *any* raw data).
  ([\#168](https://github.com/posit-dev/querychat/issues/168))

- [`querychat_app()`](https://posit-dev.github.io/querychat/reference/querychat-convenience.md)
  will now only automatically clean up the data source if QueryChat
  creates the data source internally from a data frame.
  ([\#164](https://github.com/posit-dev/querychat/issues/164))

- **Breaking change:** The `$sql()` method now returns `NULL` instead of
  `""` (empty string) when no query has been set, aligning with the
  behavior of `$title()` for consistency. Most code using
  [`isTruthy()`](https://rdrr.io/pkg/shiny/man/isTruthy.html) or similar
  falsy checks will continue working without changes. Code that
  explicitly checks `sql() == ""` should be updated to use falsy checks
  (e.g., `!isTruthy(sql())`) or explicit null checks (`is.null(sql())`).
  ([\#146](https://github.com/posit-dev/querychat/issues/146))

- Tool detail cards can now be expanded or collapsed by default when
  querychat runs a query or updates the dashboard via the
  `querychat.tool_details` R option or the `QUERYCHAT_TOOL_DETAILS`
  environment variable. Valid values are `"expanded"`, `"collapsed"`, or
  `"default"`.
  ([\#137](https://github.com/posit-dev/querychat/issues/137))

- Added bookmarking support to `QueryChat$server()` and
  [`querychat_app()`](https://posit-dev.github.io/querychat/reference/querychat-convenience.md).
  When bookmarking is enabled (via `bookmark_store = "url"` or
  `"server"` in
  [`querychat_app()`](https://posit-dev.github.io/querychat/reference/querychat-convenience.md)
  or `$app_obj()`, or via `enable_bookmarking = TRUE` in `$server()`),
  the chat state (including current query, title, and chat history) will
  be saved and restored with Shiny bookmarks.
  ([\#107](https://github.com/posit-dev/querychat/issues/107))

- Nearly the entire functional API (i.e.,
  [`querychat_init()`](https://posit-dev.github.io/querychat/reference/deprecated.md),
  [`querychat_sidebar()`](https://posit-dev.github.io/querychat/reference/deprecated.md),
  [`querychat_server()`](https://posit-dev.github.io/querychat/reference/deprecated.md),
  etc) has been hard deprecated in favor of a simpler OOP-based API.
  Namely, the new `QueryChat$new()` class is now the main entry point
  (instead of
  [`querychat_init()`](https://posit-dev.github.io/querychat/reference/deprecated.md))
  and has methods to replace old functions (e.g., `$sidebar()`,
  `$server()`, etc).
  ([\#109](https://github.com/posit-dev/querychat/issues/109))

  - In addition,
    [`querychat_data_source()`](https://posit-dev.github.io/querychat/reference/deprecated.md)
    was renamed to `as_querychat_data_source()`, and remains exported
    for a developer extension point, but users no longer have to
    explicitly create a data source.
    ([\#109](https://github.com/posit-dev/querychat/issues/109))

- Added `prompt_template` support for `querychat_system_prompt()`.
  (Thank you, [@oacar](https://github.com/oacar)!
  [\#37](https://github.com/posit-dev/querychat/issues/37),
  [\#45](https://github.com/posit-dev/querychat/issues/45))

- [`querychat_init()`](https://posit-dev.github.io/querychat/reference/deprecated.md)
  now accepts a `client`, replacing the previous `create_chat_func`
  argument. ([\#60](https://github.com/posit-dev/querychat/issues/60))

  The `client` can be:

  - an
    [`ellmer::Chat`](https://ellmer.tidyverse.org/reference/Chat.html)
    object,
  - a function that returns an
    [`ellmer::Chat`](https://ellmer.tidyverse.org/reference/Chat.html)
    object,
  - or a provider-model string, e.g. `"openai/gpt-4.1"`, to be passed to
    [`ellmer::chat()`](https://ellmer.tidyverse.org/reference/chat-any.html).

  If `client` is not provided, querychat will use

  - the `querychat.client` R option, which can be any of the above
    options,
  - the `QUERYCHAT_CLIENT` environment variable, which should be a
    provider-model string,
  - or the default model from
    [`ellmer::chat_openai()`](https://ellmer.tidyverse.org/reference/chat_openai.html).

- [`querychat_server()`](https://posit-dev.github.io/querychat/reference/deprecated.md)
  now uses a
  [`shiny::ExtendedTask`](https://rdrr.io/pkg/shiny/man/ExtendedTask.html)
  for streaming the chat response, which allows the dashboard to update
  and remain responsive while the chat response is streaming in.
  ([\#63](https://github.com/posit-dev/querychat/issues/63))

- querychat now requires `ellmer` version 0.3.0 or later and uses rich
  tool cards for dashboard updates and database queries.
  ([\#65](https://github.com/posit-dev/querychat/issues/65))

- New
  [`querychat_app()`](https://posit-dev.github.io/querychat/reference/querychat-convenience.md)
  function lets you quickly launch a Shiny app with a querychat chat
  interface. ([\#66](https://github.com/posit-dev/querychat/issues/66))

- [`querychat_ui()`](https://posit-dev.github.io/querychat/reference/deprecated.md)
  now adds a `.querychat` class to the chat container and
  [`querychat_sidebar()`](https://posit-dev.github.io/querychat/reference/deprecated.md)
  adds a `.querychat-sidebar` class to the sidebar, allowing for easier
  customization via CSS.
  ([\#68](https://github.com/posit-dev/querychat/issues/68))

- querychat now uses a separate tool to reset the dashboard.
  ([\#80](https://github.com/posit-dev/querychat/issues/80))

- [`querychat_greeting()`](https://posit-dev.github.io/querychat/reference/deprecated.md)
  can be used to generate a greeting message for your querychat bot.
  ([\#87](https://github.com/posit-dev/querychat/issues/87))

- querychat’s system prompt and tool descriptions were rewritten for
  clarity and future extensibility.
  ([\#90](https://github.com/posit-dev/querychat/issues/90))
