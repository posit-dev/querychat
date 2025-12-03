test_that("querychat_tool_starts_open respects default behavior", {
  withr::local_options(querychat.tool_details = NULL)
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = NA)

  expect_true(querychat_tool_starts_open("query"))
  expect_true(querychat_tool_starts_open("update"))
  expect_false(querychat_tool_starts_open("reset"))
})

test_that("querychat_tool_starts_open respects 'expanded' setting via option", {
  withr::local_options(querychat.tool_details = "expanded")

  expect_true(querychat_tool_starts_open("query"))
  expect_true(querychat_tool_starts_open("update"))
  expect_true(querychat_tool_starts_open("reset"))
})

test_that("querychat_tool_starts_open respects 'collapsed' setting via option", {
  withr::local_options(querychat.tool_details = "collapsed")

  expect_false(querychat_tool_starts_open("query"))
  expect_false(querychat_tool_starts_open("update"))
  expect_false(querychat_tool_starts_open("reset"))
})

test_that("querychat_tool_starts_open respects 'default' setting via option", {
  withr::local_options(querychat.tool_details = "default")

  expect_true(querychat_tool_starts_open("query"))
  expect_true(querychat_tool_starts_open("update"))
  expect_false(querychat_tool_starts_open("reset"))
})

test_that("querychat_tool_starts_open respects 'expanded' setting via envvar", {
  withr::local_options(querychat.tool_details = NULL)
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "expanded")

  expect_true(querychat_tool_starts_open("query"))
  expect_true(querychat_tool_starts_open("update"))
  expect_true(querychat_tool_starts_open("reset"))
})

test_that("querychat_tool_starts_open respects 'collapsed' setting via envvar", {
  withr::local_options(querychat.tool_details = NULL)
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "collapsed")

  expect_false(querychat_tool_starts_open("query"))
  expect_false(querychat_tool_starts_open("update"))
  expect_false(querychat_tool_starts_open("reset"))
})

test_that("querychat_tool_starts_open is case-insensitive", {
  withr::local_options(querychat.tool_details = "EXPANDED")
  expect_true(querychat_tool_starts_open("query"))

  withr::local_options(querychat.tool_details = "Collapsed")
  expect_false(querychat_tool_starts_open("query"))
})

test_that("querychat_tool_starts_open warns on invalid setting", {
  withr::local_options(querychat.tool_details = "invalid")

  expect_warning(
    querychat_tool_starts_open("query"),
    "Invalid value for"
  )
})

test_that("option takes precedence over environment variable", {
  withr::local_options(querychat.tool_details = "collapsed")
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "expanded")

  expect_false(querychat_tool_starts_open("query"))
})
