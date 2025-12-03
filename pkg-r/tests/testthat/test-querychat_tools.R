test_that("resolve_tool_open_state respects default behavior", {
  withr::local_options(querychat.tool_details = NULL)
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = NA)

  expect_true(resolve_tool_open_state("query", FALSE))
  expect_true(resolve_tool_open_state("update", FALSE))
  expect_false(resolve_tool_open_state("reset", FALSE))
  expect_false(resolve_tool_open_state("query", TRUE))
})

test_that("resolve_tool_open_state respects 'expanded' setting via option", {
  withr::local_options(querychat.tool_details = "expanded")

  expect_true(resolve_tool_open_state("query", FALSE))
  expect_true(resolve_tool_open_state("update", FALSE))
  expect_true(resolve_tool_open_state("reset", FALSE))
  expect_false(resolve_tool_open_state("query", TRUE))
})

test_that("resolve_tool_open_state respects 'collapsed' setting via option", {
  withr::local_options(querychat.tool_details = "collapsed")

  expect_false(resolve_tool_open_state("query", FALSE))
  expect_false(resolve_tool_open_state("update", FALSE))
  expect_false(resolve_tool_open_state("reset", FALSE))
  expect_false(resolve_tool_open_state("query", TRUE))
})

test_that("resolve_tool_open_state respects 'default' setting via option", {
  withr::local_options(querychat.tool_details = "default")

  expect_true(resolve_tool_open_state("query", FALSE))
  expect_true(resolve_tool_open_state("update", FALSE))
  expect_false(resolve_tool_open_state("reset", FALSE))
  expect_false(resolve_tool_open_state("query", TRUE))
})

test_that("resolve_tool_open_state respects 'expanded' setting via envvar", {
  withr::local_options(querychat.tool_details = NULL)
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "expanded")

  expect_true(resolve_tool_open_state("query", FALSE))
  expect_true(resolve_tool_open_state("update", FALSE))
  expect_true(resolve_tool_open_state("reset", FALSE))
})

test_that("resolve_tool_open_state respects 'collapsed' setting via envvar", {
  withr::local_options(querychat.tool_details = NULL)
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "collapsed")

  expect_false(resolve_tool_open_state("query", FALSE))
  expect_false(resolve_tool_open_state("update", FALSE))
  expect_false(resolve_tool_open_state("reset", FALSE))
})

test_that("resolve_tool_open_state is case-insensitive", {
  withr::local_options(querychat.tool_details = "EXPANDED")
  expect_true(resolve_tool_open_state("query", FALSE))

  withr::local_options(querychat.tool_details = "Collapsed")
  expect_false(resolve_tool_open_state("query", FALSE))
})

test_that("resolve_tool_open_state warns on invalid setting", {
  withr::local_options(querychat.tool_details = "invalid")

  expect_warning(
    resolve_tool_open_state("query", FALSE),
    "Invalid value for"
  )
})

test_that("option takes precedence over environment variable", {
  withr::local_options(querychat.tool_details = "collapsed")
  withr::local_envvar(QUERYCHAT_TOOL_DETAILS = "expanded")

  expect_false(resolve_tool_open_state("query", FALSE))
})
