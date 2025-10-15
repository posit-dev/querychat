#' HTML dependency for the code editor component
#'
#' This function returns an htmlDependency object that bundles all necessary
#' JavaScript and CSS files for the Prism Code Editor component.
#'
#' @return An htmlDependency object
#' @keywords internal
html_dependency_code_editor <- function() {
  dep_code_editor <- htmltools::htmlDependency(
    name = "shiny-input-code-editor",
    version = utils::packageVersion("querychat"),
    package = "querychat",
    src = "js",
    script = "code-editor-binding.js",
    stylesheet = "code-editor.css",
    all_files = FALSE
  )

  htmltools::tagList(
    html_dependency_prism_code_editor(),
    dep_code_editor
  )
}

html_dependency_prism_code_editor <- function() {
  htmltools::htmlDependency(
    name = "prism-code-editor",
    version = "3.0.0",
    package = "querychat",
    src = "js/prism-code-editor",
    script = list(src = "index.js", type = "module"),
    stylesheet = c("layout.css", "copy.css"),
    all_files = TRUE
  )
}

#' Get available code editor themes
#'
#' Returns a character vector of available theme names that can be used with
#' `input_code_editor()` and `update_code_editor()`.
#'
#' @return A character vector of theme names
#' @export
code_editor_themes <- function() {
  themes_dir <- system.file(
    "js/prism-code-editor/themes",
    package = "querychat"
  )

  if (!dir.exists(themes_dir)) {
    return(character(0))
  }

  theme_files <- list.files(themes_dir, pattern = "\\.css$")
  sub("\\.css$", "", theme_files)
}

#' Validate theme name
#'
#' @param theme A theme name
#' @param arg_name Name of the argument (for error messages)
#' @return The validated theme name (invisibly)
#' @keywords internal
validate_theme <- function(theme, arg_name = "theme") {
  if (is.null(theme)) {
    return(invisible(NULL))
  }

  available_themes <- code_editor_themes()

  if (!theme %in% available_themes) {
    cli::cli_abort(c(
      "{.arg {arg_name}} must be one of the available themes.",
      "x" = "You provided: {.val {theme}}",
      "i" = "Available themes: {.val {available_themes}}"
    ))
  }

  invisible(theme)
}

#' Validate language name
#'
#' @param language A language identifier
#' @param arg_name Name of the argument (for error messages)
#' @return The validated language name (invisibly)
#' @keywords internal
validate_language <- function(language, arg_name = "language") {
  if (is.null(language)) {
    return(invisible(NULL))
  }

  # List of initially supported languages - these match the grammar files
  # we've bundled from prism-code-editor
  supported_languages <- c(
    "sql",
    "python",
    "r",
    "javascript",
    "html",
    "css",
    "json",
    "bash",
    "markdown",
    "yaml",
    "xml"
  )

  if (!language %in% supported_languages) {
    cli::cli_abort(c(
      "{.arg {arg_name}} must be one of the supported languages.",
      "x" = "You provided: {.val {language}}",
      "i" = "Supported languages: {.val {supported_languages}}"
    ))
  }

  invisible(language)
}

#' Code editor input for Shiny
#'
#' Creates an interactive code editor input that can be used in Shiny applications.
#' The editor provides syntax highlighting, line numbers, and other code editing
#' features powered by Prism Code Editor.
#'
#' @param id Input ID. Access the current value with `input$<id>`.
#' @param code Initial code content. Default is an empty string.
#' @param language Programming language for syntax highlighting. Must be one of:
#'   `"sql"`, `"python"`, `"r"`, `"javascript"`, `"html"`, `"css"`, `"json"`,
#'   `"bash"`, `"markdown"`, `"yaml"`, `"xml"`. Default is `"sql"`.
#' @param height CSS height of the editor. Default is `"300px"`.
#' @param width CSS width of the editor. Default is `"100%"`.
#' @param theme_light Theme to use in light mode. See [code_editor_themes()] for
#'   available themes. Default is `"github-light"`.
#' @param theme_dark Theme to use in dark mode. See [code_editor_themes()] for
#'   available themes. Default is `"github-dark"`.
#' @param placeholder Placeholder text shown when editor is empty. Default is `NULL`.
#' @param read_only Whether the editor should be read-only. Default is `FALSE`.
#' @param line_numbers Whether to show line numbers. Default is `TRUE`.
#' @param word_wrap Whether to wrap long lines. Default is `FALSE`.
#' @param tab_size Number of spaces per tab. Default is `2`.
#' @param indentation Type of indentation: `"space"` or `"tab"`. Default is `"space"`.
#'
#' @return An HTML tag object that can be included in a Shiny UI.
#'
#' @section Keyboard shortcuts:
#' The editor supports the following keyboard shortcuts:
#' - `Ctrl/Cmd+Enter`: Submit the current code to R
#' - `Ctrl/Cmd+Z`: Undo
#' - `Ctrl/Cmd+Shift+Z`: Redo
#' - `Tab`: Indent selection
#' - `Shift+Tab`: Dedent selection
#'
#' @section Update triggers:
#' The editor value is sent to R when:
#' - The editor loses focus (blur event)
#' - The user presses `Ctrl/Cmd+Enter`
#'
#' @section Theme switching:
#' The editor automatically switches between `theme_light` and `theme_dark` based
#' on the Bootstrap 5 `data-bs-theme` attribute on the `<html>` element. This
#' integrates seamlessly with `bslib::bs_theme()` theme switching.
#'
#' @examples
#' \dontrun{
#' library(shiny)
#'
#' ui <- fluidPage(
#'   input_code_editor(
#'     "sql_query",
#'     code = "SELECT * FROM table",
#'     language = "sql"
#'   )
#' )
#'
#' server <- function(input, output, session) {
#'   observe({
#'     print(input$sql_query)
#'   })
#' }
#'
#' shinyApp(ui, server)
#' }
#'
#' @seealso
#' - [update_code_editor()] to update the editor from the server
#' - [code_editor_themes()] to see available themes
#'
#' @export
input_code_editor <- function(
  id,
  code = "",
  language = "sql",
  height = "300px",
  width = "100%",
  theme_light = "github-light",
  theme_dark = "github-dark",
  placeholder = NULL,
  read_only = FALSE,
  line_numbers = TRUE,
  word_wrap = FALSE,
  tab_size = 2,
  indentation = c("space", "tab")
) {
  # Validate inputs
  validate_language(language, "language")
  validate_theme(theme_light, "theme_light")
  validate_theme(theme_dark, "theme_dark")

  indentation <- match.arg(indentation)
  insert_spaces <- (indentation == "space")

  # Construct the base path to the htmldep folder for use by JavaScript
  # This will be used by the binding to construct paths to language files and themes
  base_path <- "prism-code-editor"

  # Create the editor container div with all configuration as data attributes
  editor_div <- htmltools::tags$div(
    id = id,
    class = "code-editor-input",
    style = htmltools::css(
      height = height,
      width = width,
      display = "grid"
    ),
    `data-language` = language,
    `data-initial-code` = code,
    `data-theme-light` = theme_light,
    `data-theme-dark` = theme_dark,
    `data-read-only` = tolower(as.character(read_only)),
    `data-line-numbers` = tolower(as.character(line_numbers)),
    `data-word-wrap` = tolower(as.character(word_wrap)),
    `data-tab-size` = as.character(tab_size),
    `data-insert-spaces` = tolower(as.character(insert_spaces)),
    `data-placeholder` = placeholder,
    `data-base-path` = base_path
  )

  # Return with htmlDependency attached
  htmltools::tagList(
    html_dependency_code_editor(),
    editor_div
  )
}

