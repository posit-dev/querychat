# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

