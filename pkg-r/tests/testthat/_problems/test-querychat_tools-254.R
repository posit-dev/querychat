# Extracted from test-querychat_tools.R:254

# test -------------------------------------------------------------------------
skip_if_no_dataframe_engine()
it("returns successful result for valid query action", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM test_table WHERE id = 1",
    action = "query"
  )

  expect_s7_class(result, ellmer::ContentToolResult)
  expect_null(result@error)
  expect_s3_class(result@value, "data.frame")
  expect_equal(nrow(result@value), 1)
})
it("returns successful result for valid update action", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM test_table WHERE value > 20",
    title = "High values",
    action = "update"
  )

  expect_s7_class(result, ellmer::ContentToolResult)
  expect_null(result@error)
  expect_equal(
    result@value,
    "Dashboard updated. Use `querychat_query` tool to review results, if needed."
  )
})
it("returns successful result for reset action", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = NULL,
    action = "reset"
  )

  expect_s7_class(result, ellmer::ContentToolResult)
  expect_null(result@error)
  expect_equal(result@value, "The dashboard has been reset to show all data.")
})
it("handles query errors appropriately", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM nonexistent_table",
    action = "query"
  )

  expect_s7_class(result, ellmer::ContentToolResult)
  expect_s3_class(result@error, "error")
  expect_null(result@value)
})
it("handles update errors appropriately", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "INVALID SQL",
    action = "update"
  )

  expect_s7_class(result, ellmer::ContentToolResult)
  expect_s3_class(result@error, "error")
  expect_null(result@value)
})
it("formats query results with details block", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM test_table LIMIT 1",
    action = "query"
  )

  markdown <- result@extra$display$markdown
  expect_match(markdown, "```sql")
  expect_match(markdown, "SELECT \\* FROM test_table LIMIT 1")
  expect_match(markdown, "<details")
  expect_match(markdown, "</details>")
})
it("formats update results with button HTML", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM test_table",
    title = "Test Filter",
    action = "update"
  )

  markdown <- result@extra$display$markdown
  expect_match(markdown, "```sql")
  expect_match(markdown, "SELECT \\* FROM test_table")
  expect_match(markdown, "button")
  expect_match(markdown, "Apply Filter")
  expect_match(markdown, "data-query")
  expect_match(markdown, "data-title")
})
it("formats reset results with button HTML", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = NULL,
    action = "reset"
  )

  markdown <- result@extra$display$markdown
  expect_match(markdown, "button")
  expect_match(markdown, "Reset Filter")
})
it("includes title in extra display metadata for update action", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM test_table",
    title = "Custom Title",
    action = "update"
  )

  expect_equal(result@extra$display$title, "Custom Title")
})
it("does not include title for query action", {
  df_source <- local_data_frame_source(new_test_df())

  result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM test_table",
    title = "Should be ignored",
    action = "query"
  )

  expect_null(result@extra$display$title)
})
it("sets open state based on action and tool details option", {
  df_source <- local_data_frame_source(new_test_df())
  withr::local_options(querychat.tool_details = NULL)

  query_result <- querychat_tool_result(
    df_source,
    query = "SELECT * FROM test_table",
    action = "query"
  )
  expect_true(query_result@extra$display$open)

  reset_result <- querychat_tool_result(
    df_source,
    query = NULL,
    action = "reset"
  )
  expect_false(reset_result@extra$display$open)
})
