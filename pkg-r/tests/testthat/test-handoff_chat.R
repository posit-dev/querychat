new_recording_handoff_view <- function() {
  view <- new.env(parent = emptyenv())
  view$events <- list()
  view$replace_source <- function(value) {
    view$events[[length(view$events) + 1L]] <- list(
      action = "replace",
      value = value
    )
  }
  view$append_source <- function(value) {
    view$events[[length(view$events) + 1L]] <- list(
      action = "append",
      value = value
    )
  }
  view$set_streaming <- function(active) {
    view$events[[length(view$events) + 1L]] <- list(
      action = "streaming",
      value = active
    )
  }
  view
}

new_mock_handoff_content <- function(value) {
  asNamespace("ellmer")[["ContentJson"]](data = value)
}

new_mock_handoff_result <- function(
  source,
  language = "r",
  referenced_tables = "sales"
) {
  list(
    source = source,
    language = language,
    referenced_tables = referenced_tables
  )
}

describe("partial_json_string()", {
  it("waits for the requested JSON string field", {
    expect_null(partial_json_string("{", "source"))
  })

  it("decodes completed escape sequences from an incomplete string", {
    expect_equal(
      partial_json_string(
        '{"source":"line 1\\nline \\"2\\"\\\\',
        "source"
      ),
      "line 1\nline \"2\"\\"
    )
  })

  it("decodes completed Unicode escape sequences", {
    expect_equal(
      partial_json_string('{"source":"caf\\u00e9"', "source"),
      "café"
    )
  })

  it("omits an incomplete Unicode escape sequence", {
    expect_equal(
      partial_json_string('{"source":"caf\\u00', "source"),
      "caf"
    )
  })

  it("combines UTF-16 surrogate pairs", {
    expect_equal(
      partial_json_string(
        '{"source":"face \\ud83d\\ude00',
        "source"
      ),
      "face 😀"
    )
  })

  it("suppresses incomplete surrogate pairs until the low pair arrives", {
    high_pair <- '{"source":"face \\ud83d'

    expect_equal(partial_json_string(high_pair, "source"), "face ")
    expect_equal(
      partial_json_string(
        paste0(high_pair, "\\ude00"),
        "source"
      ),
      "face 😀"
    )
    expect_equal(
      partial_json_string(
        paste0(high_pair, "\\u00"),
        "source"
      ),
      "face "
    )
  })

  it("decodes a large source without per-character allocation growth", {
    skip_if_not(capabilities("profmem"))
    for (i in seq_len(5L)) {
      partial_json_string('{"source":"warmup')
    }
    profile <- withr::local_tempfile()
    value <- paste0('{"source":"', strrep("a", 50000L))

    Rprofmem(profile)
    withr::defer(Rprofmem(NULL))
    result <- partial_json_string(value)
    Rprofmem(NULL)

    expect_equal(nchar(result), 50000L)
    expect_lt(length(readLines(profile, warn = FALSE)), 10000L)
  })
})

describe("HandoffChat$history_turns()", {
  it("returns the live chat turns", {
    live_turns <- list(ellmer::UserTurn("live question"))
    chat <- MockHandoffChat$new(turns = live_turns)

    expect_equal(HandoffChat$new(chat)$history_turns(), live_turns)
  })
})

describe("HandoffChat$ask()", {
  it("uses replacement turns on a clone without changing live history", {
    live_turns <- list(ellmer::UserTurn("live question"))
    replacement_turns <- list(ellmer::UserTurn("selected context"))
    type <- ellmer::type_object(answer = ellmer::type_string())
    chat <- MockHandoffChat$new(
      structured_result = list(answer = "42"),
      turns = live_turns
    )

    result <- sync_promise(
      HandoffChat$new(chat)$ask(
        "recommend",
        type,
        turns = replacement_turns
      )
    )

    expect_equal(result, list(answer = "42"))
    expect_equal(
      chat$requests()[[1]],
      list(
        turns = replacement_turns,
        system_prompt = NULL,
        prompt = "recommend",
        type = type
      )
    )
    expect_equal(chat$get_turns(), live_turns)
  })
})

