describe("querychat_tool_starts_open()", {
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

  it("always expands when option is 'expanded'", {
    withr::local_options(querychat.tool_details = "expanded")

    expect_true(querychat_tool_starts_open("query"))
    expect_true(querychat_tool_starts_open("update"))
    expect_true(querychat_tool_starts_open("reset"))
  })

  it("always collapses when option is 'collapsed'", {
    withr::local_options(querychat.tool_details = "collapsed")

    expect_false(querychat_tool_starts_open("query"))
    expect_false(querychat_tool_starts_open("update"))
    expect_false(querychat_tool_starts_open("reset"))
  })
})

describe("querychat_tool_details_option()", {
  it("is case-insensitive", {
    withr::local_options(querychat.tool_details = "EXPANDED")
    expect_equal(querychat_tool_details_option(), "expanded")

    withr::local_options(querychat.tool_details = "Collapsed")
    expect_equal(querychat_tool_details_option(), "collapsed")
  })

  it("warns on invalid setting", {
    withr::local_options(querychat.tool_details = "invalid")

    expect_warning(
      querychat_tool_details_option(),
      "Invalid value for"
    )
  })

  it("gives option precedence over envvar", {
    withr::local_options(querychat.tool_details = "collapsed")
    withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "expanded")

    expect_equal(querychat_tool_details_option(), "collapsed")
  })
})
