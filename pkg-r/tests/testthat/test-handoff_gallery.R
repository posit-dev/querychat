new_gallery_request <- function(id, name, arguments) {
  ellmer::ContentToolRequest(
    id = id,
    name = name,
    arguments = arguments
  )
}

new_gallery_query_result <- function(
  id = "query-call",
  name = "querychat_query",
  arguments = list(
    query = "SELECT COUNT(*) AS count FROM sales",
    `_intent` = "Count sales"
  ),
  value = data.frame(count = 42),
  error = NULL
) {
  ellmer::ContentToolResult(
    value = value,
    error = error,
    request = new_gallery_request(id, name, arguments)
  )
}

new_gallery_viz_result <- function(
  id = "viz-call",
  arguments = list(
    ggsql = "SELECT x, y FROM sales VISUALISE x, y DRAW point",
    title = "Sales chart"
  ),
  image_data = "aW1hZ2U=",
  error = NULL
) {
  value <- list(ellmer::ContentText("Chart displayed."))
  if (!is.null(image_data)) {
    value <- c(
      value,
      list(
        ellmer::ContentImageInline(
          type = "image/png",
          data = image_data
        )
      )
    )
  }

  ellmer::ContentToolResult(
    value = value,
    error = error,
    request = new_gallery_request(
      id,
      "querychat_visualize",
      arguments
    )
  )
}

new_gallery_turn <- function(...) {
  ellmer::AssistantTurn(list(...))
}

