check_data_source <- function(
  x,
  ...,
  arg = caller_arg(x),
  call = caller_env()
) {
  if (!inherits(x, "DataSource")) {
    cli::cli_abort(
      "{.arg {arg}} must be a {.cls DataSource} object, not {.obj_type_friendly {x}}.",
      call = call
    )
  }
}


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
  if (!is_valid_sql_table_name(x)) {
    cli::cli_abort(
      c(
        "{.arg {arg}} must be a valid SQL table name",
        "i" = "Table names must begin with a letter and contain only letters, numbers, and underscores",
        "x" = "You provided: {.val {x}}"
      ),
      call = call
    )
  }

  invisible(NULL)
}

is_valid_sql_table_name <- function(x) {
  grepl("^[a-zA-Z][a-zA-Z0-9_]*$", x)
}


# SQL query validation --------------------------------------------------------

#' Check SQL query for disallowed operations
#'
#' Validates that a SQL query does not start with a disallowed operation.
#' This is a simple safety check, not full query parsing.
#'
#' @param query The SQL query string to check
#' @param ... These dots are for future extensions and must be empty.
#' @param arg Argument name to use in error messages
#' @param call Calling environment for error messages
#'
#' @details
#' Two categories of keywords are checked:
#'
#' **Always blocked** (no escape hatch):
#' DELETE, TRUNCATE, CREATE, DROP, ALTER, GRANT, REVOKE, EXEC, EXECUTE, CALL
#'
#' **Blocked unless escape hatch enabled**:
#' INSERT, UPDATE, MERGE, REPLACE, UPSERT
#'
#' The escape hatch can be enabled via
#' `options(querychat.enable_update_queries = TRUE)` or by setting the
#' environment variable `QUERYCHAT_ENABLE_UPDATE_QUERIES=true`.
#'
#' @return Invisibly returns `NULL` if validation passes. Otherwise throws an
#'   error.
#'
#' @noRd
check_query <- function(
  query,
  ...,
  arg = caller_arg(query),
  call = caller_env()
) {
  check_dots_empty()
  check_string(query, arg = arg, call = call)

  # Normalize: newlines/tabs -> space, collapse multiple spaces, trim, uppercase
  normalized <- query
  normalized <- gsub("[\r\n\t]+", " ", normalized)
  normalized <- gsub(" +", " ", normalized)
  normalized <- trimws(normalized)
  normalized <- toupper(normalized)

  # Always blocked - destructive/schema/admin operations
  always_blocked <- c(
    "DELETE",
    "TRUNCATE",
    "CREATE",
    "DROP",
    "ALTER",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL"
  )

  # Blocked unless escape hatch enabled - data modification
  update_keywords <- c("INSERT", "UPDATE", "MERGE", "REPLACE", "UPSERT")

  # Check always-blocked keywords first
  always_pattern <- paste0("^(", paste(always_blocked, collapse = "|"), ")\\b")
  if (grepl(always_pattern, normalized)) {
    matched <- regmatches(normalized, regexpr(always_pattern, normalized))
    cli::cli_abort(
      c(
        "Query appears to contain a disallowed operation: {matched}",
        "i" = "Only SELECT queries are allowed."
      ),
      call = call
    )
  }

  # Check update keywords (can be enabled via option or envvar)
  enable_updates <- isTRUE(getOption("querychat.enable_update_queries", FALSE))
  if (!enable_updates) {
    envvar <- Sys.getenv("QUERYCHAT_ENABLE_UPDATE_QUERIES", "")
    enable_updates <- tolower(envvar) %in% c("true", "1", "yes")
  }

  if (!enable_updates) {
    update_pattern <- paste0(
      "^(",
      paste(update_keywords, collapse = "|"),
      ")\\b"
    )
    if (grepl(update_pattern, normalized)) {
      matched <- regmatches(normalized, regexpr(update_pattern, normalized))
      cli::cli_abort(
        c(
          "Query appears to contain an update operation: {matched}",
          "i" = "Only SELECT queries are allowed.",
          "i" = "Set {.code options(querychat.enable_update_queries = TRUE)} or {.envvar QUERYCHAT_ENABLE_UPDATE_QUERIES=true} to allow update queries."
        ),
        call = call
      )
    }
  }

  invisible(NULL)
}
