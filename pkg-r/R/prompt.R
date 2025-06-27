#' Create a system prompt for the chat model
#'
#' This function generates a system prompt for the chat model based on a data frame's
#' schema and optional additional context and instructions.
#'
#' @param df A data frame to generate schema information from.
#' @param tbl_name A string containing the name of the table in SQL queries.
#' @param data_description Optional string in plain text or Markdown format, containing
#'   a description of the data frame or any additional context that might be
#'   helpful in understanding the data. This will be included in the system
#'   prompt for the chat model.
#' @param extra_instructions Optional string in plain text or Markdown format, containing
#'   any additional instructions for the chat model. These will be appended at
#'   the end of the system prompt.
#' @param categorical_threshold The maximum number of unique values for a text column to be considered categorical.
#' @param prompt_path Optional string containing the path to a custom prompt file. If
#'   `NULL`, the default prompt file in the package will be used. This file should
#'   contain a whisker template for the system prompt, with placeholders for `{{schema}}`,
#'   `{{data_description}}` [optional], and `{{extra_instructions}}` [optional].
#'
#' @return A string containing the system prompt for the chat model.
#'
#' @export
querychat_system_prompt <- function(
    df,
    name,
    data_description = NULL,
    extra_instructions = NULL,
    categorical_threshold = 10,
    prompt_path = NULL) {
  schema <- df_to_schema(df, name, categorical_threshold)

  if (!is.null(data_description)) {
    data_description <- paste(data_description, collapse = "\n")
  }
  if (!is.null(extra_instructions)) {
    extra_instructions <- paste(extra_instructions, collapse = "\n")
  }

  # Read the prompt file
  if (is.null(prompt_path)) {
    prompt_path <- system.file("prompt", "prompt.md", package = "querychat")
  }
  if (!file.exists(prompt_path)) {
    stop("Prompt file not found at: ", prompt_path)
  }
  prompt_content <- readLines(prompt_path, warn = FALSE)
  prompt_text <- paste(prompt_content, collapse = "\n")

  whisker::whisker.render(
    prompt_text,
    list(
      schema = schema,
      data_description = data_description,
      extra_instructions = extra_instructions
    )
  )
}

df_to_schema <- function(
    df,
    name = deparse(substitute(df)),
    categorical_threshold) {
  schema <- c(paste("Table:", name), "Columns:")

  column_info <- lapply(names(df), function(column) {
    # Map R classes to SQL-like types
    sql_type <- if (is.integer(df[[column]])) {
      "INTEGER"
    } else if (is.numeric(df[[column]])) {
      "FLOAT"
    } else if (is.logical(df[[column]])) {
      "BOOLEAN"
    } else if (inherits(df[[column]], "POSIXt")) {
      "DATETIME"
    } else {
      "TEXT"
    }

    info <- paste0("- ", column, " (", sql_type, ")")

    # For TEXT columns, check if they're categorical
    if (sql_type == "TEXT") {
      unique_values <- length(unique(df[[column]]))
      if (unique_values <= categorical_threshold) {
        categories <- unique(df[[column]])
        categories_str <- paste0("'", categories, "'", collapse = ", ")
        info <- c(info, paste0("  Categorical values: ", categories_str))
      }
    } else if (sql_type %in% c("INTEGER", "FLOAT", "DATETIME")) {
      rng <- range(df[[column]], na.rm = TRUE)
      if (all(is.na(rng))) {
        info <- c(info, "  Range: NULL to NULL")
      } else {
        info <- c(info, paste0("  Range: ", rng[1], " to ", rng[2]))
      }
    }
    return(info)
  })

  schema <- c(schema, unlist(column_info))
  return(paste(schema, collapse = "\n"))
}
