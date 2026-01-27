# Extracted from test-SnowflakeSource.R:8

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
