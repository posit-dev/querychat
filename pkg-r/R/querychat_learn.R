#' Learn about a dataset with an interactive chat
#'
#' Launches a full-page chat app in which an assistant explores your data
#' source, interviews you about what it means, and writes a concise, reusable
#' description to `.querychat/<table_name>.md`. That file is picked up
#' automatically by future [querychat()] sessions for the same table, so the
#' effort carries forward into your real app.
#'
#' The assistant has access to the querying tools (`query`, and `visualize`
#' when \pkg{ggsql} is installed) plus `read`/`write`/`edit` file tools that are
#' restricted to the current working directory. It is *not* given the dashboard
#' filtering tools.
#'
#' @inheritParams querychat
#' @param greeting Optional initial message to display. If not provided, a
#'   greeting is generated that offers a few starting paths, including updating
#'   an existing description when one is found.
#' @param bookmark_store The bookmarking storage method. Passed to
#'   [shiny::enableBookmarking()]. Default is `"url"`.
#'
#' @return Invisibly returns a list with the session-specific `client` after
#'   the app stops. The data description is written to
#'   `.querychat/<table_name>.md`.
#'
#' @examplesIf rlang::is_interactive() && rlang::is_installed("RSQLite")
#' querychat_learn(mtcars)
#'
#' @export
querychat_learn <- function(
  data_source,
  table_name = missing_arg(),
  ...,
  client = NULL,
  greeting = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  cleanup = NA,
  bookmark_store = "url"
) {
  if (shiny::isRunning()) {
    cli::cli_abort(
      "{.fn querychat_learn} cannot be called from within a Shiny app."
    )
  }

  if (is_missing(table_name)) {
    if (inherits(data_source, "DataSource")) {
      table_name <- data_source$table_name
    } else if (is.data.frame(data_source)) {
      table_name <- deparse1(substitute(data_source))
    } else if (inherits(data_source, "pins_board")) {
      cli::cli_abort(
        "{.arg table_name} (the pin name) is required when {.arg data_source} is a pins board."
      )
    }
  }

  tools <- "query"
  if (rlang::is_installed("ggsql")) {
    tools <- c(tools, "visualize")
  }

  prompt_template <- system.file(
    "prompts",
    "learn",
    "prompt.md",
    package = "querychat"
  )

  check_bool(cleanup, allow_na = TRUE)
  if (is.data.frame(data_source)) {
    cleanup <- TRUE
  } else if (is.na(cleanup)) {
    cleanup <- FALSE
  }

  qc <- QueryChat$new(
    data_source = data_source,
    table_name = table_name,
    ...,
    client = client,
    greeting = greeting,
    tools = tools,
    categorical_threshold = categorical_threshold,
    extra_instructions = extra_instructions,
    prompt_template = prompt_template,
    cleanup = cleanup
  )

  if (is.null(greeting)) {
    tbl <- qc$data_source$table_name
    existing <- file.exists(
      file.path(getwd(), ".querychat", paste0(tbl, ".md"))
    )
    qc$greeting <- querychat_learn_greeting(tbl, has_existing = existing)
  }

  qc$learn(bookmark_store = bookmark_store)
}

# Build the learn-mode greeting, offering the analyst a few starting paths. The
# "update existing" path is only offered when a description file already exists.
querychat_learn_greeting <- function(table_name, has_existing = FALSE) {
  intro <- sprintf(
    "Hi! I can help you document the `%s` table so future querychat sessions understand it. I'll explore the data, ask you about the things only you know, and write a reusable description to `.querychat/%s.md`.\n\nHow would you like to start?",
    table_name,
    table_name
  )

  items <- c(
    '<li><span class="suggestion">Explore the data and draft a description for me</span></li>'
  )
  if (has_existing) {
    items <- c(
      items,
      '<li><span class="suggestion">Update the existing description</span></li>'
    )
  }
  items <- c(
    items,
    '<li><span class="suggestion">Let me walk you through what this data means</span></li>'
  )

  paste0(
    intro,
    "\n\n<ul>\n",
    paste(items, collapse = "\n"),
    "\n</ul>\n"
  )
}
