describe("tool_visualize_dashboard()", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("ggsql")

  it("creates a tool with correct name", {
    ds <- local_data_frame_source(new_test_df())
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )
    tool <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {
      }
    )
    expect_equal(tool@name, "querychat_visualize")
  })

  it("renders query fallback guidance only when query tool is enabled", {
    ds <- local_data_frame_source(new_test_df())
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )

    with_query <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {
      },
      has_tool_query = TRUE
    )
    without_query <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {
      },
      has_tool_query = FALSE
    )

    expect_match(with_query@description, "use `querychat_query` instead", fixed = TRUE)
    expect_no_match(without_query@description, "use `querychat_query` instead", fixed = TRUE)
    expect_no_match(without_query@description, "fall back to `querychat_query`", fixed = TRUE)
  })

  it("errors when session is NULL", {
    ds <- local_data_frame_source(new_test_df())
    expect_error(
      tool_visualize_dashboard(
        ds,
        session = NULL,
        update_fn = function(data) {
        }
      ),
      "active Shiny",
      fixed = TRUE
    )
  })

  it("calls update_fn on success", {
    ds <- local_data_frame_source(new_test_df())
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )
    callback_data <- NULL
    local_mocked_bindings(
      build_viz_footer = function(...) {
        htmltools::tagList()
      },
      .package = "querychat"
    )
    tool <- tool_visualize_dashboard(
      ds,
      session = session,
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

  it("raises an error for query without VISUALISE", {
    ds <- local_data_frame_source(new_test_df())
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )
    tool <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {
      }
    )
    expect_error(
      tool(
        ggsql = "SELECT * FROM test_table",
        title = "No viz"
      ),
      "Query must include a VISUALISE clause"
    )
  })

  it("raises an error for bad query", {
    ds <- local_data_frame_source(new_test_df())
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )
    tool <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {
      }
    )
    expect_error(
      tool(
        ggsql = "SELECT * FROM nonexistent_table VISUALISE x AS x DRAW point",
        title = "Bad"
      ),
      "Catalog Error"
    )
  })

  it("lets visualize_result() errors bubble up unchanged", {
    ds <- local_data_frame_source(new_test_df())
    long_msg <- paste(rep("word", 200), collapse = " ")
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )

    local_mocked_bindings(
      visualize_result = function(...) {
        rlang::abort(long_msg)
      },
      .package = "querychat"
    )

    impl <- tool_visualize_impl(
      ds,
      session = session,
      update_fn = function(data) {
      }
    )
    expect_error(
      impl(
        ggsql = "SELECT * FROM test_table VISUALISE value AS x DRAW histogram",
        title = "Bad"
      ),
      long_msg,
      fixed = TRUE
    )
  })
})
