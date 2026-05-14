describe("maybe_truncate()", {
  large_df <- data.frame(x = seq_len(200), y = seq_len(200))
  small_df <- data.frame(x = seq_len(5), y = seq_len(5))

  it("truncates when exceeds max_rows", {
    result <- suppressWarnings(maybe_truncate(large_df, max_rows = 50))
    expect_equal(nrow(result$df), 50)
    expect_equal(result$total_rows, 200)
    expect_equal(result$total_cols, 2)
    expect_true(result$truncated)
  })

  it("does not truncate when under max_rows", {
    result <- maybe_truncate(small_df, max_rows = 50)
    expect_equal(nrow(result$df), 5)
    expect_equal(result$total_rows, 5)
    expect_false(result$truncated)
  })

  it("does not truncate when max_rows is NULL", {
    result <- maybe_truncate(large_df, max_rows = NULL)
    expect_equal(nrow(result$df), 200)
    expect_false(result$truncated)
  })

  it("does not truncate when exactly at max_rows", {
    result <- maybe_truncate(large_df, max_rows = 200)
    expect_equal(nrow(result$df), 200)
    expect_false(result$truncated)
  })

  it("emits warning when truncated", {
    expect_warning(
      maybe_truncate(large_df, max_rows = 50),
      "Displaying 50 of 200 rows"
    )
  })

  it("does not emit warning when not truncated", {
    expect_no_warning(maybe_truncate(small_df, max_rows = 50))
  })

  it("collects tbl_sql before truncating", {
    skip_if_not_installed("duckdb")
    skip_if_not_installed("dbplyr")
    skip_if_not_installed("dplyr")

    conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
    withr::defer(DBI::dbDisconnect(conn, shutdown = TRUE))

    DBI::dbWriteTable(conn, "test_data", large_df)
    tbl <- dplyr::tbl(conn, "test_data")

    result <- suppressWarnings(maybe_truncate(tbl, max_rows = 50))
    expect_true(is.data.frame(result$df))
    expect_equal(nrow(result$df), 50)
    expect_equal(result$total_rows, 200)
    expect_true(result$truncated)
  })
})

describe("truncation_info_message()", {
  it("shows truncation message when truncated", {
    result <- suppressWarnings(
      maybe_truncate(
        data.frame(x = seq_len(200), y = seq_len(200)),
        max_rows = 50
      )
    )
    expect_equal(
      truncation_info_message(result),
      "Showing first 50 of 200 rows (2 columns)."
    )
  })

  it("shows full data message when not truncated", {
    result <- maybe_truncate(
      data.frame(x = seq_len(5), y = seq_len(5)),
      max_rows = 50
    )
    expect_equal(
      truncation_info_message(result),
      "Data has 5 rows and 2 columns."
    )
  })
})