describe("extract_handoff_gallery_items()", {
  it("extracts recognized successful query and update operations", {
    turns <- list(
      new_gallery_turn(
        new_gallery_query_result(),
        new_gallery_query_result(
          id = "update-call",
          name = "querychat_update_dashboard",
          arguments = list(
            query = "SELECT * FROM sales WHERE region = 'East'",
            title = "East region"
          ),
          value = "Dashboard updated"
        )
      )
    )

    items <- extract_handoff_gallery_items(turns)

    expect_length(items, 2L)
    expect_s7_class(items[[1]], HandoffQueryItem)
    expect_identical(items[[1]]@id, "query-0")
    expect_identical(items[[1]]@title, "Count sales")
    expect_identical(items[[1]]@sql, "SELECT COUNT(*) AS count FROM sales")
    expect_match(items[[1]]@preview_html, "<td>42</td>", fixed = TRUE)
    expect_identical(items[[2]]@id, "query-1")
    expect_identical(items[[2]]@title, "East region")
    expect_null(items[[2]]@preview_html)
  })

  it("uses title, intent, then the first 60 SQL characters", {
    sql <- paste(
      rep("SELECT a_really_long_column FROM sales", 3),
      collapse = " "
    )
    turns <- list(
      new_gallery_turn(
        new_gallery_query_result(
          id = "title",
          arguments = list(
            query = "SELECT 1",
            title = "Explicit title",
            `_intent` = "Intent title"
          )
        ),
        new_gallery_query_result(
          id = "intent",
          arguments = list(
            query = "SELECT 2",
            title = "",
            `_intent` = "Intent title"
          )
        ),
        new_gallery_query_result(
          id = "sql",
          arguments = list(query = sql)
        )
      )
    )

    items <- extract_handoff_gallery_items(turns)

    expect_identical(
      vapply(items, \(item) item@title, character(1)),
      c("Explicit title", "Intent title", substr(sql, 1L, 60L))
    )
  })

  it("caps and escapes previews while formatting numeric missing values", {
    preview <- data.frame(
      "<script>" = c("<img src=x>", NA, "R&D", "\"quoted\"", "fifth row"),
      whole = c(42, 2, 3, 4, 5),
      decimal = c(1.234, 2.345, 3.456, 4.567, 5.678),
      special = c(Inf, -Inf, NaN, NA, 0),
      omitted = rep("fifth column", 5),
      check.names = FALSE
    )
    turns <- list(
      new_gallery_turn(new_gallery_query_result(value = preview))
    )

    item <- extract_handoff_gallery_items(turns)[[1]]
    html <- item@preview_html

    expect_match(html, "<th>&lt;script&gt;</th>", fixed = TRUE)
    expect_no_match(html, "<th><script></th>", fixed = TRUE)
    expect_match(html, "&lt;img src=x&gt;", fixed = TRUE)
    expect_match(html, "R&amp;D", fixed = TRUE)
    expect_match(html, "&quot;quoted&quot;", fixed = TRUE)
    expect_match(html, "<td>42</td>", fixed = TRUE)
    expect_match(html, "<td>1.23</td>", fixed = TRUE)
    expect_match(html, "<td>inf</td>", fixed = TRUE)
    expect_match(html, "<td>-inf</td>", fixed = TRUE)
    expect_match(html, "<td>nan</td>", fixed = TRUE)
    expect_match(html, "<td></td>", fixed = TRUE)
    expect_no_match(html, "fifth row", fixed = TRUE)
    expect_no_match(html, "omitted", fixed = TRUE)
    expect_length(
      gregexpr("<tr>", html, fixed = TRUE)[[1]],
      5L
    )
  })

  it("associates expanded image marker blocks by request ID", {
    turns <- list(
      new_gallery_turn(
        new_gallery_viz_result(
          id = "viz-a",
          arguments = list(
            ggsql = "SELECT a FROM sales VISUALISE a DRAW bar",
            title = "Chart A"
          ),
          image_data = "QUFB"
        ),
        new_gallery_query_result(
          id = "query-b",
          arguments = list(
            query = "SELECT b FROM sales",
            title = "Query B"
          )
        ),
        new_gallery_viz_result(
          id = "viz-c",
          arguments = list(
            ggsql = "SELECT c FROM sales VISUALISE c DRAW line",
            title = "Chart C"
          ),
          image_data = "Q0ND"
        )
      )
    )

    items <- extract_handoff_gallery_items(turns)

    expect_identical(
      vapply(items, \(item) item@id, character(1)),
      c("viz-0", "query-1", "viz-2")
    )
    expect_identical(
      vapply(items, \(item) item@title, character(1)),
      c("Chart A", "Query B", "Chart C")
    )
    expect_identical(items[[1]]@thumbnail, "data:image/png;base64,QUFB")
    expect_identical(items[[3]]@thumbnail, "data:image/png;base64,Q0ND")
  })

  it("ignores orphan multipart results before expanding valid results", {
    orphan <- ellmer::ContentToolResult(
      value = list(
        ellmer::ContentText("Orphaned output."),
        ellmer::ContentImageInline(
          type = "image/png",
          data = "T1JQSEFO"
        )
      )
    )
    turns <- list(
      new_gallery_turn(
        orphan,
        new_gallery_query_result(
          id = "query-valid",
          arguments = list(
            query = "SELECT x FROM sales",
            title = "Valid query"
          )
        ),
        new_gallery_viz_result(
          id = "viz-valid",
          arguments = list(
            ggsql = "SELECT x FROM sales VISUALISE x DRAW bar",
            title = "Valid chart"
          ),
          image_data = "VkFMSUQ="
        )
      )
    )

    items <- extract_handoff_gallery_items(turns)

    expect_identical(
      vapply(items, \(item) item@id, character(1)),
      c("query-0", "viz-1")
    )
    expect_identical(
      vapply(items, \(item) item@title, character(1)),
      c("Valid query", "Valid chart")
    )
    expect_identical(items[[2]]@thumbnail, "data:image/png;base64,VkFMSUQ=")
  })

  it("falls back to ggsql text and allows a missing thumbnail", {
    ggsql <- paste(
      rep("SELECT x FROM sales VISUALISE x DRAW bar", 2),
      collapse = " "
    )
    turns <- list(
      new_gallery_turn(
        new_gallery_viz_result(
          arguments = list(ggsql = ggsql, title = ""),
          image_data = NULL
        )
      )
    )

    item <- extract_handoff_gallery_items(turns)[[1]]

    expect_identical(item@title, substr(ggsql, 1L, 60L))
    expect_null(item@thumbnail)
  })

  it("ignores images in malformed marker blocks", {
    request <- new_gallery_request(
      "viz-call",
      "querychat_visualize",
      list(
        ggsql = "SELECT x FROM sales VISUALISE x DRAW bar",
        title = "Sales"
      )
    )
    result <- ellmer::ContentToolResult(
      value = 'See <tool-contents call-id="viz-call"> below.',
      request = request
    )
    turn <- new_gallery_turn(
      result,
      ellmer::ContentText('<tool-contents call-id="viz-call">'),
      ellmer::ContentImageInline(type = "image/png", data = "d3Jvbmc=")
    )

    item <- extract_handoff_gallery_items(list(turn))[[1]]

    expect_null(item@thumbnail)
  })

  it("ignores failed, malformed, orphaned, and unrelated results", {
    failed_query <- new_gallery_query_result(error = simpleError("bad SQL"))
    failed_viz <- new_gallery_viz_result(
      id = "failed-viz",
      error = simpleError("bad ggsql")
    )
    orphan <- ellmer::ContentToolResult(value = data.frame(x = 1))
    unrelated <- new_gallery_query_result(
      id = "other",
      name = "other_tool"
    )
    malformed_query <- new_gallery_query_result(
      id = "bad-query",
      arguments = list(query = 1)
    )
    malformed_viz <- new_gallery_viz_result(
      id = "bad-viz",
      arguments = list(title = "Missing ggsql")
    )

    items <- extract_handoff_gallery_items(
      list(
        new_gallery_turn(
          failed_query,
          failed_viz,
          orphan,
          unrelated,
          malformed_query,
          malformed_viz
        )
      )
    )

    expect_length(items, 0L)
  })

  it("returns no items for empty or malformed turn input", {
    expect_identical(extract_handoff_gallery_items(list()), list())
    expect_identical(
      extract_handoff_gallery_items(
        list(
          "not a turn",
          ellmer::UserTurn(list(ellmer::ContentText("hello")))
        )
      ),
      list()
    )
  })
})
