maybe_truncate <- function(df, max_rows) {
  is_lazy <- inherits(df, "tbl_sql")

  if (is.null(max_rows)) {
    if (is_lazy) {
      df <- dplyr::collect(df)
    }
    total_rows <- nrow(df)
    total_cols <- ncol(df)
  } else if (is_lazy) {
    total_rows <- dplyr::pull(dplyr::tally(df))
    total_cols <- ncol(df)
    df <- if (total_rows > max_rows) {
      dplyr::collect(head(df, max_rows))
    } else {
      dplyr::collect(df)
    }
  } else {
    total_rows <- nrow(df)
    total_cols <- ncol(df)
    if (total_rows > max_rows) {
      df <- head(df, max_rows)
    }
  }

  truncated <- !is.null(max_rows) && total_rows > max_rows

  if (truncated) {
    warning(
      "querychat: Displaying ",
      max_rows,
      " of ",
      total_rows,
      " rows. ",
      "Set `max_rows` to increase or `NULL` to disable.",
      call. = FALSE
    )
  }

  list(
    df = df,
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
