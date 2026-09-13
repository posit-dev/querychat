# querychat (development version)

## New features

* **Multiple related tables**: register additional tables with `$add_table()` (or every table from a DBI connection at once with `$add_tables()`), and the LLM can reason across them — joins, cross-table filters, aggregations. Per-table reactive state (`$df()`, `$sql()`, `$title()`) is available via `qc_vals$table("name")` on the list returned by `$server()`. (#195)

  ```r
  qc <- QueryChat$new(orders_df, "orders")
  qc$add_table(customers_df, "customers")

  qc_vals <- qc$server()
  qc_vals$table("orders")$df()
  ```

* **`data_dict`**: annotate tables and columns with plain-English descriptions from a YAML file (following the [data-dict](https://data-dict.tidyverse.org/) spec). This is now the preferred way to give the LLM context about your data, especially with multiple tables — no extra prompting required. (#195)

* **Chat-first apps**: `querychat_app()` (and `QueryChat$app()`) now put the chat front and center — the SQL editor and data table live in a drawer that opens automatically when the LLM runs a query. The new `$page()` method brings the same full-window layout to your own apps:

  ```r
  qc <- QueryChat$new(penguins)
  ui <- qc$page("Penguins Explorer")
  ```

* **`/handoff` slash command**: turn selected query and visualization results from a chat session into a downloadable Quarto dashboard or Shiny app, with AI-assisted revision and bundled data.

* **Persistent conversation history**: chats now survive page reloads and browser sessions by default. For a shareable URL or full Shiny bookmark instead, pass `history = shinychat::history_options(restore_mode = "url")` or `"bookmark"`. Disable with `history = FALSE`.

* **File attachments** are now enabled by default: users can attach images, PDFs, and text files to their messages. Disable with `allow_attachments = FALSE`. (#253)

* **Editable SQL panel**: the SQL panel in `querychat_app()` is now a code editor — tweak the generated SQL and apply it with Ctrl/Cmd+Enter. (#265)

* `PinSource`: chat with datasets pinned to a [pins](https://pins.rstudio.com/) board (parquet, CSV, JSON, RDS); the pin's title, description, and tags serve as the default data description. Multiple pins (and pins mixed with data frames) work in one chat via a shared DuckDB connection. (#246, #312)

* Deferred construction is more flexible: `table_name` is now optional in `QueryChat$new(NULL)`, and `$server()` gains a `table_name` parameter so the table can be named per session. (#305)

## Breaking changes

* The `$data_source` property has been removed. Use `qc$table("name")$data_source` to read a table's data source, and `qc$add_table(df, "name", replace = TRUE)` to replace it. (#195)

* `$app()`/`$app_obj()`'s `bookmark_store` parameter has been removed; pass `history = shinychat::history_options(restore_mode = "bookmark")` for equivalent behavior (existing `$app()` callers get this default automatically). Note the storage mechanism changed: server-side bookmark storage is now required rather than encoding state in the URL, so deployments that relied on `$app()` being fully stateless should pass `history = FALSE`.

## Deprecated

* `$server()`'s `enable_bookmarking` parameter is deprecated in favor of `history`.

## Improvements

* The `"visualize"` tool is now included in the default toolset. If the suggested ggsql package is not installed, the tool is dropped with a warning instead of erroring.

* Chat greetings render instantly when provided, and generated greetings are now schema-aware — they describe the data at hand — and are preserved across bookmark/restore. Opt additional tables into the greeting with `include_in_greeting = TRUE` on `$add_table()`/`$add_tables()`. (#249, #261)

* The system prompt no longer embeds the full schema upfront; the LLM fetches per-table schema on demand, skipping columns already described by a `data_dict`. (#195)

* Special characters like `<`, `>`, and `&` in `data_description` and `extra_instructions` are no longer HTML-escaped in the system prompt. (#258)

* The close button in `$app()` is now hidden in deployed (non-interactive) contexts, where `stopApp()` would crash the session for other users. (#259)

## Bug fixes

* Query results are now expanded in the chat only when the user asks to see the raw table, instead of far more often than intended. (#295)

* Fixed a module-namespace desync when a table was registered between `$ui()` and `$server()` (e.g. via `$server(data_source = )`). (#305)

* `$server(data_source = )` no longer modifies the `QueryChat` instance. The table is registered for that session only: the instance's tables, greeting tables, and system prompt are unchanged, a same-named instance table is shadowed for that session, and any connection querychat created for it is cleaned up when the session ends. A second session's `$server(data_source = )` call therefore no longer errors with "Cannot add tables after server initialization." (#300, #306)

* `$cleanup()` follows one rule: querychat closes only what it created. `DBISource$cleanup()` and `TblSqlSource$cleanup()` no longer disconnect your connection; disconnect it yourself on shutdown. `DataFrameSource`/`PinSource` DuckDB connections are still closed.

* The automatic `$cleanup()` registered when `QueryChat` is created while a Shiny app is running (`cleanup = NA`, the default) no longer disconnects caller-supplied DBI connections when the session or app stops, for the same reason. If you relied on that to close a connection you passed to `QueryChat$new()`, register your own `shiny::onStop(function() DBI::dbDisconnect(con))` (or disconnect when the session ends). Data frames are unaffected: the in-memory DuckDB connection querychat creates for them is still closed automatically.

* Adding a *new* table with `$add_table()`/`$add_tables()` after a session has started now warns instead of erroring; running sessions keep their tables and new sessions see the addition. Replacing or removing an existing table after a session has started still errors.

* A rejected or failed `$add_table()`/`$add_tables()` call (e.g. an incompatible source type) after a session has started no longer warns about the late change or otherwise affects the instance, since the change never took effect. (#311)

* A failed `QueryChat$new()` (e.g. an unreadable `prompt_template`) no longer leaks the data source connection querychat created while normalizing its input; the source is cleaned up before the error propagates. Caller-supplied `DataSource` objects remain the caller's responsibility.


# querychat 0.3.0

## New features

* Added a new `"visualize"` tool that lets querychat render interactive charts inline in the chat. When enabled (via `tools = c("filter", "query", "visualize")`), the LLM can answer questions with charts by writing ggsql (SQL with a `VISUALISE` clause) instead of only tables. Charts can be expanded to fullscreen and their underlying query inspected. Requires the `ggsql` package and `bslib >= 0.11.0`. (#224)

* Added stream cancellation support. A stop button now appears during LLM streaming, allowing users to cancel in-progress responses by clicking it or pressing Escape. Cancellation is enabled by default and can be disabled via `enable_cancel = FALSE` in the UI. (#241)

* Added support for Snowflake Semantic Views. When connected to Snowflake via DBI, querychat automatically discovers available Semantic Views and includes their definitions in the system prompt. This helps the LLM generate correct queries using the `SEMANTIC_VIEW()` table function with certified business metrics and dimensions. (#200)

* `QueryChat$new()` now supports deferred data source. Pass `data_source = NULL` at initialization time, then provide the actual data source via the `data_source` parameter of `$server()` or by setting the `$data_source` property. This enables use cases where the data source depends on session-specific authentication or per-user database connections. (#202)

* `QueryChat$server()` now accepts a `client` parameter for session-scoped chat client overrides. This enables Posit Connect managed OAuth workflows where API credentials are only available inside the Shiny server function. The client spec is stored lazily at construction time and resolved only when needed, so `QueryChat$new(NULL, "table")` no longer requires an API key. (#205)

## Improvements

* The query tool result card now starts collapsed by default. Users can still expand it to see the SQL query and results. Set `QUERYCHAT_TOOL_DETAILS=expanded` (or `options(querychat.tool_details = "expanded")`) to restore the previous behavior. (#239)

* Query suggestions generated by the LLM now render reliably as clickable cards in the chat. (#236, #238)

* The `tools` parameter now uses `"filter"` as the preferred name (instead of `"update"`) for the dashboard-filtering tool group. The default is now `c("filter", "query")`. The legacy name `"update"` is still accepted everywhere. (#222)

* When a custom `prompt_template` is provided that doesn't contain Mustache references to `{{schema}}`, the expensive `get_schema()` call is now skipped entirely. This allows users with large databases to avoid slow startup by providing their own prompt that includes schema information inline (or omits it). (#208)

## Bug fixes

* `DBISource` now uses database-agnostic SQL for column and type detection, replacing `LIMIT` syntax with `WHERE 1=0` and `dbFetch(n=1)`. This fixes compatibility with SQL Server and other databases that don't support `LIMIT`. (#112, #197)

# querychat 0.2.0

* The update tool now requires that the SQL query returns all columns from the original data source, ensuring that the dashboard can display the complete data frame after filtering or sorting. If the query does not return all columns, an informative error message will be provided. (#180)

* Obvious SQL keywords that lead to data modification (e.g., `INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.) are now prohibited in queries run via the query tool or update tool, to prevent accidental data changes. If such keywords are detected, an informative error message will be provided. (#180)

* `querychat()` and `QueryChat$new()` now use either `{duckdb}` or `{SQLite}` for the in-memory database backend for data frames, depending on which package is installed. If both are installed, `{duckdb}` will be preferred. You can explicitly choose the `engine` in `DataFrameSource$new()` or set `querychat.DataFrameSource.engine` option to choose a global default. (#178)

* `QueryChat$sidebar()`, `QueryChat$ui()`, and `QueryChat$server()` now support an optional `id` parameter to enable use within Shiny modules. When used in a module UI function, pass `id = ns("your_id")` where `ns` is the namespacing function from `shiny::NS()`. In the corresponding module server function, pass the unwrapped ID to `QueryChat$server(id = "your_id")`. This enables multiple independent QueryChat instances from the same QueryChat object. (#172)

* `QueryChat$client()` can now create standalone querychat-enabled chat clients with configurable tools and callbacks, enabling use outside of Shiny applications. (#168)

* `QueryChat$console()` was added to launch interactive console-based chat sessions with your data source, with persistent conversation state across invocations. (#168)

* The tools used in a `QueryChat` chatbot are now configurable. Use the new `tools` parameter of `querychat()` or `QueryChat$new()` to select either or both `"query"` or `"update"` tools. Choose `tools = "update"` if you only want QueryChat to be able to update the dashboard (useful when you want to be 100% certain that the LLM will not see _any_ raw data). (#168)

* `querychat_app()` will now only automatically clean up the data source if QueryChat creates the data source internally from a data frame. (#164)

* **Breaking change:** The `$sql()` method now returns `NULL` instead of `""` (empty string) when no query has been set, aligning with the behavior of `$title()` for consistency. Most code using `isTruthy()` or similar falsy checks will continue working without changes. Code that explicitly checks `sql() == ""` should be updated to use falsy checks (e.g., `!isTruthy(sql())`) or explicit null checks (`is.null(sql())`). (#146)

* Tool detail cards can now be expanded or collapsed by default when querychat runs a query or updates the dashboard via the `querychat.tool_details` R option or the `QUERYCHAT_TOOL_DETAILS` environment variable. Valid values are `"expanded"`, `"collapsed"`, or `"default"`. (#137)

* Added bookmarking support to `QueryChat$server()` and `querychat_app()`. When bookmarking is enabled (via `bookmark_store = "url"` or `"server"` in `querychat_app()` or `$app_obj()`, or via `enable_bookmarking = TRUE` in `$server()`), the chat state (including current query, title, and chat history) will be saved and restored with Shiny bookmarks. (#107)

* Nearly the entire functional API (i.e., `querychat_init()`, `querychat_sidebar()`, `querychat_server()`, etc) has been hard deprecated in favor of a simpler OOP-based API. Namely, the new `QueryChat$new()` class is now the main entry point (instead of `querychat_init()`) and has methods to replace old functions (e.g., `$sidebar()`, `$server()`, etc). (#109)
    * In addition, `querychat_data_source()` was renamed to `as_querychat_data_source()`, and remains exported for a developer extension point, but users no longer have to explicitly create a data source. (#109)

* Added `prompt_template` support for `querychat_system_prompt()`. (Thank you, @oacar! #37, #45)

* `querychat_init()` now accepts a `client`, replacing the previous `create_chat_func` argument. (#60)

  The `client` can be:

  * an `ellmer::Chat` object,
  * a function that returns an `ellmer::Chat` object,
  * or a provider-model string, e.g. `"openai/gpt-4.1"`, to be passed to `ellmer::chat()`.

  If `client` is not provided, querychat will use

  * the `querychat.client` R option, which can be any of the above options,
  * the `QUERYCHAT_CLIENT` environment variable, which should be a provider-model string,
  * or the default model from `ellmer::chat_openai()`.

* `querychat_server()` now uses a `shiny::ExtendedTask` for streaming the chat response, which allows the dashboard to update and remain responsive while the chat response is streaming in. (#63)

* querychat now requires `ellmer` version 0.3.0 or later and uses rich tool cards for dashboard updates and database queries. (#65)

* New `querychat_app()` function lets you quickly launch a Shiny app with a querychat chat interface. (#66)

* `querychat_ui()` now adds a `.querychat` class to the chat container and `querychat_sidebar()` adds a `.querychat-sidebar` class to the sidebar, allowing for easier customization via CSS. (#68)

* querychat now uses a separate tool to reset the dashboard. (#80)

* `querychat_greeting()` can be used to generate a greeting message for your querychat bot. (#87)

* querychat's system prompt and tool descriptions were rewritten for clarity and future extensibility. (#90)
