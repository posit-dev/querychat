#' Clean SQL query for safe execution with dbplyr
#'
#' This function cleans an SQL query by removing comments, trailing semicolons,
#' and handling other syntax issues that can cause problems with dbplyr's tbl() function.
#'
#' @param query A character string containing an SQL query
#' @param enforce_select Logical, whether to validate that the query is a SELECT statement
#' @return A cleaned SQL query string or NULL if the query is empty or invalid
#' @keywords internal
clean_sql <- function(query, enforce_select = TRUE) {
  # Check input
  if (!is.character(query)) {
    query <- as.character(query)
  }

  # Save original query for error messages
  original_query <- query

  # First, handle nested multiline comments safely
  query <- gsub("/\\*[^*]*\\*+(?:[^/*][^*]*\\*+)*/", "", query, perl = TRUE)

  # Remove single-line comments (--) anywhere in the string
  query <- gsub("--[^\n]*", "", query)

  # Remove GO statements (common in T-SQL as batch separators)
  query <- gsub("\\bGO\\b", "", query, ignore.case = TRUE)

  # Split multiple statements and keep only the first one
  # First, check if we have any semicolons
  if (grepl(";", query, fixed = TRUE)) {
    # Check if we have quotes that might contain semicolons
    quote_matches <- gregexpr("'[^']*'", query, perl = TRUE)
    if (quote_matches[[1]][1] != -1) {
      # We have quoted strings, check if any contain semicolons
      has_quoted_semicolon <- FALSE

      for (i in 1:length(quote_matches[[1]])) {
        start_pos <- quote_matches[[1]][i]
        end_pos <- start_pos + attr(quote_matches[[1]], "match.length")[i] - 1
        quoted_part <- substr(query, start_pos, end_pos)

        if (grepl(";", quoted_part, fixed = TRUE)) {
          has_quoted_semicolon <- TRUE
          break
        }
      }

      if (!has_quoted_semicolon) {
        # No semicolons inside quotes, we can safely split by semicolons
        parts <- strsplit(query, ";", fixed = TRUE)[[1]]
        if (length(parts) > 1) {
          first_statement <- trimws(parts[1])
          rlang::warn(
            c(
              "Multiple SQL statements detected. Only the first statement will be used:",
              "i" = paste0(
                "Using: ",
                substr(first_statement, 1, 60),
                if (nchar(first_statement) > 60) "..." else ""
              ),
              "i" = paste0(
                "Ignoring ",
                length(parts) - 1,
                " additional statement(s)"
              )
            )
          )
          query <- first_statement
        }
      }
    } else {
      # No quotes, we can safely split by semicolons
      parts <- strsplit(query, ";", fixed = TRUE)[[1]]
      if (length(parts) > 1) {
        first_statement <- trimws(parts[1])
        rlang::warn(
          c(
            "Multiple SQL statements detected. Only the first statement will be used:",
            "i" = paste0(
              "Using: ",
              substr(first_statement, 1, 60),
              if (nchar(first_statement) > 60) "..." else ""
            ),
            "i" = paste0(
              "Ignoring ",
              length(parts) - 1,
              " additional statement(s)"
            )
          )
        )
        query <- first_statement
      }
    }
  }

  # Remove trailing semicolons
  query <- gsub(";\\s*$", "", query)

  # Trim whitespace
  query <- trimws(query)

  # Handle empty query
  if (nchar(query) == 0) {
    return(NULL)
  }

  # Check for unbalanced quotes
  single_quotes <- gregexpr("'", query, fixed = TRUE)[[1]]
  if (length(single_quotes) > 0 && single_quotes[1] != -1) {
    single_quote_count <- length(single_quotes)
    if (single_quote_count %% 2 != 0) {
      rlang::warn(
        c(
          "SQL contains unbalanced single quotes, which may cause errors:",
          "i" = substr(original_query, 1, 100)
        )
      )
      # Attempt to fix by adding a closing quote at the end
      query <- paste0(query, "'")
    }
  }

  double_quotes <- gregexpr("\"", query, fixed = TRUE)[[1]]
  if (length(double_quotes) > 0 && double_quotes[1] != -1) {
    double_quote_count <- length(double_quotes)
    if (double_quote_count %% 2 != 0) {
      rlang::warn(
        c(
          "SQL contains unbalanced double quotes, which may cause errors:",
          "i" = substr(original_query, 1, 100)
        )
      )
      # Attempt to fix by adding a closing quote at the end
      query <- paste0(query, "\"")
    }
  }

  # Check for unbalanced parentheses
  open_parens <- gregexpr("\\(", query, perl = TRUE)[[1]]
  if (open_parens[1] == -1) {
    open_parens <- integer(0)
  }

  close_parens <- gregexpr("\\)", query, perl = TRUE)[[1]]
  if (close_parens[1] == -1) {
    close_parens <- integer(0)
  }

  if (length(open_parens) != length(close_parens)) {
    rlang::warn(
      c(
        "SQL contains unbalanced parentheses, which may cause errors:",
        "i" = substr(original_query, 1, 100)
      )
    )

    # Attempt to fix by adding closing parentheses if there are more open ones
    if (length(open_parens) > length(close_parens)) {
      diff <- length(open_parens) - length(close_parens)
      query <- paste0(query, paste0(rep(")", diff), collapse = ""))
    }
  }

  # Filter out non-standard characters that might break SQL
  query <- gsub("[^\x20-\x7E\r\n\t]", "", query)

  # Validate that it's a SELECT statement if requested
  if (enforce_select) {
    # Check if it starts with SELECT (case insensitive, allowing for whitespace)
    if (!grepl("^\\s*SELECT\\b", query, ignore.case = TRUE)) {
      rlang::abort(
        c(
          "SQL query does not appear to start with SELECT:",
          "x" = substr(query, 1, 100),
          "i" = "dbplyr::tbl() requires a SELECT statement."
        )
      )
    }
  }

  # Final trimming
  query <- trimws(query)

  return(query)
}
