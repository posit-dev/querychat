# Changelog

## querychat (development version)

### New features

- The SQL panel in
  [`querychat_app()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
  is now an editable code editor. Users can tweak the generated SQL
  directly and apply it with Ctrl/Cmd+Enter or by clicking away — no
  extra button required. The editor stays in sync when the LLM updates
  the query or the active table changes.
  ([\#265](https://github.com/posit-dev/querychat/issues/265))

- `QueryChat$new()` now supports **multiple related tables**. Register
  additional tables with `$add_table()` and the LLM can reason across
  all of them — joins, cross-table filters, aggregations. Per-table
  reactive state (`$df()`, `$sql()`, `$title()`) is accessible via
  `qc_vals$table("name")` on the list returned by `$server()`. For DBI
  connections, `$add_tables()` registers all tables (or a named subset)
  in a single call.
  ([\#195](https://github.com/posit-dev/querychat/issues/195))

  ``` r

  qc <- QueryChat$new(orders_df, "orders")
  qc$add_table(customers_df, "customers")

  # Or, register all tables from a DBI connection at once:
  qc <- QueryChat$new()
  qc$add_tables(con)

  qc_vals <- qc$server()
  qc_vals$table("orders")$df()
  qc_vals$table("customers")$sql()
  ```

- A new **`data_dict`** parameter — integrating with the
  [data-dict](https://data-dict.tidyverse.org/) spec — lets you annotate
  tables and columns with plain-English descriptions loaded from a YAML
  file. This is the preferred way to provide additional context for the
  data, especially when multiple tables are relevant. The LLM receives
  these descriptions when it fetches the schema, helping it interpret
  ambiguous or domain-specific column names without any extra prompting.
  ([\#195](https://github.com/posit-dev/querychat/issues/195))

  ``` r

  QueryChat$new(data_dict = "data_dict.yaml")
  ```

- Added `PinSource`, a data source for chatting with datasets pinned to
  a [pins](https://pins.rstudio.com/) board. Works with parquet, CSV,
  JSON, and RDS pins, and uses the pin’s title, description, and tags as
  the default data description.
  ([\#246](https://github.com/posit-dev/querychat/issues/246))

- File attachments are now enabled by default in the Shiny chat UI.
  Users can attach images, PDFs, and text files to their messages and
  the LLM will receive them. Disable with `allow_attachments = FALSE` in
  `mod_ui()` or `QueryChat$ui()`.
  ([\#253](https://github.com/posit-dev/querychat/issues/253))

- Conversation history is now persisted by default. `QueryChat` keeps a
  user’s chat around across page reloads and browser sessions, backed by
  shinychat’s history support. The default `restore_mode = "browser"`
  stores the active conversation in the browser’s localStorage, but you
  can pass `history = shinychat::history_options(restore_mode = "url")`
  to restore via a plain, shareable URL instead, or
  `restore_mode = "bookmark"` to fold the conversation into a full Shiny
  bookmark. Disable with `history = FALSE`.

### Breaking changes

- The `$data_source` property has been removed. Use
  `qc$table("name")$data_source` to read a table’s data source, and
  `qc$add_table(df, "name", replace = TRUE)` to replace it. The
  `data_source` parameter to `$server()` has also been removed; call
  `$add_table()` before `$server()` instead.
  ([\#195](https://github.com/posit-dev/querychat/issues/195))

- `$app()`/`$app_obj()`’s `bookmark_store` parameter has been removed.
  Pass `history = shinychat::history_options(restore_mode = "bookmark")`
  to get the same shareable-bookmark behavior; any other `history` value
  disables Shiny-level bookmarking for the generated app. `$app()`
  defaults to `restore_mode = "bookmark"` when no `history` is set
  anywhere, so existing `$app()` callers keep working without changes.
  Note this default is a storage-mechanism change, not just a rename:
  the old default (`bookmark_store = "url"`) encoded the entire bookmark
  state in the URL itself, requiring no server storage; the new default
  requires server-side bookmark storage (`bookmarkStore = "server"`),
  with just a short state ID in the URL. Deployments that relied on
  `$app()` being fully stateless should pass `history = FALSE` or a
  non-bookmark `history_options()`.

### Deprecated

- `$server()`’s `enable_bookmarking` parameter is deprecated in favor of
  `history`. Pass
  `history = shinychat::history_options(restore_mode = "bookmark")`
  instead of `enable_bookmarking = TRUE` for the equivalent behavior.

### Improvements

- Chat greetings now use shinychat’s greeting API (requires shinychat
  \>= 0.4.0). A provided `greeting` renders instantly when the app
  loads, and when no `greeting` is given one is generated on demand —
  now **schema-aware**, so it can describe the data it’s about to help
  you explore — without being added to the conversation history.
  Generated greetings are preserved across bookmark/restore. Tables
  passed to `QueryChat$new()` are described in the greeting
  automatically; opt additional tables in with
  `include_in_greeting = TRUE` on `$add_table()`/`$add_tables()`, or
  fine-tune which tables and which template the greeting uses via
  `qc$greeter`.
  ([\#249](https://github.com/posit-dev/querychat/issues/249),
  [\#261](https://github.com/posit-dev/querychat/issues/261))

- The system prompt is now lighter: full schema is no longer embedded
  upfront. Instead the LLM fetches per-table schema on demand via the
  new `querychat_get_schema` tool — and only when it needs to. When a
  `data_dict` is provided, the tool skips columns that already have
  descriptions, so the LLM only pays for what isn’t already documented.
  ([\#195](https://github.com/posit-dev/querychat/issues/195))

- Fixed `data_description` and `extra_instructions` being HTML-escaped
  in the system prompt. Special characters like `<`, `>`, and `&` in
  developer-provided descriptions and instructions are now passed to the
  LLM verbatim.
  ([\#258](https://github.com/posit-dev/querychat/issues/258))

- The close button in `$app()` is now hidden when running in a
  non-interactive context (e.g. a deployed Shiny app), preventing
  [`stopApp()`](https://rdrr.io/pkg/shiny/man/stopApp.html) from
  crashing the session for other users.
  ([\#259](https://github.com/posit-dev/querychat/issues/259))

## querychat 0.3.0

CRAN release: 2026-06-01

### New features

- Added a new `"visualize"` tool that lets querychat render interactive
  charts inline in the chat. When enabled (via
  `tools = c("filter", "query", "visualize")`), the LLM can answer
  questions with charts by writing ggsql (SQL with a `VISUALISE` clause)
  instead of only tables. Charts can be expanded to fullscreen and their
  underlying query inspected. Requires the `ggsql` package and
  `bslib >= 0.11.0`.
  ([\#224](https://github.com/posit-dev/querychat/issues/224))

- Added stream cancellation support. A stop button now appears during
  LLM streaming, allowing users to cancel in-progress responses by
  clicking it or pressing Escape. Cancellation is enabled by default and
  can be disabled via `enable_cancel = FALSE` in the UI.
  ([\#241](https://github.com/posit-dev/querychat/issues/241))

- Added support for Snowflake Semantic Views. When connected to
  Snowflake via DBI, querychat automatically discovers available
  Semantic Views and includes their definitions in the system prompt.
  This helps the LLM generate correct queries using the
  `SEMANTIC_VIEW()` table function with certified business metrics and
  dimensions.
  ([\#200](https://github.com/posit-dev/querychat/issues/200))

- `QueryChat$new()` now supports deferred data source. Pass
  `data_source = NULL` at initialization time, then provide the actual
  data source via the `data_source` parameter of `$server()` or by
  setting the `$data_source` property. This enables use cases where the
  data source depends on session-specific authentication or per-user
  database connections.
  ([\#202](https://github.com/posit-dev/querychat/issues/202))

- `QueryChat$server()` now accepts a `client` parameter for
  session-scoped chat client overrides. This enables Posit Connect
  managed OAuth workflows where API credentials are only available
  inside the Shiny server function. The client spec is stored lazily at
  construction time and resolved only when needed, so
  `QueryChat$new(NULL, "table")` no longer requires an API key.
  ([\#205](https://github.com/posit-dev/querychat/issues/205))

### Improvements

- The query tool result card now starts collapsed by default. Users can
  still expand it to see the SQL query and results. Set
  `QUERYCHAT_TOOL_DETAILS=expanded` (or
  `options(querychat.tool_details = "expanded")`) to restore the
  previous behavior.
  ([\#239](https://github.com/posit-dev/querychat/issues/239))

- Query suggestions generated by the LLM now render reliably as
  clickable cards in the chat.
  ([\#236](https://github.com/posit-dev/querychat/issues/236),
  [\#238](https://github.com/posit-dev/querychat/issues/238))

- The `tools` parameter now uses `"filter"` as the preferred name
  (instead of `"update"`) for the dashboard-filtering tool group. The
  default is now `c("filter", "query")`. The legacy name `"update"` is
  still accepted everywhere.
  ([\#222](https://github.com/posit-dev/querychat/issues/222))

- When a custom `prompt_template` is provided that doesn’t contain
  Mustache references to `{{schema}}`, the expensive `get_schema()` call
  is now skipped entirely. This allows users with large databases to
  avoid slow startup by providing their own prompt that includes schema
  information inline (or omits it).
  ([\#208](https://github.com/posit-dev/querychat/issues/208))

### Bug fixes

- `DBISource` now uses database-agnostic SQL for column and type
  detection, replacing `LIMIT` syntax with `WHERE 1=0` and
  `dbFetch(n=1)`. This fixes compatibility with SQL Server and other
  databases that don’t support `LIMIT`.
  ([\#112](https://github.com/posit-dev/querychat/issues/112),
  [\#197](https://github.com/posit-dev/querychat/issues/197))

## querychat 0.2.0

CRAN release: 2026-01-12

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

- [`querychat()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
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
  [`querychat()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
  or `QueryChat$new()` to select either or both `"query"` or `"update"`
  tools. Choose `tools = "update"` if you only want QueryChat to be able
  to update the dashboard (useful when you want to be 100% certain that
  the LLM will not see *any* raw data).
  ([\#168](https://github.com/posit-dev/querychat/issues/168))

- [`querychat_app()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
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
  [`querychat_app()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md).
  When bookmarking is enabled (via `bookmark_store = "url"` or
  `"server"` in
  [`querychat_app()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
  or `$app_obj()`, or via `enable_bookmarking = TRUE` in `$server()`),
  the chat state (including current query, title, and chat history) will
  be saved and restored with Shiny bookmarks.
  ([\#107](https://github.com/posit-dev/querychat/issues/107))

- Nearly the entire functional API (i.e.,
  [`querychat_init()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md),
  [`querychat_sidebar()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md),
  [`querychat_server()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md),
  etc) has been hard deprecated in favor of a simpler OOP-based API.
  Namely, the new `QueryChat$new()` class is now the main entry point
  (instead of
  [`querychat_init()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md))
  and has methods to replace old functions (e.g., `$sidebar()`,
  `$server()`, etc).
  ([\#109](https://github.com/posit-dev/querychat/issues/109))

  - In addition,
    [`querychat_data_source()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md)
    was renamed to `as_querychat_data_source()`, and remains exported
    for a developer extension point, but users no longer have to
    explicitly create a data source.
    ([\#109](https://github.com/posit-dev/querychat/issues/109))

- Added `prompt_template` support for `querychat_system_prompt()`.
  (Thank you, [@oacar](https://github.com/oacar)!
  [\#37](https://github.com/posit-dev/querychat/issues/37),
  [\#45](https://github.com/posit-dev/querychat/issues/45))

- [`querychat_init()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md)
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

- [`querychat_server()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md)
  now uses a
  [`shiny::ExtendedTask`](https://rdrr.io/pkg/shiny/man/ExtendedTask.html)
  for streaming the chat response, which allows the dashboard to update
  and remain responsive while the chat response is streaming in.
  ([\#63](https://github.com/posit-dev/querychat/issues/63))

- querychat now requires `ellmer` version 0.3.0 or later and uses rich
  tool cards for dashboard updates and database queries.
  ([\#65](https://github.com/posit-dev/querychat/issues/65))

- New
  [`querychat_app()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
  function lets you quickly launch a Shiny app with a querychat chat
  interface. ([\#66](https://github.com/posit-dev/querychat/issues/66))

- [`querychat_ui()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md)
  now adds a `.querychat` class to the chat container and
  [`querychat_sidebar()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md)
  adds a `.querychat-sidebar` class to the sidebar, allowing for easier
  customization via CSS.
  ([\#68](https://github.com/posit-dev/querychat/issues/68))

- querychat now uses a separate tool to reset the dashboard.
  ([\#80](https://github.com/posit-dev/querychat/issues/80))

- [`querychat_greeting()`](https://posit-dev.github.io/querychat/dev/reference/deprecated.md)
  can be used to generate a greeting message for your querychat bot.
  ([\#87](https://github.com/posit-dev/querychat/issues/87))

- querychat’s system prompt and tool descriptions were rewritten for
  clarity and future extensibility.
  ([\#90](https://github.com/posit-dev/querychat/issues/90))
