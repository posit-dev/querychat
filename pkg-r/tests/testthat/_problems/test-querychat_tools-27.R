# Extracted from test-querychat_tools.R:27

# test -------------------------------------------------------------------------
it("uses the tool default when options are unset", {
    withr::local_options(querychat.tool_details = NULL)
    withr::local_envvar(QUERYCHAT_TOOL_DETAILS = NA)

    expect_true(querychat_tool_starts_open("query"))
    expect_true(querychat_tool_starts_open("update"))
    expect_false(querychat_tool_starts_open("reset"))
  })