describe("HandoffChat$stream()", {
  type <- handoff_result_type("sales", "r")

  it("uses replacement turns and system prompt on a clone", {
    live_turns <- list(ellmer::UserTurn("live question"))
    replacement_turns <- list(ellmer::UserTurn("selected context"))
    parsed <- new_mock_handoff_result("print(1)")
    chat <- MockHandoffChat$new(
      stream_chunks = paste0(
        '{"source":"print(1)","language":"r",',
        '"referenced_tables":["sales"]}'
      ),
      completed_content = new_mock_handoff_content(parsed),
      turns = live_turns,
      system_prompt = "live system"
    )
    view <- new_recording_handoff_view()

    streamed <- sync_promise(
      HandoffChat$new(chat)$stream(
        "generate",
        turns = replacement_turns,
        system_prompt = "handoff system",
        type = type,
        view = view
      )
    )

    expect_equal(
      chat$requests()[[1]],
      list(
        turns = replacement_turns,
        system_prompt = "handoff system",
        prompt = "generate",
        type = type
      )
    )
    expect_equal(streamed$result@source, "print(1)")
    expect_equal(chat$get_turns(), live_turns)
    expect_equal(chat$get_system_prompt(), "live system")
  })

  it("replaces the initial source then appends monotonic suffixes", {
    parsed <- new_mock_handoff_result("print(1)")
    chat <- MockHandoffChat$new(
      stream_chunks = c(
        '{"source":"print',
        "(",
        "1)",
        '","language":"r","referenced_tables":["sales"]}'
      ),
      completed_content = new_mock_handoff_content(parsed)
    )
    view <- new_recording_handoff_view()

    streamed <- sync_promise(
      HandoffChat$new(chat)$stream(
        "generate",
        type = type,
        view = view
      )
    )

    expect_equal(streamed$result@source, "print(1)")
    expect_equal(
      view$events,
      list(
        list(action = "streaming", value = TRUE),
        list(action = "replace", value = "print"),
        list(action = "append", value = "("),
        list(action = "append", value = "1)"),
        list(action = "streaming", value = FALSE)
      )
    )
  })

  it("awaits promised stream chunks", {
    parsed <- new_mock_handoff_result("print(1)")
    chat <- MockHandoffChat$new(
      stream_chunks = list(
        promises::promise_resolve('{"source":"pri'),
        promises::promise_resolve(
          paste0(
            'nt(1)","language":"r",',
            '"referenced_tables":["sales"]}'
          )
        )
      ),
      completed_content = new_mock_handoff_content(parsed)
    )
    view <- new_recording_handoff_view()

    streamed <- sync_promise(
      HandoffChat$new(chat)$stream(
        "generate",
        type = type,
        view = view
      )
    )

    expect_equal(streamed$result@source, "print(1)")
    expect_equal(
      view$events,
      list(
        list(action = "streaming", value = TRUE),
        list(action = "replace", value = "pri"),
        list(action = "append", value = "nt(1)"),
        list(action = "streaming", value = FALSE)
      )
    )
  })

  it("uses completed structured content to correct a divergent partial", {
    parsed <- new_mock_handoff_result("correct source")
    chat <- MockHandoffChat$new(
      stream_chunks = paste0(
        '{"source":"wrong source","language":"r",',
        '"referenced_tables":["sales"]}'
      ),
      completed_content = new_mock_handoff_content(parsed)
    )
    view <- new_recording_handoff_view()

    streamed <- sync_promise(
      HandoffChat$new(chat)$stream(
        "generate",
        type = type,
        view = view
      )
    )

    expect_equal(streamed$result@source, "correct source")
    expect_equal(
      view$events,
      list(
        list(action = "streaming", value = TRUE),
        list(action = "replace", value = "wrong source"),
        list(action = "replace", value = "correct source"),
        list(action = "streaming", value = FALSE)
      )
    )
  })

  it("returns the clone's completed turns", {
    selected_turn <- ellmer::UserTurn("selected context")
    parsed <- new_mock_handoff_result("print(1)")
    chat <- MockHandoffChat$new(
      stream_chunks = paste0(
        '{"source":"print(1)","language":"r",',
        '"referenced_tables":["sales"]}'
      ),
      completed_content = new_mock_handoff_content(parsed),
      turns = list(ellmer::UserTurn("live question"))
    )

    streamed <- sync_promise(
      HandoffChat$new(chat)$stream(
        "generate",
        turns = list(selected_turn),
        type = type,
        view = new_recording_handoff_view()
      )
    )

    expect_length(streamed$turns, 3L)
    expect_equal(streamed$turns[[1]], selected_turn)
    expect_equal(streamed$turns[[2]]@text, "generate")
    expect_equal(streamed$turns[[3]]@contents[[1]]@parsed, parsed)
  })

  it("propagates native structured-stream rejection without fallback", {
    rejection <- simpleError(
      paste(
        "Streaming structured output requires native provider support",
        "for the supplied model."
      )
    )
    chat <- MockHandoffChat$new(stream_error = rejection)
    view <- new_recording_handoff_view()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        HandoffChat$new(chat)$stream(
          "generate",
          type = type,
          view = view
        )
      )
    )

    expect_length(chat$requests(), 1L)
    expect_equal(
      view$events,
      list(
        list(action = "streaming", value = TRUE),
        list(action = "streaming", value = FALSE)
      )
    )
  })

  it("rejects chats without structured streaming before changing the view", {
    chat <- mock_ellmer_chat_client(
      public = list(
        stream_async = function(prompt) {
          stop("legacy stream should not be called")
        }
      )
    )
    view <- new_recording_handoff_view()

    expect_snapshot(
      error = TRUE,
      HandoffChat$new(chat)$stream(
        "generate",
        type = type,
        view = view
      )
    )

    expect_length(view$events, 0L)
  })

  it("clears streaming after an error", {
    chat <- MockHandoffChat$new(
      stream_chunks = '{"source":"partial',
      stream_error = simpleError("stream failed")
    )
    view <- new_recording_handoff_view()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        HandoffChat$new(chat)$stream(
          "generate",
          type = type,
          view = view
        )
      )
    )

    expect_equal(
      tail(view$events, 1L),
      list(list(action = "streaming", value = FALSE))
    )
  })

  it("clears streaming after synchronous stream setup rejection", {
    chat <- MockHandoffChat$new(
      stream_start_error = simpleError("stream setup failed")
    )
    view <- new_recording_handoff_view()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        HandoffChat$new(chat)$stream(
          "generate",
          type = type,
          view = view
        )
      )
    )

    expect_equal(
      view$events,
      list(
        list(action = "streaming", value = TRUE),
        list(action = "streaming", value = FALSE)
      )
    )
  })

  it("clears streaming after cancellation", {
    cancellation <- structure(
      list(message = "generation cancelled", call = NULL),
      class = c("mock_handoff_cancellation", "error", "condition")
    )
    chat <- MockHandoffChat$new(
      stream_chunks = '{"source":"partial',
      cancellation = cancellation
    )
    view <- new_recording_handoff_view()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        HandoffChat$new(chat)$stream(
          "generate",
          type = type,
          view = view
        )
      )
    )

    expect_equal(
      tail(view$events, 1L),
      list(list(action = "streaming", value = FALSE))
    )
  })

  it("rejects normally exhausted partial-turn cancellation", {
    chat <- MockHandoffChat$new(
      stream_chunks = '{"source":"partial',
      partial_turn_reason = "cancelled"
    )
    view <- new_recording_handoff_view()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        HandoffChat$new(chat)$stream(
          "generate",
          type = type,
          view = view
        )
      )
    )

    expect_equal(
      chat$requests(),
      list(list(
        turns = list(),
        system_prompt = NULL,
        prompt = "generate",
        type = type
      ))
    )
    expect_equal(
      tail(view$events, 1L),
      list(list(action = "streaming", value = FALSE))
    )
  })
})

describe("update_streamed_source()", {
  it("replaces a source that does not extend the previous value", {
    view <- new_recording_handoff_view()

    current <- update_streamed_source(view, "abc", "axy")

    expect_equal(current, "axy")
    expect_equal(
      view$events,
      list(list(action = "replace", value = "axy"))
    )
  })
})

describe("completed_json_content()", {
  it("does not use completed content from an earlier assistant turn", {
    old_content <- new_mock_handoff_content(
      new_mock_handoff_result("old source")
    )
    turns <- list(
      ellmer::AssistantTurn(list(old_content)),
      ellmer::AssistantPartialTurn("partial source")
    )

    expect_snapshot(
      error = TRUE,
      completed_json_content(turns)
    )
  })
})

describe("sync_promise()", {
  it("fails with a diagnostic when a promise does not settle", {
    pending <- promises::promise(function(resolve, reject) {
      invisible(NULL)
    })

    expect_snapshot(
      error = TRUE,
      sync_promise(pending, timeout = 0.01)
    )
  })
})
