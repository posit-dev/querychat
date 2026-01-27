# Extracted from test-SnowflakeSource.R:95

# test -------------------------------------------------------------------------
it("has_semantic_views() returns FALSE before get_schema() is called", {
  skip_if_not_installed("RSQLite")

  conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
  withr::defer(DBI::dbDisconnect(conn))
  DBI::dbWriteTable(conn, "test_table", data.frame(x = 1:3))

  source <- DBISource$new(conn, "test_table")
  expect_false(source$has_semantic_views())
})
it("has_semantic_views() returns FALSE for non-Snowflake after get_schema()", {
  skip_if_not_installed("RSQLite")

  conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
  withr::defer(DBI::dbDisconnect(conn))
  DBI::dbWriteTable(conn, "test_table", data.frame(x = 1:3))

  source <- DBISource$new(conn, "test_table")
  source$get_schema()
  expect_false(source$has_semantic_views())
})
