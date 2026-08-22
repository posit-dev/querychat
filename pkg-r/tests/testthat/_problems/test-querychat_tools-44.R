# Extracted from test-querychat_tools.R:44

# test -------------------------------------------------------------------------
it("uses the tool default when options are unset", {
    withr::local_options(querychat.tool_details = NULL)
    withr::local_envvar(QUERYCHAT_TOOL_DETAILS = NA)

    expect_true(querychat_tool_starts_open("query"))
    expect_true(querychat_tool_starts_open("update"))
    expect_false(querychat_tool_starts_open("reset"))
  })
it("uses the tool default when envvar is 'default'", {
    withr::local_options(querychat.tool_details = NULL)
    withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "default")

    expect_true(querychat_tool_starts_open("query"))
    expect_true(querychat_tool_starts_open("update"))
    expect_false(querychat_tool_starts_open("reset"))
  })
it("uses the tool default when option is 'default'", {
    withr::local_options(querychat.tool_details = "default")

    expect_true(querychat_tool_starts_open("query"))
    expect_true(querychat_tool_starts_open("update"))
    expect_false(querychat_tool_starts_open("reset"))
  })
