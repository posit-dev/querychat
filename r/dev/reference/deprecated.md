# Deprecated functions

These functions have been replaced by the new `QueryChat` R6 class API.
Please update your code to use the new class-based approach.

## Usage

``` r
querychat_init(...)

querychat_sidebar(...)

querychat_ui(...)

querychat_server(...)

querychat_greeting(...)

querychat_data_source(...)
```

## Value

Please see the updated function details for return values.

## Functions

- `querychat_init()`: was replaced with the `$new()` method of
  [QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md).

- `querychat_sidebar()`: was replaced with the `$sidebar()` method of
  [QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md).

- `querychat_ui()`: was replaced with the `$ui()` method of
  [QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md).

- `querychat_server()`: was replaced with the `$server()` method of
  [QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md).

- `querychat_greeting()`: was replaced with the `$generate_greeting()`
  method of
  [QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md).

- `querychat_data_source()`: was replaced with the `$new()` method of
  [QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md).
