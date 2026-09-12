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
    #' @param client_factory function(tables, prompt, base = NULL, table_set = NULL) returning a configured greeting client.
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
    #' @param tables Table names to describe. Defaults to `$tables`. `$server()`
    #'   passes the session's snapshot so a lazily generated greeting describes
    #'   the session that asked for it.
    #' @param table_set Optional `TableSet` to build the prompt from. Defaults to
    #'   the owning QueryChat's instance set.
    build_client = function(base = NULL, tables = NULL, table_set = NULL) {
      private$.client_factory(
        tables %||% private$.tables,
        private$.prompt,
        base,
        table_set = table_set
      )
    },

    #' @description Generate a greeting synchronously and return it as text.
    #' @param echo "none" or "output".
    #' @param base Optional resolved client to clone.
    generate = function(echo = c("none", "output"), base = NULL) {
      echo <- rlang::arg_match(echo)
      client <- self$build_client(base)
      as.character(client$chat(GREETING_PROMPT, echo = echo))
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
