#' Create a system prompt for the chat model
#'
#' This function generates a system prompt for the chat model based on a data frame's
#' schema and optional additional context and instructions.
#'
#' @param df A data frame to generate schema information from.
#' @param table_name A string containing the name of the table in SQL queries.
#' @param data_description Optional string or existing file path. The contents
#'   should be in plain text or Markdown format, containing a description of the
#'   data frame or any additional context that might be helpful in understanding
#'   the data. This will be included in the system prompt for the chat model.
#' @param extra_instructions Optional string or existing file path. The contents
#'   should be in plain text or Markdown format, containing any additional
#'   instructions for the chat model. These will be appended at the end of the
#'   system prompt.
#' @param prompt_template Optional string or existing file path. If `NULL`, the
#'   default prompt file in the package will be used. The contents should
#'   contain a whisker template for the system prompt, with placeholders for
#'   `{{schema}}`, `{{data_description}}`, and `{{extra_instructions}}`.
#' @param categorical_threshold The maximum number of unique values for a text
#'   column to be considered categorical.
#' @param ... Ignored. Used to allow for future parameters.
#'
#' @return A string containing the system prompt for the chat model.
#'
#' @export
querychat_system_prompt <- function(
  df,
  table_name,
  ...,
  data_description = NULL,
  extra_instructions = NULL,
  prompt_template = NULL,
  categorical_threshold = 10
) {
  rlang::check_dots_empty()

  schema <- df_to_schema(df, table_name, categorical_threshold)

  data_description <- read_path_or_string(data_description, "data_description")
  extra_instructions <- read_path_or_string(
    extra_instructions,
    "extra_instructions"
  )
  if (is.null(prompt_template)) {
    prompt_template <- system.file("prompt", "prompt.md", package = "querychat")
  }
  prompt_text <- read_path_or_string(prompt_template, "prompt_template")

  processed_template <-
    whisker::whisker.render(
      prompt_text,
      list(
        schema = schema,
        data_description = data_description,
        extra_instructions = extra_instructions
      )
    )

  attr(processed_template, "table_name") <- table_name

  processed_template
}

read_path_or_string <- function(x, name) {
  if (is.null(x)) {
    return(NULL)
  }
  if (!is.character(x)) {
    stop(sprintf("`%s=` must be a string or a path to a file.", name))
  }
  if (file.exists(x)) {
    x <- readLines(x, warn = FALSE)
  }
  return(paste(x, collapse = "\n"))
}


#' Generate a schema description from a data frame
#'
#' This function generates a schema description for a data frame, including
#' the column names, their types, and additional information such as ranges for
#' numeric columns and unique values for text columns.
#'
#' @param df A data frame to generate schema information from.
#' @param table_name A string containing the name of the table in SQL queries.
#' @param categorical_threshold The maximum number of unique values for a text column to be considered categorical.
#'
#' @return A string containing the schema description for the data frame.
#' The schema includes the table name, column names, their types, and additional
#' information such as ranges for numeric columns and unique values for text columns.
#' @export
df_to_schema <- function(
  df,
  table_name = deparse(substitute(df)),
  categorical_threshold = 10
) {
  schema <- c(paste("Table:", table_name), "Columns:")

  column_info <- lapply(names(df), function(column) {
    # Map R classes to SQL-like types
    sql_type <- if (is.integer(df[[column]])) {
      "INTEGER"
    } else if (is.numeric(df[[column]])) {
      "FLOAT"
    } else if (is.logical(df[[column]])) {
      "BOOLEAN"
    } else if (inherits(df[[column]], "Date")) {
      "DATE"
    } else if (inherits(df[[column]], "POSIXt")) {
      "TIMESTAMP"
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
    } else if (sql_type %in% c("INTEGER", "FLOAT", "DATE", "DATETIME")) {
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
