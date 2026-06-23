test_that("validate_measures() passes for valid list of ToolDef", {
  td <- ellmer::tool(function() 1, "A measure.", name = "my_measure")
  expect_no_error(validate_measures(list(td)))
})

test_that("validate_measures() errors for non-ToolDef elements", {
  expect_snapshot(error = TRUE, validate_measures(list("not a tool")))
  expect_snapshot(error = TRUE, validate_measures(list(42)))
})

test_that("validate_measures() passes for empty list", {
  expect_no_error(validate_measures(list()))
})

test_that("humanize_measure_name() converts underscores to spaces and uppercases", {
  expect_equal(humanize_measure_name("revenue_by_region"), "Revenue by region")
  expect_equal(humanize_measure_name("order_count"), "Order count")
  expect_equal(humanize_measure_name("x"), "X")
})

test_that("td_name() and td_description() extract S7 props", {
  td <- ellmer::tool(function() 1, "My desc.", name = "my_measure")
  expect_equal(td_name(td), "my_measure")
  expect_equal(td_description(td), "My desc.")
})

test_that("td_title() returns annotation title when set", {
  td <- ellmer::tool(
    function() 1, "desc", name = "my_measure",
    annotations = ellmer::tool_annotations(title = "Custom Title")
  )
  expect_equal(td_title(td), "Custom Title")
})

test_that("td_title() humanizes name when no annotation title", {
  td <- ellmer::tool(function() 1, "desc", name = "my_measure")
  expect_equal(td_title(td), "My measure")
})

test_that("lexical_rank() returns indices of matching items", {
  catalog <- c("revenue by region", "order count total", "revenue trend over time")
  result <- lexical_rank("revenue", catalog, n = 5)
  expect_true(1 %in% result)
  expect_true(3 %in% result)
  expect_false(2 %in% result)
})

test_that("lexical_rank() returns empty when no overlap", {
  catalog <- c("foo bar", "baz qux")
  result <- lexical_rank("zzz", catalog, n = 5)
  expect_length(result, 0)
})

test_that("measures_search_text() returns match block for relevant query", {
  td <- ellmer::tool(
    function() 1, "Count of orders placed.", name = "order_count"
  )
  result <- measures_search_text(list(order_count = td), "how many orders")
  expect_match(result, "order_count")
  expect_match(result, "Count of orders placed.")
})

test_that("measures_search_text() returns no-match message", {
  td <- ellmer::tool(function() 1, "Revenue total.", name = "revenue")
  result <- measures_search_text(list(revenue = td), "zzzzz unrelated")
  expect_match(result, "No measure")
})

test_that("measures_search_text() returns no-measures message for empty registry", {
  result <- measures_search_text(list(), "anything")
  expect_match(result, "No measures")
})

test_that("parse_measure_args() handles NA and empty character", {
  expect_equal(parse_measure_args(NA_character_), list())
  expect_equal(parse_measure_args(character(0)), list())
})

test_that("format_measure_value() formats scalars as comma-separated string", {
  expect_equal(format_measure_value(42), "42")
  expect_equal(format_measure_value(1234567), "1,234,567")
  expect_match(format_measure_value(c("a", "b", "c")), "a, b, c")
})

test_that("format_measure_value() formats data frames as markdown", {
  df <- data.frame(x = 1:2, y = c("a", "b"), stringsAsFactors = FALSE)
  result <- format_measure_value(df)
  expect_match(result, "\\|")  # markdown table has pipes
  expect_match(result, "x")
  expect_match(result, "y")
})

test_that("tool_search_measures() returns a ToolDef named querychat_search_measures", {
  td <- ellmer::tool(function() 1, "A measure.", name = "my_measure")
  tool <- tool_search_measures(list(my_measure = td))
  expect_s3_class(tool, "ellmer::ToolDef")
  expect_equal(S7::prop(tool, "name"), "querychat_search_measures")
})

test_that("tool_search_measures() function searches and returns text", {
  td <- ellmer::tool(function() 1, "Count of orders placed.", name = "order_count")
  tool <- tool_search_measures(list(order_count = td))
  result <- tool(query = "orders")
  expect_match(result, "order_count")
})

test_that("tool_call_measure() returns a ToolDef named querychat_call_measure", {
  td <- ellmer::tool(function() 42, "Returns 42.", name = "the_answer")
  tool <- tool_call_measure(list(the_answer = td))
  expect_s3_class(tool, "ellmer::ToolDef")
  expect_equal(S7::prop(tool, "name"), "querychat_call_measure")
})

test_that("tool_call_measure() function executes measure and returns ContentToolResult", {
  td <- ellmer::tool(function() 42, "Returns 42.", name = "the_answer")
  tool <- tool_call_measure(list(the_answer = td))
  result <- tool(name = "the_answer", arguments = "{}")
  expect_s3_class(result, "ellmer::ContentToolResult")
  expect_match(S7::prop(result, "value"), "42")
})

