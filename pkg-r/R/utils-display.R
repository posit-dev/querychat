maybe_truncate <- function(df, max_rows) {
  total_rows <- nrow(df)
  total_cols <- ncol(df)
  truncated <- !is.null(max_rows) && total_rows > max_rows

  if (truncated) {
    display_df <- head(df, max_rows)
    warning(
      "querychat: Displaying ",
      max_rows,
      " of ",
      total_rows,
      " rows. ",
      "Set `max_rows` to increase or `NULL` to disable.",
      call. = FALSE
    )
  } else {
    display_df <- df
  }

  list(
    df = display_df,
    total_rows = total_rows,
    total_cols = total_cols,
    truncated = truncated
  )
}

truncation_info_message <- function(result) {
  if (result$truncated) {
    sprintf(
      "Showing first %d of %d rows (%d columns).",
      nrow(result$df),
      result$total_rows,
      result$total_cols
    )
  } else {
    sprintf(
      "Data has %d rows and %d columns.",
      result$total_rows,
      result$total_cols
    )
  }
}
