test_that("tool_update_dashboard() checks inputs", {
  expect_snapshot(error = TRUE, tool_update_dashboard("foo"))

  df_source <- local_data_frame_source(new_test_df())
  expect_snapshot(error = TRUE, {
    tool_update_dashboard(df_source, udpate_fn = NULL)
    tool_update_dashboard(df_source, update_fn = function(query) {})
    tool_update_dashboard(df_source, update_fn = function(title, extra) {})
  })
})

test_that("tool_reset_dashboard() checks inputs", {
  expect_snapshot(error = TRUE, tool_reset_dashboard("not_a_function"))
})

test_that("tool_query() checks inputs", {
  expect_snapshot(error = TRUE, tool_query("invalid_source"))
})

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

describe("querychat_tool_result()", {
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

  it("shows request on error", {
    df_source <- local_data_frame_source(new_test_df())

    result <- querychat_tool_result(
      df_source,
      query = "INVALID SQL",
      action = "query"
    )

    expect_true(result@extra$display$show_request)
  })

  it("hides request on success", {
    df_source <- local_data_frame_source(new_test_df())

    result <- querychat_tool_result(
      df_source,
      query = "SELECT * FROM test_table",
      action = "query"
    )

    expect_false(result@extra$display$show_request)
  })
})

describe("tool_query()", {
  it("returns an ellmer tool object", {
    df_source <- local_data_frame_source(new_test_df())
    tool <- tool_query(df_source)

    expect_s3_class(tool, "ellmer::ToolDef")
    expect_equal(tool@name, "querychat_query")
  })

  it("includes database type in description", {
    df_source <- local_data_frame_source(new_test_df())
    tool <- tool_query(df_source)

    # DataFrameSource uses DuckDB
    expect_match(tool@description, "DuckDB|duckdb", ignore.case = TRUE)
  })

  it("creates a working tool function", {
    df_source <- local_data_frame_source(new_test_df())
    tool <- tool_query(df_source)

    # Execute the tool function
    result <- tool(query = "SELECT * FROM test_table LIMIT 1")

    expect_s7_class(result, ellmer::ContentToolResult)
    expect_null(result@error)
  })
})

describe("tool_update_dashboard()", {
  it("returns an ellmer tool object", {
    df_source <- local_data_frame_source(new_test_df())

    tool <- tool_update_dashboard(df_source)

    expect_s3_class(tool, "ellmer::ToolDef")
    expect_equal(tool@name, "querychat_update_dashboard")
  })

  it("includes database type in description", {
    df_source <- local_data_frame_source(new_test_df())

    tool <- tool_update_dashboard(df_source)

    # DataFrameSource uses DuckDB
    expect_match(tool@description, "DuckDB|duckdb", ignore.case = TRUE)
  })

  it("creates a working tool function", {
    df_source <- local_data_frame_source(new_test_df())

    res_update <- NULL
    tool <- tool_update_dashboard(df_source, function(query, title) {
      res_update <<- list(query = query, title = title)
    })

    res_tool <- tool(
      query = "SELECT * FROM test_table WHERE id > 2",
      title = "Filtered View"
    )

    expect_s7_class(res_tool, ellmer::ContentToolResult)
    expect_equal(res_update$query, "SELECT * FROM test_table WHERE id > 2")
    expect_equal(res_update$title, "Filtered View")
  })
})

describe("tool_reset_dashboard()", {
  reset_fn <- function() {
    "Reset executed"
  }

  it("returns an ellmer tool object", {
    tool <- tool_reset_dashboard(reset_fn)

    expect_s3_class(tool, "ellmer::ToolDef")
    expect_equal(tool@name, "querychat_reset_dashboard")
  })

  it("uses the provided reset function", {
    tool <- tool_reset_dashboard(reset_fn)

    expect_s3_class(tool, "ellmer::ToolDef")
    expect_equal(tool(), "Reset executed")
  })
})

describe("tool_update_dashboard_impl()", {
  it("returns a function", {
    df_source <- local_data_frame_source(new_test_df())
    current_query <- shiny::reactiveVal("SELECT * FROM test_table")
    current_title <- shiny::reactiveVal("All Data")

    impl_fn <- tool_update_dashboard_impl(df_source)

    expect_type(impl_fn, "closure")
  })

  it("updates reactive values on successful query", {
    df_source <- local_data_frame_source(new_test_df())

    res_update <- NULL
    impl_fn <- tool_update_dashboard_impl(df_source, function(query, title) {
      res_update <<- list(query = query, title = title)
    })

    res_tool <- impl_fn(
      query = "SELECT * FROM test_table WHERE id < 3",
      title = "First Two"
    )

    expect_equal(res_update$query, "SELECT * FROM test_table WHERE id < 3")
    expect_equal(res_update$title, "First Two")
    expect_null(res_tool@error)
  })

  it("does not update reactive values on query error", {
    df_source <- local_data_frame_source(new_test_df())

    res_update <- NULL
    impl_fn <- tool_update_dashboard_impl(df_source, function(query, title) {
      res_update <<- list(query = query, title = title)
    })

    res_tool <- impl_fn(
      query = "INVALID SQL",
      title = "Should Not Update"
    )

    # `update_fn` was not called
    expect_null(res_update)
    # because the tool resulted in an error
    expect_s3_class(res_tool@error, class = "error")
  })
})
