# querychat (development version)

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
