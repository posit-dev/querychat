decode_handoff_payload <- function(message) {
  jsonlite::fromJSON(
    shiny:::toJSON(message$payload),
    simplifyVector = FALSE
  )
}

describe("handoff_message_type()", {
  it("returns the exact browser message type for canonical actions", {
    actions <- c(
      "recommend",
      "recommend-error",
      "source-update",
      "streaming",
      "panel-toggle"
    )

    expect_identical(
      unname(vapply(actions, handoff_message_type, character(1))),
      paste0("querychat-handoff-", actions)
    )
  })

  it("rejects noncanonical and malformed actions", {
    expect_snapshot(error = TRUE, handoff_message_type("unknown"))
    expect_snapshot(
      error = TRUE,
      handoff_message_type(c("streaming", "panel-toggle"))
    )
    expect_snapshot(error = TRUE, handoff_message_type(NA_character_))
  })

  it("drops names from canonical actions", {
    expect_identical(
      handoff_message_type(c(action = "streaming")),
      "querychat-handoff-streaming"
    )
  })
})

describe("handoff_recommend_message()", {
  it("builds the exact recommendation message", {
    recommendation <- HandoffRecommendation(
      selected_ids = c("query-0", "viz-1"),
      format_id = "quarto-dashboard",
      directions = "Lead with the chart."
    )

    expect_identical(
      handoff_recommend_message(
        "module-handoff_modal_root",
        recommendation,
        "module-handoff_directions"
      ),
      list(
        type = "querychat-handoff-recommend",
        payload = list(
          root_id = "module-handoff_modal_root",
          selected_ids = list("query-0", "viz-1"),
          format_id = "quarto-dashboard",
          directions = "Lead with the chart.",
          directions_id = "module-handoff_directions"
        )
      )
    )
  })

  it("serializes one selected ID as a JSON array", {
    recommendation <- HandoffRecommendation(
      selected_ids = "query-0",
      format_id = "quarto-dashboard"
    )

    message <- handoff_recommend_message(
      "module-handoff_modal_root",
      recommendation,
      "module-handoff_directions"
    )
    json <- shiny:::toJSON(message$payload)

    expect_identical(message$payload$selected_ids, list("query-0"))
    expect_match(
      json,
      '"selected_ids":["query-0"]',
      fixed = TRUE
    )
    expect_identical(
      jsonlite::fromJSON(json, simplifyVector = FALSE)$selected_ids,
      list("query-0")
    )
  })

  it("serializes named inputs as scalars and selected IDs as an array", {
    recommendation <- HandoffRecommendation(
      selected_ids = c(item = "query-0"),
      format_id = c(format = "quarto-dashboard"),
      directions = c(notes = "Lead with the chart.")
    )

    message <- handoff_recommend_message(
      c(root = "module-handoff_modal_root"),
      recommendation,
      c(directions = "module-handoff_directions")
    )

    expect_identical(
      message$payload,
      list(
        root_id = "module-handoff_modal_root",
        selected_ids = list("query-0"),
        format_id = "quarto-dashboard",
        directions = "Lead with the chart.",
        directions_id = "module-handoff_directions"
      )
    )
    expect_identical(decode_handoff_payload(message), message$payload)
  })
})

describe("handoff_recommend_error_message()", {
  it("builds the exact recommendation error message", {
    expect_identical(
      handoff_recommend_error_message(
        "module-handoff_modal_root",
        "Service unavailable"
      ),
      list(
        type = "querychat-handoff-recommend-error",
        payload = list(
          root_id = "module-handoff_modal_root",
          error = "Service unavailable"
        )
      )
    )
  })

  it("serializes named inputs as strings", {
    message <- handoff_recommend_error_message(
      c(root = "module-handoff_modal_root"),
      c(problem = "Service unavailable")
    )

    expect_identical(
      decode_handoff_payload(message),
      list(
        root_id = "module-handoff_modal_root",
        error = "Service unavailable"
      )
    )
  })
})

describe("handoff_source_update_message()", {
  it("omits optional NULL fields", {
    expect_identical(
      handoff_source_update_message(
        "module-handoff_root",
        "module-handoff_source_editor",
        "print(1)"
      ),
      list(
        type = "querychat-handoff-source-update",
        payload = list(
          root_id = "module-handoff_root",
          id = "module-handoff_source_editor",
          value = "print(1)"
        )
      )
    )
  })

  it("builds the exact complete source payload", {
    expect_identical(
      handoff_source_update_message(
        "module-handoff_root",
        "module-handoff_source_editor",
        "print(1)",
        append = TRUE,
        language = "r",
        download_available = FALSE
      ),
      list(
        type = "querychat-handoff-source-update",
        payload = list(
          root_id = "module-handoff_root",
          id = "module-handoff_source_editor",
          value = "print(1)",
          append = TRUE,
          language = "r",
          download_available = FALSE
        )
      )
    )
  })

  it("rejects malformed scalars and extra fields", {
    expect_snapshot(
      error = TRUE,
      handoff_source_update_message(
        c("root-a", "root-b"),
        "editor",
        "print(1)"
      )
    )
    expect_snapshot(
      error = TRUE,
      handoff_source_update_message(
        "root",
        "editor",
        "print(1)",
        append = 1
      )
    )
    expect_snapshot(
      error = TRUE,
      do.call(
        handoff_source_update_message,
        list(
          root_id = "root",
          id = "editor",
          value = "print(1)",
          extra = TRUE
        )
      )
    )
  })

  it("serializes every named input with its scalar JSON type", {
    message <- handoff_source_update_message(
      c(root = "module-handoff_root"),
      c(editor = "module-handoff_source_editor"),
      c(source = "print(1)"),
      append = c(append = FALSE),
      language = c(language = "r"),
      download_available = c(download = FALSE)
    )

    expect_identical(
      decode_handoff_payload(message),
      list(
        root_id = "module-handoff_root",
        id = "module-handoff_source_editor",
        value = "print(1)",
        append = FALSE,
        language = "r",
        download_available = FALSE
      )
    )
  })
})

describe("handoff_streaming_message()", {
  it("builds the exact streaming message", {
    expect_identical(
      handoff_streaming_message("module-handoff_root", TRUE),
      list(
        type = "querychat-handoff-streaming",
        payload = list(
          root_id = "module-handoff_root",
          active = TRUE
        )
      )
    )
  })

  it("serializes named inputs as a string and boolean", {
    message <- handoff_streaming_message(
      c(root = "module-handoff_root"),
      c(active = FALSE)
    )

    expect_identical(
      decode_handoff_payload(message),
      list(root_id = "module-handoff_root", active = FALSE)
    )
  })
})

describe("handoff_panel_toggle_message()", {
  it("builds the exact panel toggle message", {
    expect_identical(
      handoff_panel_toggle_message("module-handoff_root", FALSE),
      list(
        type = "querychat-handoff-panel-toggle",
        payload = list(
          root_id = "module-handoff_root",
          open = FALSE
        )
      )
    )
  })

  it("serializes named inputs as a string and boolean", {
    message <- handoff_panel_toggle_message(
      c(root = "module-handoff_root"),
      c(open = FALSE)
    )

    expect_identical(
      decode_handoff_payload(message),
      list(root_id = "module-handoff_root", open = FALSE)
    )
  })
})
