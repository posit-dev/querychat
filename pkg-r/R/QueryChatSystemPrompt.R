#' System Prompt Management for QueryChat
#'
#' @description
#' `QueryChatSystemPrompt` is an R6 class that encapsulates system prompt
#' template and component management for QueryChat. It handles loading of
#' prompt templates, data descriptions, and extra instructions from files or
#' strings, and renders them with tool configuration using Mustache templates.
#'
#' @noRd
QueryChatSystemPrompt <- R6::R6Class(
  "QueryChatSystemPrompt",

  public = list(
    #' @field template The Mustache template string for the system prompt, or
    #'   a path to a file containing a system prompt template.
    template = NULL,

    #' @field data_description Optional description of the data context, or a
    #'   path to a file containing the data description.
    data_description = NULL,

    #' @field extra_instructions Optional custom instructions for the LLM, or a
    #'   path to a file containing the extra instructions.
    extra_instructions = NULL,

    #' @field categorical_threshold Threshold for categorical column detection.
    categorical_threshold = NULL,

    #' @field data_sources Named list of DataSource objects.
    data_sources = NULL,

    #' @field data_dicts List of data dict lists (from [read_data_dict()]).
    data_dicts = NULL,

    #' @field has_measures Whether measures are registered.
    has_measures = NULL,

    #' @description
    #' Create a new QueryChatSystemPrompt object.
    #'
    #' @param prompt_template Path to template file or template string.
    #' @param data_sources Named list of DataSource objects.
    #' @param data_description Optional path to data description file or description string.
    #' @param extra_instructions Optional path to instructions file or instructions string.
    #' @param categorical_threshold Threshold for categorical column detection (default: 10).
    #' @param data_dicts Optional list of data dict lists (from [read_data_dict()]).
    #'
    #' @return A new `QueryChatSystemPrompt` object.
    initialize = function(
      prompt_template,
      data_sources,
      data_description = NULL,
      extra_instructions = NULL,
      categorical_threshold = 10,
      data_dicts = NULL,
      has_measures = FALSE
    ) {
      self$template <- read_text(prompt_template)

      if (!is.null(data_description)) {
        self$data_description <- read_text(data_description)
      }

      if (!is.null(extra_instructions)) {
        self$extra_instructions <- read_text(extra_instructions)
      }

      self$categorical_threshold <- categorical_threshold
      self$data_sources <- data_sources
      self$data_dicts <- data_dicts %||% list()
      self$has_measures <- has_measures

      if (length(data_sources) > 1 && length(self$data_dicts) == 0) {
        cli::cli_warn(
          c(
            "Multiple tables registered without a {.arg data_dict}.",
            "i" = "Providing a {.arg data_dict} with table descriptions and relationships gives the LLM better context."
          )
        )
      }
    },

    #' @description
    #' Render the system prompt with tool configuration.
    #'
    #' @param tools Character vector of tool names to enable (e.g.,
    #'   `c("query", "update"))`, or `NULL` for no tools.
    #'
    #' @return A character string containing the rendered system prompt.
    render = function(tools) {
      first_source <- self$data_sources[[1]]
      db_type <- first_source$get_db_type()
      has_dicts <- length(self$data_dicts) > 0

      semantic_views <- ""
      if (inherits(first_source, "DBISource")) {
        semantic_views <- first_source$get_semantic_views_description()
      }

      # Compute schema for backward compat with templates using {{schema}}
      schema <- ""
      if (grepl("\\{\\{[{#^/]?\\s*schema\\b", self$template)) {
        schema <- first_source$get_schema(
          categorical_threshold = self$categorical_threshold
        )
      }

      context <- list(
        db_type = db_type,
        is_duck_db = tolower(db_type) == "duckdb",
        semantic_views = semantic_views,
        schema = schema,
        has_data_dicts = has_dicts,
        data_dicts = if (has_dicts) self$generate_data_dicts_yaml() else "",
        tables_overview = if (!has_dicts) {
          self$generate_tables_overview()
        } else {
          ""
        },
        data_description = self$data_description,
        extra_instructions = self$extra_instructions,
        has_tool_update = if ("update" %in% tools) "true",
        has_tool_query = if ("query" %in% tools) "true",
        has_tool_visualize = if ("visualize" %in% tools) "true",
        include_query_guidelines = if (length(tools) > 0) "true",
        multi_table = length(self$data_sources) > 1,
        has_measures = if (isTRUE(self$has_measures)) "true"
      )

      partials <- list()
      syntax_path <- system.file(
        "prompts",
        "ggsql-syntax.md",
        package = "querychat"
      )
      if (nzchar(syntax_path)) {
        partials[["ggsql-syntax"]] <- paste(
          readLines(syntax_path),
          collapse = "\n"
        )
      }
      measures_path <- system.file("prompts", "measures.md", package = "querychat")
      if (nzchar(measures_path)) {
        partials[["measures"]] <- paste(readLines(measures_path, warn = FALSE), collapse = "\n")
      }

      whisker::whisker.render(self$template, context, partials = partials)
    },

    #' @description
    #' Generate a plain-text tables overview for the system prompt.
    generate_tables_overview = function() {
      lines <- character()
      for (name in names(self$data_sources)) {
        source <- self$data_sources[[name]]
        desc <- if (is.null(self$data_description)) {
          source$get_data_description()
        }
        if (nzchar(desc %||% "")) {
          lines <- c(lines, sprintf("- %s: %s", name, desc))
        } else {
          lines <- c(lines, sprintf("- %s", name))
        }
      }
      paste(lines, collapse = "\n")
    },

    #' @description
    #' Generate YAML-formatted data dict blocks for the system prompt.
    generate_data_dicts_yaml = function() {
      check_installed("yaml")
      blocks <- character()
      all_claimed <- character()

      for (dd in self$data_dicts) {
        d <- data_dict_to_prompt_list(dd)
        d$name <- NULL
        d$description <- NULL

        claimed <- intersect(names(self$data_sources), names(dd$tables))
        all_claimed <- c(all_claimed, claimed)
        if (!is.null(d$tables)) {
          d$tables <- d$tables[names(d$tables) %in% names(self$data_sources)]
          if (length(d$tables) == 0) d$tables <- NULL
        }

        escape_attr <- function(s) gsub('"', "&quot;", s, fixed = TRUE)
        attrs <- if (!is.null(dd$name)) {
          sprintf('name="%s"', escape_attr(dd$name))
        } else {
          ""
        }
        if (!is.null(dd$description)) {
          attrs <- paste0(
            attrs,
            sprintf(' description="%s"', escape_attr(dd$description))
          )
        }
        attrs <- trimws(attrs)

        body <- if (length(d) > 0) {
          yaml::as.yaml(d, column.major = FALSE)
        } else {
          ""
        }
        body <- sub("\n$", "", body)

        if (nzchar(body)) {
          blocks <- c(
            blocks,
            sprintf('<data-dict %s>\n%s\n</data-dict>', attrs, body)
          )
        } else {
          blocks <- c(blocks, sprintf('<data-dict %s/>', attrs))
        }
      }

      unclaimed <- setdiff(names(self$data_sources), all_claimed)
      if (length(unclaimed) > 0) {
        tables <- list()
        for (name in unclaimed) {
          desc <- if (is.null(self$data_description)) {
            self$data_sources[[name]]$get_data_description()
          }
          tables[[name]] <- if (nzchar(desc %||% "")) {
            list(description = desc)
          } else {
            NULL
          }
        }
        yaml_str <- yaml::as.yaml(list(tables = tables), column.major = FALSE)
        yaml_str <- sub("\n$", "", yaml_str)
        blocks <- c(blocks, sprintf("<tables>\n%s\n</tables>", yaml_str))
      }

      paste(blocks, collapse = "\n\n")
    }
  )
)

# Utility function for loading file or string content
read_text <- function(x) {
  if (file.exists(x)) {
    read_utf8(x)
  } else {
    paste(x, collapse = "\n")
  }
}
