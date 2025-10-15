#' Code editor input for Shiny
#'
#' Creates an interactive code editor input that can be used in Shiny
#' applications. The editor provides syntax highlighting, line numbers, and
#' other code editing features powered by Prism Code Editor.
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
#' The editor automatically switches between `theme_light` and `theme_dark`
#' when used with [bslib::input_dark_mode()].
#'
#' @examples
#' \dontrun{
#' library(shiny)
#' library(querychat)
#'
#' ui <- fluidPage(
#'   input_code_editor(
#'     "sql_query",
#'     value = "SELECT * FROM table",
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
#' @param id Input ID. Access the current value with `input$<id>`.
#' @param value Initial code content. Default is an empty string.
#' @param label Display label for the input. Default is `NULL` for no label.
#' @param ... Must be empty. Prevents accidentally passing unnamed arguments.
#' @param language Programming language for syntax highlighting. Must be one of:
#'   `"sql"`, `"python"`, `"r"`, `"javascript"`, `"html"`, `"css"`, `"json"`,
#'   `"bash"`, `"markdown"`, `"yaml"`, `"xml"`. Default is `"sql"`.
#' @param height CSS height of the editor. Default is `"300px"`.
#' @param width CSS width of the editor. Default is `"100%"`.
#' @param theme_light Theme to use in light mode. See [code_editor_themes()] for
#'   available themes. Default is `"github-light"`.
#' @param theme_dark Theme to use in dark mode. See [code_editor_themes()] for
#'   available themes. Default is `"github-dark"`.
#' @param read_only Whether the editor should be read-only. Default is `FALSE`.
#' @param line_numbers Whether to show line numbers. Default is `TRUE`.
#' @param word_wrap Whether to wrap long lines. Default is `FALSE`.
#' @param tab_size Number of spaces per tab. Default is `2`.
#' @param indentation Type of indentation: `"space"` or `"tab"`. Default is
#'   `"space"`.
#' @param session Shiny session object, for expert use only.
#'
#' @return An HTML tag object that can be included in a Shiny UI.
#'
#' @describeIn input_code_editor Create a light-weight code editor input
#' @export
input_code_editor <- function(
  id,
  value = "",
  label = NULL,
  ...,
  language = "sql",
  height = "auto",
  width = "100%",
  theme_light = "github-light",
  theme_dark = "github-dark",
  read_only = FALSE,
  line_numbers = TRUE,
  word_wrap = FALSE,
  tab_size = 2,
  indentation = c("space", "tab"),
  fill = TRUE
) {
  # Ensure no extra arguments
  rlang::check_dots_empty()
  stopifnot(rlang::is_bool(fill))

  # Validate inputs
  language <- arg_match_language(language)
  theme_light <- arg_match_theme(theme_light, "theme_light")
  theme_dark <- arg_match_theme(theme_dark, "theme_dark")

  indentation <- match.arg(indentation)
  insert_spaces <- (indentation == "space")

  # Create label element
  label_tag <- asNamespace("shiny")[["shinyInputLabel"]](id, label)

  # Create inner container that will hold the actual editor
  editor_inner <- htmltools::tags$div(
    class = "code-editor",
    bslib::as_fill_item(),
    style = htmltools::css(
      display = "grid"
    )
  )

  htmltools::tags$div(
    id = id,
    class = "shiny-input-code-editor",
    style = htmltools::css(
      height = height,
      width = width
    ),
    if (fill) bslib::as_fill_item(),
    bslib::as_fillable_container(),
    `data-language` = language,
    `data-initial-code` = value,
    `data-theme-light` = theme_light,
    `data-theme-dark` = theme_dark,
    `data-read-only` = tolower(as.character(read_only)),
    `data-line-numbers` = tolower(as.character(line_numbers)),
    `data-word-wrap` = tolower(as.character(word_wrap)),
    `data-tab-size` = as.character(tab_size),
    `data-insert-spaces` = tolower(as.character(insert_spaces)),
    label_tag,
    editor_inner,
    html_dependency_code_editor(),
  )
}

#' @describeIn input_code_editor Update the code editor input value and settings
#' @export
update_code_editor <- function(
  id,
  value = NULL,
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
    language <- arg_match_language(language, "language")
  }
  if (!is.null(theme_light)) {
    theme_light <- arg_match_theme(theme_light, "theme_light")
  }
  if (!is.null(theme_dark)) {
    theme_dark <- arg_match_theme(theme_dark, "theme_dark")
  }

  # Build message with only non-NULL values
  message <- list()

  if (!is.null(value)) {
    message$code <- value
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

#' @describeIn input_code_editor List available code editor syntax highlighting
#'   themes
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

arg_match_theme <- function(theme, arg_name = "theme") {
  if (is.null(theme)) {
    return(invisible(NULL))
  }

  available_themes <- code_editor_themes()

  rlang::arg_match(
    theme,
    values = available_themes,
    error_arg = arg_name,
    error_call = rlang::caller_env()
  )
}

arg_match_language <- function(language, arg_name = "language") {
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

  rlang::arg_match(
    language,
    values = supported_languages,
    error_arg = arg_name,
    error_call = rlang::caller_env()
  )
}