#' Update a code editor from the server
#'
#' Update the code, language, themes, or other options of a code editor from the
#' server side.
#'
#' @param id The input ID of the editor to update.
#' @param code New code content. If `NULL`, the code is not changed.
#' @param ... Reserved for future use. Must be named arguments.
#' @param language New programming language. If `NULL`, the language is not changed.
#'   See [input_code_editor()] for supported languages.
#' @param theme_light New light theme. If `NULL`, the theme is not changed.
#'   See [code_editor_themes()] for available themes.
#' @param theme_dark New dark theme. If `NULL`, the theme is not changed.
#'   See [code_editor_themes()] for available themes.
#' @param read_only New read-only state. If `NULL`, the state is not changed.
#' @param line_numbers New line numbers setting. If `NULL`, the setting is not changed.
#' @param word_wrap New word wrap setting. If `NULL`, the setting is not changed.
#' @param tab_size New tab size. If `NULL`, the size is not changed.
#' @param indentation New indentation type: `"space"` or `"tab"`. If `NULL`, the
#'   type is not changed.
#' @param session The Shiny session object. Defaults to the current session.
#'
#' @return Called for its side effect of updating the editor. Invisibly returns `NULL`.
#'
#' @examples
#' \dontrun{
#' library(shiny)
#'
#' ui <- fluidPage(
#'   actionButton("change_lang", "Switch to Python"),
#'   input_code_editor(
#'     "code",
#'     code = "SELECT * FROM table",
#'     language = "sql"
#'   )
#' )
#'
#' server <- function(input, output, session) {
#'   observeEvent(input$change_lang, {
#'     update_code_editor(
#'       "code",
#'       code = "print('Hello, world!')",
#'       language = "python"
#'     )
#'   })
#' }
#'
#' shinyApp(ui, server)
#' }
#'
#' @seealso [input_code_editor()]
#'
#' @export
update_code_editor <- function(
  id,
  code = NULL,
  ...,
  language = NULL,
  theme_light = NULL,
  theme_dark = NULL,
  read_only = NULL,
  line_numbers = NULL,
  word_wrap = NULL,
  tab_size = NULL,
  indentation = NULL,
  session = shiny::getDefaultReactiveDomain()
) {
  # Ensure no extra arguments
  rlang::check_dots_empty()

  # Validate inputs if provided
  if (!is.null(language)) {
    validate_language(language, "language")
  }
  if (!is.null(theme_light)) {
    validate_theme(theme_light, "theme_light")
  }
  if (!is.null(theme_dark)) {
    validate_theme(theme_dark, "theme_dark")
  }

  # Build message with only non-NULL values
  message <- list()

  if (!is.null(code)) {
    message$code <- code
  }
  if (!is.null(language)) {
    message$language <- language
  }
  if (!is.null(theme_light)) {
    message$theme_light <- theme_light
  }
  if (!is.null(theme_dark)) {
    message$theme_dark <- theme_dark
  }
  if (!is.null(read_only)) {
    message$read_only <- read_only
  }
  if (!is.null(line_numbers)) {
    message$line_numbers <- line_numbers
  }
  if (!is.null(word_wrap)) {
    message$word_wrap <- word_wrap
  }
  if (!is.null(tab_size)) {
    message$tab_size <- tab_size
  }
  if (!is.null(indentation)) {
    if (!indentation %in% c("space", "tab")) {
      cli::cli_abort(c(
        "{.arg indentation} must be either {.val space} or {.val tab}.",
        "x" = "You provided: {.val {indentation}}"
      ))
    }
    message$indentation <- indentation
  }

  # Send message to JavaScript binding
  session$sendInputMessage(id, message)

  invisible(NULL)
}
