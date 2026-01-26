# Extracted from test-SnowflakeSource.R:107

# test -------------------------------------------------------------------------
it("returns empty list on error with proper message", {
  skip_if_not_installed("RSQLite")

  # SQLite doesn't have SHOW SEMANTIC VIEWS, so it should error
  conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
  withr::defer(DBI::dbDisconnect(conn))

  # Without tryCatch wrapping, this should error (not return empty list)
  expect_error(
    discover_semantic_views_impl(conn),
    "SEMANTIC"
  )
})
