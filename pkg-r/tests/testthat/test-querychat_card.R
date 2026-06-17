test_that("tool_card() checks inputs", {
  skip_if_no_dataframe_engine()

  expect_snapshot(error = TRUE, tool_card("invalid_source"))

  df_source <- local_data_frame_source(new_test_df())
  expect_snapshot(error = TRUE, tool_card(df_source, manage_card = NULL))
})

describe("tool_card()", {
  skip_if_no_dataframe_engine()

  it("creates a tool with the correct name", {
    ds <- local_data_frame_source(new_test_df())
    tool <- tool_card(ds, function(...) {})
    expect_equal(tool@name, "querychat_card")
  })
})

describe("tool_card_impl()", {
  skip_if_no_dataframe_engine()

  new_mock <- function() {
    record <- new.env(parent = emptyenv())
    record$calls <- list()
    mock_manage <- function(action, id = NULL, card = NULL) {
      record$calls[[length(record$calls) + 1L]] <- list(
        action = action,
        id = id,
        card = card
      )
      "1 card: [abcd] Test (table)"
    }
    list(record = record, mock_manage = mock_manage)
  }

  it("adds a table card and calls manage_card", {
    ds <- local_data_frame_source(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    res <- impl(
      action = "add",
      type = "card",
      display = "table",
      title = "T",
      value = "SELECT * FROM test_table"
    )

    expect_s7_class(res, ellmer::ContentToolResult)
    expect_length(mock$record$calls, 1)
    call <- mock$record$calls[[1]]
    expect_equal(call$action, "add")
    expect_false(is.null(call$id))
    expect_equal(call$card$type, "card")
    expect_equal(call$card$display, "table")
    expect_equal(call$card$id, call$id)
  })

  it("adds a markdown card without query execution", {
    ds <- local_data_frame_source(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    res <- impl(
      action = "add",
      type = "card",
      display = "markdown",
      title = "M",
      value = "Some **markdown**"
    )

    expect_s7_class(res, ellmer::ContentToolResult)
    expect_length(mock$record$calls, 1)
    call <- mock$record$calls[[1]]
    expect_equal(call$card$display, "markdown")
  })

  it("adds a value_box card for a 1x1 query", {
    ds <- local_data_frame_source(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    res <- impl(
      action = "add",
      type = "value_box",
      title = "V",
      value = "SELECT COUNT(*) AS n FROM test_table"
    )

    expect_s7_class(res, ellmer::ContentToolResult)
    expect_length(mock$record$calls, 1)
    call <- mock$record$calls[[1]]
    expect_equal(call$card$type, "value_box")
  })

  it("errors for value_box query returning more than 1 row x 1 column", {
    ds <- local_data_frame_source(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        type = "value_box",
        title = "V",
        value = "SELECT * FROM test_table"
      ),
      "1 row"
    )
    expect_length(mock$record$calls, 0)
  })

  it("errors for replace action when id is missing", {
    ds <- local_data_frame_source(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "replace",
        type = "card",
        display = "table",
        title = "T",
        value = "SELECT * FROM test_table"
      ),
      "'id' is required for action 'replace'"
    )
  })

  it("patches an existing card by overlaying supplied fields", {
    ds <- local_data_frame_source(new_test_df())
    existing <- list(
      id = "abcd",
      type = "card",
      display = "table",
      title = "Old title",
      value = "SELECT * FROM test_table",
      footer = "Old footer"
    )
    record <- new.env(parent = emptyenv())
    record$calls <- list()
    mock_manage <- function(action, id = NULL, card = NULL) {
      if (action == "get") {
        return(existing)
      }
      record$calls[[length(record$calls) + 1L]] <- list(
        action = action,
        id = id,
        card = card
      )
      "1 card: [abcd] New title (table)"
    }
    impl <- tool_card_impl(ds, mock_manage)

    res <- impl(action = "patch", id = "abcd", title = "New title")

    expect_s7_class(res, ellmer::ContentToolResult)
    expect_length(record$calls, 1)
    call <- record$calls[[1]]
    expect_equal(call$action, "replace")
    expect_equal(call$id, "abcd")
    expect_equal(call$card$title, "New title")
    expect_equal(call$card$value, existing$value)
    expect_equal(call$card$footer, existing$footer)
    expect_equal(jsonlite::fromJSON(res@value)$status, "patched")
  })

  it("errors for patch action when the card does not exist", {
    ds <- local_data_frame_source(new_test_df())
    mock_manage <- function(action, id = NULL, card = NULL) {
      if (action == "get") {
        return(NULL)
      }
      "no cards"
    }
    impl <- tool_card_impl(ds, mock_manage)

    expect_error(
      impl(action = "patch", id = "zzzz", title = "New title"),
      "No card found with id 'zzzz'"
    )
  })

  it("removes a card by id without validation", {
    ds <- local_data_frame_source(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    res <- impl(action = "remove", id = "abcd")

    expect_s7_class(res, ellmer::ContentToolResult)
    expect_length(mock$record$calls, 1)
    call <- mock$record$calls[[1]]
    expect_equal(call$action, "remove")
    expect_equal(call$id, "abcd")
  })

  it("errors when value is missing on add", {
    ds <- local_data_frame_source(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        type = "card",
        display = "table",
        title = "T"
      ),
      "'value' is required"
    )
  })
})

describe("card_tool_result()", {
  it("returns a ContentToolResult with JSON value", {
    res <- card_tool_result("abc123", "added", "1 card: [abc123] Test (table)")

    expect_s7_class(res, ellmer::ContentToolResult)
    parsed <- jsonlite::fromJSON(res@value)
    expect_equal(parsed$id, "abc123")
    expect_equal(parsed$status, "added")
    expect_equal(parsed$cards_summary, "1 card: [abc123] Test (table)")
  })
})
