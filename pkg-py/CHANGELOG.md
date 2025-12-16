# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### New features

* `QueryChat.client()` can now create standalone querychat-enabled chat clients with configurable tools and callbacks, enabling use outside of Shiny applications. (#168)

* `QueryChat.console()` was added to launch interactive console-based chat sessions with your data source, with persistent conversation state across invocations. (#168)

* The tools used in a `QueryChat` chatbot are now configurable. Use the new `tools` parameter of `QueryChat()` to select either or both `"query"` or `"update"` tools. Choose `tools=["update"]` if you only want QueryChat to be able to update the dashboard (useful when you want to be 100% certain that the LLM will not see _any_ raw data). (#168)

## [0.3.0] - 2025-12-10

### Breaking Changes

* The entire functional API (i.e., `init()`, `sidebar()`, `server()`, etc) has been hard deprecated in favor of a simpler OOP-based API. Namely, the new `QueryChat()` class is now the main entry point (instead of `init()`) and has methods to replace old functions (e.g., `.sidebar()`, `.server()`, etc). (#101)

* The `.sql()` method now returns `None` instead of `""` (empty string) when no query has been set, aligning with the behavior of `.title()` for consistency. Most code using the `or` operator or `req()` for falsy checks will continue working without changes. Code that explicitly checks `sql() == ""` should be updated to use falsy checks (`if not sql()`) or explicit null checks (`if sql() is None`). (#146)

### New features

* New `QueryChat.app()` method enables quicker/easier chatting with a dataset. (#104)

* Enabled bookmarking by default in both `.app()` and `.server()` methods. In latter case, you'll need to also specify the `bookmark_store` (either in `shiny.App()` or `shiny.express.app_opts()`) for it to take effect. (#104)

* The current SQL query and title can now be programmatically set through the `.sql()` and `.title()` methods of `QueryChat()`. (#98, #101)

* New `querychat.data` module provides sample datasets (`titanic()` and `tips()`) to make it easier to get started without external dependencies. (#118)

* Added a `.generate_greeting()` method to help you create a greeting message for your querychat bot. (#87)

* Added `querychat_reset_dashboard()` tool for easily resetting the dashboard filters when asked by the user. (#81)

### Improvements

* Added rich tool UI support using shinychat development version and chatlas >= 0.11.1. (#67)

* querychat's system prompt and tool descriptions were rewritten for clarity and future extensibility. (#90)

* Tool detail cards can now be expanded or collapsed by default when querychat runs a query or updates the dashboard via the `QUERYCHAT_TOOL_DETAILS` environment variable. Valid values are `"expanded"`, `"collapsed"`, or `"default"`. (#137)

## [0.2.2] - 2025-09-04

* Fixed another issue with data sources that aren't already narwhals DataFrames (#83)

## [0.2.1] - 2025-09-04

* Fixed an issue with the query tool when used with SQLAlchemy data sources. (@npelikan #79)

## [0.2.0] - 2025-09-02

* `querychat.init()` now accepts a `client` argument, replacing the previous `create_chat_callback` argument. (#60)

  The `client` can be:

  * a `chatlas.Chat` object,
  * a function that returns a `chatlas.Chat` object,
  * or a provider-model string, e.g. `"openai/gpt-4.1"`, to be passed to `chatlas.ChatAuto()`.

  If `client` is not provided, querychat will use the `QUERYCHAT_CLIENT` environment variable, which should be a provider-model string. If the envvar is not set, querychat uses OpenAI with the default model from `chatlas.ChatOpenAI()`.

* `querychat.ui()` now adds a `.querychat` class to the chat container and `querychat.sidebar()` adds a `.querychat-sidebar` class to the sidebar, allowing for easier customization via CSS. (#68)

## [0.1.0] - 2025-05-24

This first release of the `querychat` package.
