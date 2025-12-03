# SQL table name validation ----------------------------------------------

#' Check SQL table name validity
#'
#' Validates that a string is a valid SQL table name. A valid SQL table name
#' must begin with a letter and contain only letters, numbers, and underscores.
#'
#' @param x The value to check
#' @param ... These dots are for future extensions and must be empty.
#' @param allow_null Logical. If `TRUE`, `NULL` is accepted as a valid value.
#' @param arg Argument name to use in error messages
#' @param call Calling environment for error messages
#'
#' @return Invisibly returns `NULL` if validation passes. Otherwise throws an error.
#' @keywords internal
#' @noRd
check_sql_table_name <- function(
  x,
  ...,
  allow_null = FALSE,
  arg = caller_arg(x),
  call = caller_env()
) {
  check_dots_empty()

  # Check if NULL is allowed
  if (allow_null && is.null(x)) {
    return(invisible(NULL))
  }

  # First check it's a string
  check_string(x, allow_null = allow_null, arg = arg, call = call)

  # Then validate SQL table name pattern
  if (!grepl("^[a-zA-Z][a-zA-Z0-9_]*$", x)) {
    cli::cli_abort(
      "{.arg {arg}} must be a valid SQL table name.",
      "i" = "Table names must begin with a letter and contain only letters, numbers, and underscores.",
      "x" = "You provided: {.val {x}}",
      call = call
    )
  }

  invisible(NULL)
}
