#' QueryChatGreeter
#'
#' @description
#' Controls greeting generation for a [QueryChat] instance. Access via
#' `qc$greeter`.
#'
#' @noRd
QueryChatGreeter <- R6::R6Class(
  "QueryChatGreeter",
  private = list(
    .client_factory = NULL,
    .tables = NULL,
    .prompt = NULL
  ),
  public = list(
    #' @param client_factory function(tables, prompt, base) returning a configured greeting client.
    initialize = function(client_factory) {
      private$.client_factory <- client_factory
      private$.tables <- character()
      private$.prompt <- system.file(
        "prompts",
        "greeting.md",
        package = "querychat"
      )
    },

    #' @description Build a fresh greeting client (no history) configured with the greeting system prompt.
    #' @param base Optional resolved client to clone (resolve-once base from `$server()`).
    build_client = function(base = NULL) {
      private$.client_factory(private$.tables, private$.prompt, base)
    },

    #' @description Generate a greeting synchronously and return it as text.
    #' @param echo "none" or "output".
    #' @param base Optional resolved client to clone.
    generate = function(echo = c("none", "output"), base = NULL) {
      echo <- rlang::arg_match(echo)
      client <- self$build_client(base)
      as.character(client$chat(GREETING_PROMPT, echo = echo))
    },

    #' @description Stream a greeting into the chat UI and capture the result
    #'   (Shiny path).
    #' @param greeting_reactive Session reactiveVal to receive the generated greeting.
    #' @param base Optional resolved client to clone.
    #' @param chat_id Chat component id targeted by the Shiny stream (default "chat").
    generate_stream = function(
      greeting_reactive,
      base = NULL,
      chat_id = "chat"
    ) {
      client <- self$build_client(base)
      stream <- client$stream_async(GREETING_PROMPT)
      p <- shinychat::chat_set_greeting(
        chat_id,
        chat_greeting_persistent(stream)
      )
      promises::then(p, function(value) {
        greeting_reactive(client$last_turn()@text)
      })
      p
    }
  ),
  active = list(
    #' @field tables Character vector of table names whose context to include in the greeting.
    tables = function(value) {
      if (missing(value)) {
        return(private$.tables)
      }
      private$.tables <- value %||% character()
    },
    #' @field prompt The greeting template (string or file path).
    prompt = function(value) {
      if (missing(value)) {
        return(private$.prompt)
      }
      private$.prompt <- value
    }
  )
)
