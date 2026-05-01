describe("query tool collapsed parameter", {
  skip_if_no_dataframe_engine()

  it("collapsed=TRUE sets open=FALSE in display", {
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_query(ds)
    result <- tool(
      query = "SELECT * FROM test_table",
      `_intent` = "",
      collapsed = TRUE
    )
    expect_false(result@extra$display$open)
  })

  it("collapsed=FALSE sets open=TRUE in display", {
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_query(ds)
    result <- tool(
      query = "SELECT * FROM test_table",
      `_intent` = "",
      collapsed = FALSE
    )
    expect_true(result@extra$display$open)
  })

  it("collapsed defaults to FALSE (open=TRUE for query)", {
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_query(ds)
    result <- tool(query = "SELECT * FROM test_table", `_intent` = "")
    expect_true(result@extra$display$open)
  })

  it("collapsed=TRUE overrides QUERYCHAT_TOOL_DETAILS=expanded", {
    withr::local_options(querychat.tool_details = "expanded")
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_query(ds)
    result <- tool(
      query = "SELECT * FROM test_table",
      `_intent` = "",
      collapsed = TRUE
    )
    expect_false(result@extra$display$open)
  })

  it("collapsed=FALSE overrides QUERYCHAT_TOOL_DETAILS=collapsed", {
    withr::local_options(querychat.tool_details = "collapsed")
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_query(ds)
    result <- tool(
      query = "SELECT * FROM test_table",
      `_intent` = "",
      collapsed = FALSE
    )
    expect_true(result@extra$display$open)
  })
})
