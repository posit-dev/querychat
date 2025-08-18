# querychat (development version)

* Initial CRAN submission.

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
