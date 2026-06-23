test_that("tool_card() checks inputs", {
  skip_if_no_dataframe_engine()

  expect_snapshot(error = TRUE, tool_card("invalid_source"))

  executor <- local_query_executor(new_test_df())
  expect_snapshot(error = TRUE, tool_card(executor, manage_card = NULL))
})

describe("tool_card()", {
  skip_if_no_dataframe_engine()

  it("creates a tool with the correct name", {
    ds <- local_query_executor(new_test_df())
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
      if (action == "get") {
        return(list())
      }
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
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    res <- impl(
      action = "add",
      display = "table",
      title = "T",
      value = "SELECT * FROM test_table"
    )

    expect_s7_class(res, ellmer::ContentToolResult)
    expect_length(mock$record$calls, 1)
    call <- mock$record$calls[[1]]
    expect_equal(call$action, "add")
    expect_false(is.null(call$id))
    expect_match(call$id, "^[0-9a-f]{4}$")
    expect_equal(call$card$display, "table")
    expect_equal(call$card$id, call$id)
  })

  it("adds a markdown card without query execution", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    res <- impl(
      action = "add",
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
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    res <- impl(
      action = "add",
      display = "value_box",
      title = "V",
      value = "SELECT COUNT(*) AS n FROM test_table"
    )

    expect_s7_class(res, ellmer::ContentToolResult)
    expect_length(mock$record$calls, 1)
    call <- mock$record$calls[[1]]
    expect_equal(call$card$display, "value_box")
  })

  it("errors for value_box query returning more than 1 row x 1 column", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        display = "value_box",
        title = "V",
        value = "SELECT * FROM test_table"
      ),
      "1 row"
    )
    expect_length(mock$record$calls, 0)
  })

  it("errors for replace action when id is missing", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "replace",
        display = "table",
        title = "T",
        value = "SELECT * FROM test_table"
      ),
      "'id' is required for action 'replace'"
    )
  })

  it("patches an existing card by overlaying supplied fields", {
    ds <- local_query_executor(new_test_df())
    existing <- list(
      id = "abcd",
      display = "table",
      title = "Old title",
      value = "SELECT * FROM test_table",
      caption = "Old caption"
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
    expect_equal(call$card$caption, existing$caption)
    expect_equal(jsonlite::fromJSON(res@value)$status, "patched")
  })

  it("errors for patch action when the card does not exist", {
    ds <- local_query_executor(new_test_df())
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
    ds <- local_query_executor(new_test_df())
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
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        display = "table",
        title = "T"
      ),
      "'value' is required"
    )
  })

  it("errors when display is missing on add", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        title = "T",
        value = "SELECT * FROM test_table"
      ),
      "'display' is required"
    )
  })

  it("validates icon for table display", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        display = "table",
        title = "T",
        value = "SELECT * FROM test_table",
        icon = "not-a-real-icon-xyz-99999"
      )
    )
    expect_length(mock$record$calls, 0)
  })

  it("validates icon for markdown display", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        display = "markdown",
        title = "M",
        value = "Some text",
        icon = "not-a-real-icon-xyz-99999"
      )
    )
    expect_length(mock$record$calls, 0)
  })

  it("validates icon for value_box display", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    expect_error(
      impl(
        action = "add",
        display = "value_box",
        title = "V",
        value = "SELECT COUNT(*) AS n FROM test_table",
        icon = "not-a-real-icon-xyz-99999"
      )
    )
    expect_length(mock$record$calls, 0)
  })

  it("stores caption field in the card", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    impl(
      action = "add",
      display = "table",
      title = "T",
      value = "SELECT * FROM test_table",
      caption = "Some caption text"
    )

    call <- mock$record$calls[[1]]
    expect_equal(call$card$caption, "Some caption text")
  })

  it("stores caption field for value_box", {
    ds <- local_query_executor(new_test_df())
    mock <- new_mock()
    impl <- tool_card_impl(ds, mock$mock_manage)

    impl(
      action = "add",
      display = "value_box",
      title = "V",
      value = "SELECT COUNT(*) AS n FROM test_table",
      caption = "All time"
    )

    call <- mock$record$calls[[1]]
    expect_equal(call$card$caption, "All time")
  })
})

describe("card_tool_result()", {
  it("returns a ContentToolResult with JSON value", {
    res <- card_tool_result(list(id = "abc123", status = "added"), "Add Card")

    expect_s7_class(res, ellmer::ContentToolResult)
    parsed <- jsonlite::fromJSON(res@value)
    expect_equal(parsed$id, "abc123")
    expect_equal(parsed$status, "added")
    expect_null(parsed$cards_summary)
  })
})

describe("new_card_id()", {
  it("returns a 4 hex char id", {
    id <- new_card_id(function(action, ...) list())
    expect_match(id, "^[0-9a-f]{4}$")
  })

  it("avoids colliding with existing card ids", {
    # Exhaust all but one id so the loop is forced onto the only free value.
    all_ids <- sprintf("%04x", 0:65535)
    free <- "abcd"
    taken <- setdiff(all_ids, free)
    existing <- lapply(taken, function(x) list(id = x))
    id <- new_card_id(function(action, ...) existing)
    expect_equal(id, free)
  })
})

