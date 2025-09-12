#' Generate or retrieve a greeting message
#'
#' Use this function to generate a friendly greeting message using the chat
#' client and data source specified in the `querychat_config` object. You can
#' pass this greeting to [querychat_init()] to set an initial greeting for users
#' for faster startup times and lower costs. If you don't provide a greeting in
#' [querychat_init()], one will be generated at the start of every new
#' conversation, using this function.
#'
#' @examplesIf interactive()
#' penguins_config <- querychat_init(penguins)
#'
#' # Generate a new greeting
#' querychat_greeting(penguins_config)
#'
#' # Update the config with the generated greeting
#' penguins_config <- querychat_init(
#'   penguins,
#'   greeting = "Hello! I’m here to help you explore and analyze the penguins..."
#' )
#'
#' # Alternatively, you could generate the greeting once when starting up your
#' # Shiny app server, to be shared across all users.
#' penguins_config <- querychat_init(penguins)
#' penguins_config$greeting <- querychat_greeting(penguins_config)
#'
#' @param querychat_config A `querychat_config` object from [querychat_init()].
#' @param generate If `TRUE` and if `querychat_config` does not include a
#'   `greeting`, a new greeting is generated. If `FALSE`, returns the existing
#'   greeting from the configuration (if any).
#' @param stream If `TRUE`, calls `$stream_async()` on the [ellmer::Chat]
#'   client, suitable for streaming the greeting into a Shiny app with
#'   [shinychat::chat_append()]. If `FALSE` (default), calls `$chat()` to get
#'   the full greeting at once. Only relevant when `generate = TRUE`.
#'
#' @return
#' - When `generate = FALSE`: Returns the existing greeting as a string or
#'   `NULL` if no greeting exists.
#' - When `generate = TRUE`: Returns the chat response containing a greeting and
#'   sample prompts.
#'
#' @export
querychat_greeting <- function(
  querychat_config,
  generate = TRUE,
  stream = FALSE
) {
  if (!inherits(querychat_config, "querychat_config")) {
    rlang::abort("`querychat_config` must be a `querychat_config` object.")
  }

  greeting <- querychat_config$greeting

  if (!isTRUE(generate)) {
    has_greeting <- !is.null(greeting) && any(nzchar(greeting))
    return(
      if (has_greeting) paste(greeting, collapse = "\n") else NULL
    )
  }

  chat <- querychat_config$client$clone()
  chat$set_system_prompt(querychat_config$system_prompt)

  prompt <- "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."

  if (isTRUE(stream)) {
    chat$stream_async(prompt)
  } else {
    is_user_facing <- rlang::env_is_user_facing(rlang::caller_env())
    echo = if (is_user_facing) "output" else "none"
    chat$chat(prompt, echo = echo)
  }
}
