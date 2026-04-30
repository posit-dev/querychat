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
      update_fn = function(data) {}
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
      update_fn = function(data) {},
      has_tool_query = TRUE
    )
    without_query <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {},
      has_tool_query = FALSE
    )

    expect_match(
      with_query@description,
      "use `querychat_query` instead",
      fixed = TRUE
    )
    expect_no_match(
      without_query@description,
      "use `querychat_query` instead",
      fixed = TRUE
    )
    expect_no_match(
      without_query@description,
      "fall back to `querychat_query`",
      fixed = TRUE
    )
  })

  it("describes current ggsql 0.3 visualization rules", {
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
      update_fn = function(data) {}
    )

    expect_match(
      tool@description,
      "All data transformations must happen in the `SELECT` clause.",
      fixed = TRUE
    )
    expect_match(tool@description, "DRAW range", fixed = TRUE)
    expect_no_match(
      tool@description,
      "using single quotes for strings",
      fixed = TRUE
    )
  })

  it("prints the spec and returns a simple result when session is NULL", {
    ds <- local_data_frame_source(new_test_df())

    tool <- tool_visualize_dashboard(
      ds,
      session = NULL,
      update_fn = function(data) {}
    )

    result <- tool(
      ggsql = "SELECT * FROM test_table VISUALISE value AS x DRAW histogram",
      title = "Test"
    )

    expect_match(
      result@value,
      "Chart displayed with title 'Test'.",
      fixed = TRUE
    )
    expect_equal(result@extra, list())
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
      update_fn = function(data) {}
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
      update_fn = function(data) {}
    )
    expect_error(
      tool(
        ggsql = paste(
          "SELECT value AS x, 1 AS y FROM nonexistent_table",
          "VISUALISE x AS x, y AS y DRAW point"
        ),
        title = "Bad"
      ),
      "Catalog Error"
    )
  })

  it("uses ggsql validation errors and does not execute invalid queries", {
    ds <- local_data_frame_source(new_test_df())
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )
    validated <- structure(
      list(
        valid = FALSE,
        errors = data.frame(
          message = c("first ggsql error", "second ggsql error")
        )
      ),
      class = "ggsql_validated"
    )
    executed <- FALSE

    local_mocked_bindings(
      ggsql_validate = function(...) validated,
      ggsql_has_visual = function(...) TRUE,
      .package = "ggsql"
    )
    local_mocked_bindings(
      execute_ggsql = function(...) {
        executed <<- TRUE
        rlang::abort("execute_ggsql should not be called")
      },
      .package = "querychat"
    )

    tool <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {}
    )

    expect_error(
      tool(
        ggsql = "SELECT * FROM test_table VISUALISE value AS x DRAW point",
        title = "Bad Viz"
      ),
      "first ggsql error\nsecond ggsql error",
      fixed = TRUE
    )
    expect_false(executed)
  })

  it("does not fall back to stale QueryChat VISUALISE guidance for invalid ggsql", {
    ds <- local_data_frame_source(new_test_df())
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )
    validated <- structure(
      list(
        valid = FALSE,
        errors = data.frame(message = "upstream validation failed")
      ),
      class = "ggsql_validated"
    )

    local_mocked_bindings(
      ggsql_validate = function(...) validated,
      ggsql_has_visual = function(...) TRUE,
      .package = "ggsql"
    )

    tool <- tool_visualize_dashboard(
      ds,
      session = session,
      update_fn = function(data) {}
    )

    err <- tryCatch(
      {
        tool(
          ggsql = "SELECT * FROM test_table VISUALISE value AS x DRAW point",
          title = "Bad Viz"
        )
        NULL
      },
      error = identity
    )

    expect_s3_class(err, "error")
    expect_match(
      conditionMessage(err),
      "upstream validation failed",
      fixed = TRUE
    )
    expect_no_match(
      conditionMessage(err),
      "VISUALISE clause was not recognized",
      fixed = TRUE
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
      update_fn = function(data) {}
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

describe("collapse_validation_errors()", {
  it("joins multiple upstream validation messages", {
    validated <- structure(
      list(
        errors = data.frame(
          message = c("first ggsql error", "second ggsql error")
        )
      ),
      class = "ggsql_validated"
    )

    expect_equal(
      collapse_validation_errors(validated),
      "first ggsql error\nsecond ggsql error"
    )
  })

  it("falls back when no validation messages are available", {
    validated <- structure(
      list(
        errors = data.frame(message = character())
      ),
      class = "ggsql_validated"
    )

    expect_equal(
      collapse_validation_errors(validated),
      "Invalid ggsql query."
    )
  })
})

describe("resolve_viz_dom_id()", {
  it("uses the session namespace when available", {
    session <- structure(
      list(ns = function(id) paste0("repro-", id)),
      class = "MockShinySession"
    )

    expect_equal(resolve_viz_dom_id(session, "viz"), "repro-viz")
  })

  it("falls back to the raw widget id without a session", {
    expect_equal(resolve_viz_dom_id(NULL, "viz"), "viz")
  })
})