describe("card_public()", {
  it("orders id first and drops NULL optional fields", {
    card <- list(
      display = "table",
      title = "T",
      value = "SELECT 1",
      caption = NULL,
      theme = NULL,
      icon = NULL,
      id = "abc123"
    )
    public <- card_public(card)
    expect_equal(names(public)[[1]], "id")

    parsed <- jsonlite::fromJSON(jsonlite::toJSON(public, auto_unbox = TRUE))
    expect_equal(parsed$id, "abc123")
    expect_equal(parsed$display, "table")
    expect_null(parsed$caption)
  })
})

describe("tool_card_impl() get action", {
  skip_if_no_dataframe_engine()

  it("returns all cards when id is omitted", {
    ds <- local_query_executor(new_test_df())
    all_cards <- list(
      list(id = "aaa", display = "table", title = "One", value = "SELECT 1"),
      list(id = "bbb", display = "markdown", title = "Two", value = "Note")
    )
    mock_manage <- function(action, id = NULL, card = NULL) {
      expect_equal(action, "get")
      expect_null(id)
      all_cards
    }
    impl <- tool_card_impl(ds, mock_manage)

    res <- impl(action = "get")
    parsed <- jsonlite::fromJSON(res@value, simplifyDataFrame = FALSE)
    expect_length(parsed, 2)
    expect_equal(parsed[[1]]$id, "aaa")
    expect_equal(parsed[[2]]$title, "Two")
  })

  it("returns a single card when id is supplied", {
    ds <- local_query_executor(new_test_df())
    mock_manage <- function(action, id = NULL, card = NULL) {
      expect_equal(id, "aaa")
      list(id = "aaa", display = "table", title = "One", value = "SELECT 1")
    }
    impl <- tool_card_impl(ds, mock_manage)

    res <- impl(action = "get", id = "aaa")
    parsed <- jsonlite::fromJSON(res@value)
    expect_equal(parsed$id, "aaa")
    expect_equal(parsed$display, "table")
  })

  it("errors when the requested card does not exist", {
    ds <- local_query_executor(new_test_df())
    mock_manage <- function(action, id = NULL, card = NULL) NULL
    impl <- tool_card_impl(ds, mock_manage)

    expect_error(
      impl(action = "get", id = "zzzz"),
      "No card found with id 'zzzz'"
    )
  })
})

describe("cards_to_payload() / payload_to_cards()", {
  it("round-trips a value_box card with all optional fields", {
    cards <- list(
      list(
        id = "ab12",
        display = "value_box",
        title = "Total Sales",
        value = "SELECT '$1,234' AS val",
        caption = "All time",
        theme = "success",
        icon = "currency-dollar"
      )
    )
    payload <- cards_to_payload(cards)
    expect_type(payload, "character")
    expect_length(payload, 1)
    # URL-safe: no +, /, or = characters
    expect_false(grepl("[+/=]", payload))

    result <- payload_to_cards(payload)
    expect_length(result, 1)
    card <- result[[1]]
    expect_equal(card$id, "ab12")
    expect_equal(card$display, "value_box")
    expect_equal(card$title, "Total Sales")
    expect_equal(card$value, "SELECT '$1,234' AS val")
    expect_equal(card$caption, "All time")
    expect_equal(card$theme, "success")
    expect_equal(card$icon, "currency-dollar")
  })

  it("round-trips a table card without optional fields", {
    cards <- list(
      list(
        id = "cc00",
        display = "table",
        title = "Top Products",
        value = "SELECT * FROM test_table"
      )
    )
    result <- payload_to_cards(cards_to_payload(cards))
    expect_length(result, 1)
    card <- result[[1]]
    expect_equal(card$id, "cc00")
    expect_equal(card$display, "table")
    expect_equal(card$title, "Top Products")
    expect_equal(card$value, "SELECT * FROM test_table")
    expect_null(card$caption)
    expect_null(card$theme)
    expect_null(card$icon)
  })

  it("round-trips a markdown card", {
    cards <- list(
      list(
        id = "dd01",
        display = "markdown",
        title = "Notes",
        value = "**Key insight**: sales are up."
      )
    )
    result <- payload_to_cards(cards_to_payload(cards))
    card <- result[[1]]
    expect_equal(card$display, "markdown")
    expect_equal(card$value, "**Key insight**: sales are up.")
  })

  it("round-trips a mixed list of multiple cards", {
    cards <- list(
      list(
        id = "aa01",
        display = "value_box",
        title = "Count",
        value = "SELECT COUNT(*) FROM t",
        caption = "Rows"
      ),
      list(
        id = "bb02",
        display = "table",
        title = "Detail",
        value = "SELECT * FROM t"
      ),
      list(
        id = "cc03",
        display = "markdown",
        title = "Summary",
        value = "All good."
      )
    )
    result <- payload_to_cards(cards_to_payload(cards))
    expect_length(result, 3)
    expect_equal(result[[1]]$display, "value_box")
    expect_equal(result[[1]]$caption, "Rows")
    expect_equal(result[[2]]$display, "table")
    expect_equal(result[[3]]$display, "markdown")
  })

  it("payload_to_cards() returns plain lists, not data.frames", {
    cards <- list(
      list(id = "e1", display = "table", title = "T", value = "SELECT 1"),
      list(id = "e2", display = "markdown", title = "M", value = "Text")
    )
    result <- payload_to_cards(cards_to_payload(cards))
    expect_true(is.list(result))
    expect_true(is.list(result[[1]]))
    expect_false(is.data.frame(result[[1]]))
  })
})
