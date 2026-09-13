# The tables a chat can query, plus the system prompt and query executor
# built from them. Never mutated after construction: QueryChat holds one
# built from $add_table() calls, and $server(data_source = ) derives a second
# one per session so a running session never observes later changes.
#
# Not exported.
TableSet <- R6::R6Class(
  "TableSet",
  private = list(
    .data_sources = NULL,
    .system_prompt = NULL,
    .data_description = NULL,
    .executor = NULL
  ),
  public = list(
    initialize = function(
      data_sources,
      system_prompt,
      data_description = NULL
    ) {
      if (length(data_sources) == 0) {
        cli::cli_abort("{.cls TableSet} requires at least one data source.")
      }
      nms <- names(data_sources)
      if (is.null(nms) || any(!nzchar(nms))) {
        cli::cli_abort("{.arg data_sources} must be a named list.")
      }
      private$.data_sources <- data_sources
      private$.system_prompt <- system_prompt
      private$.data_description <- data_description
    },

    executor = function() {
      if (is.null(private$.executor)) {
        private$.executor <- build_query_executor(private$.data_sources)
      }
      private$.executor
    },

    executor_built = function() {
      !is.null(private$.executor)
    },

    table_names = function() {
      names(private$.data_sources)
    },

    # Closes the executor if it was ever built. Never touches data sources.
    cleanup_executor = function() {
      if (!is.null(private$.executor)) {
        tryCatch(
          private$.executor$cleanup(),
          finally = {
            private$.executor <- NULL
          }
        )
      }
      invisible(NULL)
    }
  ),
  active = list(
    data_sources = function(value) {
      if (!missing(value)) {
        cli::cli_abort("{.field data_sources} is read-only.")
      }
      private$.data_sources
    },
    system_prompt = function(value) {
      if (!missing(value)) {
        cli::cli_abort("{.field system_prompt} is read-only.")
      }
      private$.system_prompt
    },
    data_description = function(value) {
      if (!missing(value)) {
        cli::cli_abort("{.field data_description} is read-only.")
      }
      private$.data_description
    }
  )
)
