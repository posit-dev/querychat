# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### New features

* New `QueryChat.app()` method enables quicker/easier chatting with a dataset. (#xx)
* Enabled bookmarking by default in both `.app()` and `.server()` methods. In latter case, you'll need to also specify the `bookmark_store` (either in `shiny.App()` or `shiny.express.app_opts()`) for it to take effect. (#xx)


## [UNRELEASED]

### Changes

* The entire functional API (i.e., `init()`, `sidebar()`, `server()`, etc) has been deprecated in favor of a new class/OOP API. Namely, the new `QueryChat()` class is now the recommended way to start (instead of `init()`), which has methods to replace old functions (e.g., `.sidebar()`, `.server()`, etc). (#101)
* The previously deprecated `create_chat_callback` parameter of `init()` was removed. (#101)
* The `querychat.querychat` submodule was removed. It was never intended to be a part of the public API. (#101)

## [UNRELEASED]

### New features

* The `.sql` query and `.title` returned from `querychat.server()` are now reactive values, meaning you can now `.set()` their value, and `.df()` will update accordingly. (#98)

* Added `querychat.greeting()` to help you create a greeting message for your querychat bot. (#87)

* Added `querychat_reset_dashboard()` tool for easily resetting the dashboard filters when asked by the user. (#81)

### Improvements

* Added rich tool UI support using shinychat development version and chatlas >= 0.11.1. (#67)

* querychat's system prompt and tool descriptions were rewritten for clarity and future extensibility. (#90)

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
