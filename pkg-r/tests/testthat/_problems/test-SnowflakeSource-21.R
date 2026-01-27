# Extracted from test-SnowflakeSource.R:21

# test -------------------------------------------------------------------------
it("formats single semantic view correctly", {
  views <- list(
    list(name = "db.schema.view", ddl = "CREATE SEMANTIC VIEW test_view")
  )
  result <- format_semantic_views_section(views)

  expect_match(result, "## Snowflake Semantic Views")
  expect_match(result, "db.schema.view")
  expect_match(result, "CREATE SEMANTIC VIEW test_view")
  expect_match(result, "```sql")
})
it("formats multiple views", {
  views <- list(
    list(name = "db.schema.view1", ddl = "CREATE SEMANTIC VIEW v1"),
    list(name = "db.schema.view2", ddl = "CREATE SEMANTIC VIEW v2")
  )
  result <- format_semantic_views_section(views)

  expect_match(result, "db.schema.view1")
  expect_match(result, "db.schema.view2")
  expect_match(result, "CREATE SEMANTIC VIEW v1")
  expect_match(result, "CREATE SEMANTIC VIEW v2")
})