test_that("tool_call_measure() errors informatively for unknown measure name", {
  td <- ellmer::tool(function() 1, "A measure.", name = "my_measure")
  tool <- tool_call_measure(list(my_measure = td))
  expect_snapshot(error = TRUE, tool(name = "unknown_measure", arguments = "{}"))
})

test_that("tool_call_measure() collects tbl_sql before formatting", {
  skip_if_not_installed("duckdb")
  skip_if_not_installed("dplyr")
  skip_if_not_installed("dbplyr")
  con <- DBI::dbConnect(duckdb::duckdb(), ":memory:")
  withr::defer(DBI::dbDisconnect(con, shutdown = TRUE))
  DBI::dbWriteTable(con, "t", data.frame(x = 1:2))
  td <- ellmer::tool(
    function() dplyr::tbl(con, "t"),
    "Returns a tbl_sql.",
    name = "my_tbl"
  )
  tool <- tool_call_measure(list(my_tbl = td))
  result <- tool(name = "my_tbl", arguments = "{}")
  expect_s3_class(result, "ellmer::ContentToolResult")
})

describe("new_ephemeral_db()", {
  it("registers a data frame and makes it queryable", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    withr::defer(db$cleanup())

    df <- data.frame(x = 1:3, y = c("a", "b", "c"), stringsAsFactors = FALSE)
    tbl_name <- db$register(df)
    expect_match(tbl_name, "^_run_")

    result <- db$execute(sprintf("SELECT * FROM %s", tbl_name))
    expect_equal(nrow(result), 3)
    expect_equal(names(result), c("x", "y"))
  })

  it("assigns incrementing names for multiple registrations", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    withr::defer(db$cleanup())

    name1 <- db$register(data.frame(x = 1))
    name2 <- db$register(data.frame(x = 2))
    expect_equal(name1, "_run_1")
    expect_equal(name2, "_run_2")
  })

  it("creates a named table from a SELECT query", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    withr::defer(db$cleanup())

    tbl <- db$register(data.frame(x = 1:3, stringsAsFactors = FALSE))
    db$create_table("my_output", sprintf("SELECT x * 2 AS x2 FROM %s", tbl))

    result <- db$execute("SELECT * FROM my_output")
    expect_equal(result$x2, c(2L, 4L, 6L))
  })

  it("drops tables", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    withr::defer(db$cleanup())

    tbl <- db$register(data.frame(x = 1))
    db$drop_tables(tbl)
    tables_after <- db$list_tables()
    expect_false(tbl %in% tables_after)
  })

  it("cleanup() disconnects without error", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    expect_no_error(db$cleanup())
  })
})

describe("tool_run_measures()", {
  it("registers data frame results and returns schema summary", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    withr::defer(db$cleanup())

    td <- ellmer::tool(
      function() data.frame(region = "West", revenue = 100, stringsAsFactors = FALSE),
      "Returns regional revenue. Columns: region (string), revenue (number).",
      name = "revenue_by_region"
    )
    measures <- list(revenue_by_region = td)
    tool <- tool_run_measures(measures, db)

    calls_json <- '[{"name": "revenue_by_region", "arguments": {}}]'
    result <- tool(calls = calls_json)
    expect_s3_class(result, "ellmer::ContentToolResult")
    value <- S7::prop(result, "value")
    expect_match(value, "_run_1")
    expect_match(value, "region")
    expect_match(value, "revenue")
  })

  it("includes scalar results directly in response", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    withr::defer(db$cleanup())

    td <- ellmer::tool(function() 42L, "Total order count.", name = "order_count")
    tool <- tool_run_measures(list(order_count = td), db)

    calls_json <- '[{"name": "order_count", "arguments": {}}]'
    result <- tool(calls = calls_json)
    value <- S7::prop(result, "value")
    expect_match(value, "42")
  })
})

describe("tool_prepare_visualization()", {
  it("creates named table from SELECT query referencing _run tables", {
    skip_if_not_installed("duckdb")
    db <- new_ephemeral_db()
    withr::defer(db$cleanup())

    df <- data.frame(x = 1:3, y = c(10, 20, 30), stringsAsFactors = FALSE)
    tbl <- db$register(df)

    tool <- tool_prepare_visualization(db)

    preps_json <- sprintf(
      '[{"name": "my_data", "query": "SELECT * FROM %s"}]',
      tbl
    )
    result <- tool(preparations = preps_json)
    expect_s3_class(result, "ellmer::ContentToolResult")

    tables <- db$list_tables()
    expect_true("my_data" %in% tables)
    expect_false(tbl %in% tables)  # _run_ tables dropped
  })
})
