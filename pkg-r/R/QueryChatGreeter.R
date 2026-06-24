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
    .parent = NULL,
    .tables = NULL,
    .prompt = NULL
  ),
  public = list(
    #' @description Create a new QueryChatGreeter.
    #' @param parent The owning QueryChat instance.
    initialize = function(parent) {
      private$.parent <- parent
      private$.tables <- character()
      private$.prompt <- system.file(
        "prompts",
        "greeting.md",
        package = "querychat"
      )
    },

    #' @description Generate a greeting using the greeting system prompt.
    #' @param echo Whether to echo the output (`"none"` or `"output"`).
    #' @return The greeting string.
    generate = function(echo = c("none", "output")) {
      echo <- rlang::arg_match(echo)
      chat <- private$.parent$.__enclos_env__$private$build_greeting_client()
      txt <- as.character(chat$chat(GREETING_PROMPT, echo = echo))
      private$.parent$greeting <- txt
      txt
    }
  ),
  active = list(
    #' @field tables Character vector of table names whose context to include in
    #'   the greeting. Changes affect the next generated greeting.
    tables = function(value) {
      if (missing(value)) {
        return(private$.tables)
      }
      private$.tables <- value
    },

    #' @field prompt The greeting template (string or file path). Changes affect
    #'   the next generated greeting.
    prompt = function(value) {
      if (missing(value)) {
        return(private$.prompt)
      }
      private$.prompt <- value
    }
  )
)
