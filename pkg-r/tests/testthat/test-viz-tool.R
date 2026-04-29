describe("tool_visualize_dashboard()", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("ggsql")

  it("creates a tool with correct name", {
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {}
    )
    expect_equal(tool@name, "querychat_visualize")
  })

  it("renders query fallback guidance only when query tool is enabled", {
    ds <- local_data_frame_source(new_test_df())

    with_query <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {
      },
      has_tool_query = TRUE
    )
    without_query <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {
      },
      has_tool_query = FALSE
    )

    expect_match(with_query@description, "use `querychat_query` instead", fixed = TRUE)
    expect_no_match(without_query@description, "use `querychat_query` instead", fixed = TRUE)
    expect_no_match(without_query@description, "fall back to `querychat_query`", fixed = TRUE)
  })

  it("executes and returns a ContentToolResult (no display without session)", {
    ds <- local_data_frame_source(new_test_df())
    callback_data <- NULL
    tool <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {
        callback_data <<- data
      }
    )
    result <- tool(
      ggsql = "SELECT * FROM test_table VISUALISE value AS x DRAW histogram",
      title = "Test Chart"
    )
    expect_s7_class(result, ellmer::ContentToolResult)
    # Without a Shiny session, no display is produced
    expect_null(result@extra$display)
  })

  it("calls update_fn on success", {
    ds <- local_data_frame_source(new_test_df())
    callback_data <- NULL
    tool <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {
        callback_data <<- data
      }
    )
    tool(
      ggsql = "SELECT * FROM test_table VISUALISE value AS x DRAW histogram",
      title = "Test"
    )
    expect_type(callback_data, "list")
    expect_true(all(c("ggsql", "title", "widget_id") %in% names(callback_data)))
  })

  it("returns error result for query without VISUALISE", {
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {}
    )
    result <- tool(
      ggsql = "SELECT * FROM test_table",
      title = "No viz"
    )
    expect_s7_class(result, ellmer::ContentToolResult)
    expect_true(!is.null(result@error))
  })

  it("returns error result with truncated message for bad query", {
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {}
    )
    result <- tool(
      ggsql = "SELECT * FROM nonexistent_table VISUALISE x AS x DRAW point",
      title = "Bad"
    )
    expect_s7_class(result, ellmer::ContentToolResult)
    expect_true(!is.null(result@error))
  })
})
