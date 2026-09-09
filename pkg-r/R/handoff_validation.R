validate_handoff_source <- function(source, handoff_type) {
  if (!S7::S7_inherits(handoff_type, HandoffType)) {
    cli::cli_abort("{.arg handoff_type} must be a <HandoffType> object.")
  }
  if (
    !is.character(source) ||
      length(source) != 1L ||
      is.na(source) ||
      !nzchar(trimws(source))
  ) {
    cli::cli_abort("Generated handoff source must be a non-empty string.")
  }
  if (identical(handoff_type@structure, "notebook-json")) {
    validate_notebook_handoff_source(source, handoff_type@language)
  }

  invisible(NULL)
}

validate_notebook_handoff_source <- function(source, language) {
  notebook <- tryCatch(
    jsonlite::parse_json(source),
    error = function(error) abort_invalid_notebook_source()
  )
  if (
    !is.list(notebook) ||
      is.null(names(notebook)) ||
      !is.list(notebook$cells) ||
      !is.list(notebook$metadata) ||
      !is.numeric(notebook$nbformat)
  ) {
    abort_invalid_notebook_source()
  }

  label <- handoff_language_label(language)
  kernelspec <- notebook$metadata$kernelspec
  actual <- if (is.list(kernelspec)) kernelspec$language else NULL
  if (!is.character(actual) || length(actual) != 1L || is.na(actual)) {
    cli::cli_abort("Generated notebook must declare a {label} kernelspec.")
  }
  if (tolower(actual) != tolower(language)) {
    cli::cli_abort(
      "Generated notebook must declare a {label} kernelspec, not {actual}."
    )
  }

  invisible(NULL)
}

abort_invalid_notebook_source <- function() {
  cli::cli_abort("Generated source is not valid notebook JSON.")
}
