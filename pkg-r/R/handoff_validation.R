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

  invisible(NULL)
}
