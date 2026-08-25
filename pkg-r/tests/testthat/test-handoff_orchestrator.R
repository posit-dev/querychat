new_orchestrator_gallery_turn <- function() {
  request <- ellmer::ContentToolRequest(
    id = "query-call",
    name = "querychat_query",
    arguments = list(
      query = "SELECT SUM(amount) AS total FROM sales",
      title = "Total sales"
    )
  )
  ellmer::AssistantTurn(list(
    ellmer::ContentToolResult(
      value = '[{"total":42}]',
      request = request
    )
  ))
}

new_plan_orchestrator <- function(
  history = list(new_orchestrator_gallery_turn()),
  ask_results = list()
) {
  chat <- new_recording_handoff_chat(
    history = history,
    ask_results = ask_results
  )
  view <- new_recording_handoff_view()
  executor <- new_recording_handoff_executor(list(
    sales = "SCHEMA sales amount DOUBLE",
    customers = "SCHEMA customers id INTEGER"
  ))
  data_sources <- list(
    sales = new_fake_handoff_data_source("sales", "PostgreSQL"),
    customers = new_fake_handoff_data_source("customers", "SQLite")
  )
  orchestrator <- HandoffOrchestrator$new(
    chat = chat$chat,
    data_sources = data_sources,
    executor = executor,
    view = view
  )
  list(
    orchestrator = orchestrator,
    chat = chat,
    view = view,
    executor = executor,
    data_sources = data_sources
  )
}

describe("HandoffOrchestrator$open_modal()", {
  it("stores the current gallery and shows it", {
    fixture <- new_plan_orchestrator()

    items <- fixture$orchestrator$open_modal()

    expect_length(items, 1L)
    expect_identical(items[[1]]@id, "query-0")
    expect_identical(
      fixture$view$events,
      list(list(action = "show_modal", items = items))
    )
  })
})

describe("HandoffOrchestrator$recommend()", {
  it("asks for only current item and registry format IDs", {
    raw <- list(
      selected_ids = "query-0",
      format_id = "quarto-dashboard",
      directions = "Use one chart."
    )
    fixture <- new_plan_orchestrator(ask_results = list(raw))
    items <- fixture$orchestrator$open_modal()

    recommendation <- sync_promise(
      fixture$orchestrator$recommend(items)
    )

    expect_s7_class(recommendation, HandoffRecommendation)
    request <- fixture$chat$state$events[[1]]
    expect_identical(
      request$type@properties$selected_ids@items@values,
      "query-0"
    )
    expect_identical(
      request$type@properties$format_id@values,
      names(handoff_registry())
    )
  })
})

describe("HandoffOrchestrator$prepare_generation()", {
  it("resolves built-ins and includes current items, schemas, and data", {
    fixture <- new_plan_orchestrator()
    fixture$orchestrator$open_modal()
    request <- HandoffGenerateRequest(
      selected_ids = c("query-0", "stale-id"),
      type_id = "quarto-dashboard",
      language = "r"
    )

    plan <- sync_promise(
      fixture$orchestrator$prepare_generation(
        request,
        "Use a compact layout."
      )
    )

    expect_s7_class(plan$handoff_format, HandoffFormat)
    expect_s7_class(plan$handoff_type, HandoffType)
    expect_identical(plan$handoff_type@language, "r")
    expect_identical(plan$handoff_type@file_extension, ".qmd")
    expect_match(
      plan$system_prompt,
      "SELECT SUM(amount) AS total FROM sales",
      fixed = TRUE
    )
    expect_no_match(plan$system_prompt, "stale-id", fixed = TRUE)
    expect_match(plan$schema, "SCHEMA sales", fixed = TRUE)
    expect_match(plan$schema, "SCHEMA customers", fixed = TRUE)
    expect_match(
      plan$system_prompt,
      'Sys.getenv("DATABASE_URL")',
      fixed = TRUE
    )
    expect_identical(
      vapply(
        fixture$executor$calls,
        `[[`,
        character(1),
        "table_name"
      ),
      c("sales", "customers")
    )
    expect_identical(
      plan$result_type@properties$referenced_tables@items@values,
      c("sales", "customers")
    )
    expect_identical(plan$result_type@properties$language@values, "r")
    expect_identical(
      plan$result_type@properties$run_instructions@required,
      TRUE
    )
  })

  it("asks only for safe metadata for a named Other format", {
    fixture <- new_plan_orchestrator(
      ask_results = list(list(
        file_extension = "sql",
        editor_language = "sql"
      ))
    )
    fixture$orchestrator$open_modal()
    request <- HandoffGenerateRequest(
      type_id = "other",
      language = "python",
      freeform = "SQL script"
    )

    plan <- sync_promise(
      fixture$orchestrator$prepare_generation(request, "")
    )

    ask <- fixture$chat$state$events[[1]]
    expect_named(
      ask$type@properties,
      c("file_extension", "editor_language")
    )
    expect_match(ask$prompt, "SQL script", fixed = TRUE)
    expect_null(plan$handoff_format)
    expect_identical(plan$handoff_type@id, "other")
    expect_identical(plan$handoff_type@file_extension, ".sql")
    expect_identical(plan$handoff_type@editor_language, "sql")
    expect_identical(plan$handoff_type@structure, "text")
  })

  it("rejects blank Other names before asking the model", {
    fixture <- new_plan_orchestrator()
    request <- HandoffGenerateRequest(
      type_id = "other",
      language = "python",
      freeform = " "
    )

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$prepare_generation(request, "")
      )
    )
    expect_length(fixture$chat$state$events, 0L)
  })

  it("rejects missing languages and incompatible targets", {
    fixture <- new_plan_orchestrator()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$prepare_generation(
          HandoffGenerateRequest(type_id = "quarto-dashboard"),
          ""
        )
      )
    )
    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$prepare_generation(
          HandoffGenerateRequest(
            type_id = "marimo-notebook",
            language = "r"
          ),
          ""
        )
      )
    )
  })

  it("rejects unknown built-in format IDs", {
    fixture <- new_plan_orchestrator()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$prepare_generation(
          HandoffGenerateRequest(
            type_id = "unknown-format",
            language = "python"
          ),
          ""
        )
      )
    )
  })
})

new_transaction_handoff_result <- function(
  source = "print('done')",
  language = "r",
  summary = "Completed handoff",
  turns = list(ellmer::UserTurn("Generate it")),
  referenced_tables = "sales"
) {
  list(
    result = HandoffResult(
      source = source,
      language = language,
      summary = summary,
      run_instructions = "Run the handoff.",
      referenced_tables = referenced_tables
    ),
    turns = turns
  )
}

new_transaction_orchestrator <- function(
  stream_results,
  view_failures = list(),
  data_sources = NULL,
  bundle_store = NULL,
  max_bundle_bytes = 5 * 1024^2
) {
  journal <- new_handoff_event_journal()
  chat <- new_recording_handoff_chat(
    stream_results = stream_results,
    journal = journal
  )
  view <- new_recording_handoff_view(
    failures = view_failures,
    journal = journal
  )
  store <- new_recording_handoff_store(journal)
  bundle_store <- bundle_store %||% HandoffBundleStore$new()
  executor <- new_recording_handoff_executor(list(
    sales = "SCHEMA sales amount DOUBLE"
  ))
  data_sources <- data_sources %||%
    list(sales = new_fake_handoff_data_source("sales", "PostgreSQL"))
  orchestrator <- HandoffOrchestrator$new(
    chat = chat$chat,
    data_sources = data_sources,
    executor = executor,
    view = view,
    store = store,
    bundle_store = bundle_store,
    max_bundle_bytes = max_bundle_bytes
  )
  list(
    orchestrator = orchestrator,
    chat = chat,
    view = view,
    store = store,
    bundle_store = bundle_store,
    journal = journal
  )
}

transaction_request <- function() {
  HandoffGenerateRequest(
    type_id = "quarto-dashboard",
    language = "r"
  )
}

new_revision_handoff_state <- function(
  handoff_id = "handoff-1",
  source = "old source",
  turns = list(ellmer::AssistantTurn("Old handoff")),
  bundle_id = NULL,
  bundled_tables = character()
) {
  HandoffState(
    handoff_id = handoff_id,
    handoff_type = resolve_handoff_type("quarto-dashboard", "r"),
    system_prompt = "Saved handoff system prompt",
    source = source,
    turns = turns,
    summary = "Old summary",
    run_instructions = "Run the old handoff.",
    referenced_tables = "sales",
    bundled_tables = bundled_tables,
    bundle_id = bundle_id,
    data_instructions = "Use the saved data snapshot."
  )
}

journal_actions <- function(fixture) {
  vapply(fixture$journal$events, `[[`, character(1), "action")
}

describe("HandoffOrchestrator$snapshot()", {
  it("returns stored states without changing recency", {
    fixture <- new_transaction_orchestrator(list())
    states <- lapply(
      c("handoff-1", "handoff-2", "handoff-3"),
      new_revision_handoff_state
    )
    invisible(lapply(states, fixture$store$remember))
    fixture$store$get("handoff-1")
    expected <- fixture$store$values()

    snapshot <- fixture$orchestrator$snapshot()

    expect_identical(snapshot, expected)
    expect_identical(fixture$store$values(), expected)
  })
})

describe("HandoffOrchestrator$close_panel()", {
  it("delegates panel closure to the view", {
    fixture <- new_transaction_orchestrator(list())
    fixture$journal$events <- list()

    result <- fixture$orchestrator$close_panel()

    expect_null(result)
    expect_identical(
      fixture$journal$events,
      list(list(action = "set_panel_open", open = FALSE))
    )
  })
})

describe("HandoffOrchestrator$restore_snapshot()", {
  it("replaces the store from validated records", {
    fixture <- new_transaction_orchestrator(list())
    fixture$store$remember(new_revision_handoff_state("old"))
    restored <- new_revision_handoff_state("restored", source = "restored")

    fixture$orchestrator$restore_snapshot(
      list(handoff_state_record(restored))
    )

    expect_identical(fixture$store$snapshot(), list(restored))
  })

  it("leaves state and bundles intact when validation fails", {
    fixture <- new_transaction_orchestrator(list())
    bundle <- fixture$bundle_store$stage(
      list("sales.csv" = charToRaw("old"))
    )
    state <- new_revision_handoff_state(
      bundle_id = bundle@bundle_id,
      bundled_tables = "sales"
    )
    fixture$store$remember(state)

    expect_snapshot(
      error = TRUE,
      fixture$orchestrator$restore_snapshot(list(list(version = 99L)))
    )

    expect_identical(fixture$store$snapshot(), list(state))
    expect_identical(
      fixture$bundle_store$get(bundle@bundle_id),
      bundle
    )
  })
})

describe("HandoffOrchestrator$generate()", {
  it("commits in exact transaction order and refreshes availability", {
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result())
    )

    sync_promise(
      fixture$orchestrator$generate(
        transaction_request(),
        "Use one page.",
        "handoff-1"
      )
    )

    expect_identical(
      journal_actions(fixture),
      c(
        "remove_modal",
        "clear_source",
        "stream",
        "show_handoff",
        "remember",
        "append_pill",
        "show_handoff"
      )
    )
    expect_identical(
      fixture$journal$events[[2]],
      list(action = "clear_source", language = "markdown")
    )
    expect_identical(
      fixture$journal$events[[4]]$download_available,
      FALSE
    )
    expect_identical(
      fixture$journal$events[[7]]$download_available,
      TRUE
    )
    state <- fixture$store$get("handoff-1")
    expect_s7_class(state, HandoffState)
    expect_identical(state@source, "print('done')")
    expect_identical(
      state@data_instructions,
      paste0(
        "The data comes from a PostgreSQL database with a table named ",
        "\"sales\".\n\n",
        "Generate a clearly marked DATA SETUP section at the top of the ",
        "handoff.\n",
        "Include a TODO comment for the PostgreSQL database connection.\n",
        "Use DBI with the appropriate database backend. For credentials, use ",
        "environment variables such as `Sys.getenv(\"DATABASE_URL\")`.\n",
        "Do not hardcode passwords or connection strings.\n",
        "Make the required user change clear before the handoff runs."
      )
    )
  })

  it("repairs one validation failure using accumulated handoff turns", {
    first_turns <- list(ellmer::UserTurn("Initial generation"))
    fixture <- new_transaction_orchestrator(list(
      new_transaction_handoff_result(source = " ", turns = first_turns),
      new_transaction_handoff_result(source = "print('repaired')")
    ))

    sync_promise(
      fixture$orchestrator$generate(
        transaction_request(),
        "",
        "handoff-1"
      )
    )

    stream_events <- Filter(
      \(event) identical(event$action, "stream"),
      fixture$journal$events
    )
    expect_length(stream_events, 2L)
    expect_match(
      stream_events[[2]]$prompt,
      "failed structural validation",
      fixed = TRUE
    )
    expect_identical(stream_events[[2]]$turns, first_turns)
    expect_identical(
      fixture$store$get("handoff-1")@source,
      "print('repaired')"
    )
  })

  it("rejects a repaired language change and rolls back", {
    fixture <- new_transaction_orchestrator(list(
      new_transaction_handoff_result(source = " "),
      new_transaction_handoff_result(
        source = "print('python')",
        language = "python"
      )
    ))

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(
          transaction_request(),
          "",
          "handoff-1"
        )
      )
    )

    expect_length(fixture$store$values(), 0L)
    expect_identical(tail(journal_actions(fixture), 1L), "clear_source")
    expect_identical(
      tail(fixture$journal$events, 1L)[[1]]$language,
      "plain"
    )
  })

  it("rolls back stream and cancellation failures", {
    failures <- list(
      simpleError("stream failed"),
      structure(
        list(message = "generation cancelled", call = NULL),
        class = c("mock_handoff_cancellation", "error", "condition")
      )
    )

    for (failure in failures) {
      fixture <- new_transaction_orchestrator(list(failure))

      expect_snapshot(
        error = TRUE,
        sync_promise(
          fixture$orchestrator$generate(
            transaction_request(),
            "",
            "handoff-1"
          )
        )
      )
      expect_length(fixture$store$values(), 0L)
      expect_identical(
        journal_actions(fixture),
        c("remove_modal", "clear_source", "stream", "clear_source")
      )
    }
  })

  it("rolls back a second validation failure", {
    fixture <- new_transaction_orchestrator(list(
      new_transaction_handoff_result(source = " "),
      new_transaction_handoff_result(source = "\n")
    ))

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(
          transaction_request(),
          "",
          "handoff-1"
        )
      )
    )

    expect_length(fixture$store$values(), 0L)
    expect_identical(tail(journal_actions(fixture), 1L), "clear_source")
  })

  it("rolls back completed-view failures before remember", {
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result()),
      view_failures = list(show_handoff = 1L)
    )

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(
          transaction_request(),
          "",
          "handoff-1"
        )
      )
    )
    expect_length(fixture$store$values(), 0L)
    expect_identical(
      journal_actions(fixture),
      c(
        "remove_modal",
        "clear_source",
        "stream",
        "show_handoff",
        "clear_source"
      )
    )
  })

  it("keeps the committed handoff when the pill append fails after commit", {
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result()),
      view_failures = list(append_pill = 1L)
    )

    expect_warning(
      sync_promise(
        fixture$orchestrator$generate(
          transaction_request(),
          "",
          "handoff-1"
        )
      ),
      "post-commit step failed"
    )

    expect_identical(fixture$store$has("handoff-1"), TRUE)
    expect_identical(
      journal_actions(fixture),
      c(
        "remove_modal",
        "clear_source",
        "stream",
        "show_handoff",
        "remember",
        "append_pill"
      )
    )
  })

  it("keeps the committed handoff when bundle eviction fails after commit", {
    FailingEvictBundleStore <- R6::R6Class(
      "FailingEvictBundleStore",
      inherit = HandoffBundleStore,
      public = list(
        evict = function() {
          stop("evict failed")
        }
      )
    )
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result()),
      bundle_store = FailingEvictBundleStore$new()
    )

    expect_warning(
      sync_promise(
        fixture$orchestrator$generate(
          transaction_request(),
          "",
          "handoff-1"
        )
      ),
      "post-commit step failed"
    )

    expect_identical(fixture$store$has("handoff-1"), TRUE)
    expect_identical(
      tail(journal_actions(fixture), 2L),
      c("remember", "append_pill")
    )
  })

  it("keeps committed state when the availability refresh fails", {
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result()),
      view_failures = list(show_handoff = 2L)
    )

    expect_no_error(
      sync_promise(
        fixture$orchestrator$generate(
          transaction_request(),
          "",
          "handoff-1"
        )
      )
    )

    expect_identical(fixture$store$has("handoff-1"), TRUE)
    expect_identical(
      tail(journal_actions(fixture), 3L),
      c(
        "remember",
        "append_pill",
        "show_handoff"
      )
    )
  })

  it("stages one immutable data bundle before commit", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result()),
      data_sources = list(sales = sales$source)
    )

    sync_promise(
      fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
    )

    state <- fixture$store$get("handoff-1")
    expect_identical(state@bundled_tables, "sales")
    expect_false(is.null(state@bundle_id))
    bundle <- fixture$bundle_store$get(state@bundle_id)
    expect_identical(names(bundle@bundled_files), "sales.csv")
    expect_identical(sales$state$get_data_calls, 1L)
  })

  it("corrects oversized referenced data with exactly one repair stream", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(
        new_transaction_handoff_result(),
        new_transaction_handoff_result(source = "print('corrected')")
      ),
      data_sources = list(sales = sales$source),
      max_bundle_bytes = 1
    )

    sync_promise(
      fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
    )

    stream_events <- Filter(
      \(event) identical(event$action, "stream"),
      fixture$journal$events
    )
    expect_length(stream_events, 2L)
    expect_identical(
      stream_events[[2]]$prompt,
      "Return the complete corrected handoff now."
    )
    expect_match(
      stream_events[[2]]$system_prompt,
      "exceed the bundle limit",
      fixed = TRUE
    )
    state <- fixture$store$get("handoff-1")
    expect_identical(state@source, "print('corrected')")
    expect_identical(state@bundled_tables, character())
    expect_null(state@bundle_id)
    expect_match(state@data_instructions, "may need adjustment", fixed = TRUE)
  })

  it("aborts when the correction changes the handoff language", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(
        new_transaction_handoff_result(),
        new_transaction_handoff_result(
          source = "print('python')",
          language = "python"
        )
      ),
      data_sources = list(sales = sales$source),
      max_bundle_bytes = 1
    )

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
      )
    )
    expect_length(fixture$store$values(), 0L)
  })

  it("aborts when the correction changes the referenced-table set", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(
        new_transaction_handoff_result(),
        new_transaction_handoff_result(
          source = "print('corrected')",
          referenced_tables = character()
        )
      ),
      data_sources = list(sales = sales$source),
      max_bundle_bytes = 1
    )

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
      )
    )
    expect_length(fixture$store$values(), 0L)
  })

  it("propagates an unrelated correction stream error unchanged", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(
        new_transaction_handoff_result(),
        simpleError("model returned malformed JSON")
      ),
      data_sources = list(sales = sales$source),
      max_bundle_bytes = 1
    )

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
      )
    )
    expect_length(fixture$store$values(), 0L)
  })

  it("fails when the corrected source is invalid", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(
        new_transaction_handoff_result(),
        new_transaction_handoff_result(source = " ")
      ),
      data_sources = list(sales = sales$source),
      max_bundle_bytes = 1
    )

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
      )
    )
    expect_length(fixture$store$values(), 0L)
  })

  it("rolls back when the correction is cancelled", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    cancellation <- structure(
      list(message = "correction cancelled", call = NULL),
      class = c("mock_handoff_cancellation", "error", "condition")
    )
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result(), cancellation),
      data_sources = list(sales = sales$source),
      max_bundle_bytes = 1
    )

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
      )
    )
    expect_length(fixture$store$values(), 0L)
    expect_identical(tail(journal_actions(fixture), 1L), "clear_source")
  })

  it("evicts least-recently-used bundles after a successful commit", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    small_csv <- export_handoff_csv(sales$source)
    bundle_store <- HandoffBundleStore$new(max_bytes = length(small_csv))
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result()),
      data_sources = list(sales = sales$source),
      bundle_store = bundle_store
    )
    stale_bundle <- fixture$bundle_store$stage(
      list("stale.csv" = charToRaw("x"))
    )

    sync_promise(
      fixture$orchestrator$generate(transaction_request(), "", "handoff-1")
    )

    expect_null(fixture$bundle_store$get(stale_bundle@bundle_id))
  })
})

describe("HandoffOrchestrator$revise()", {
  it("does nothing for missing IDs and blank instructions", {
    fixture <- new_transaction_orchestrator(list())
    state <- new_revision_handoff_state()
    fixture$store$remember(state)
    fixture$journal$events <- list()

    missing <- sync_promise(
      fixture$orchestrator$revise("missing", "Make it smaller.")
    )
    blank <- sync_promise(
      fixture$orchestrator$revise("handoff-1", "   ")
    )
    # The revise textarea reports NULL before it is bound client-side.
    unbound <- sync_promise(
      fixture$orchestrator$revise("handoff-1", NULL)
    )

    expect_identical(missing, FALSE)
    expect_identical(blank, FALSE)
    expect_identical(unbound, FALSE)
    expect_identical(fixture$store$get("handoff-1"), state)
    expect_length(fixture$journal$events, 0L)
  })

  it("preserves LRU order for missing IDs and blank instructions", {
    fixture <- new_transaction_orchestrator(list())
    states <- lapply(
      c("handoff-1", "handoff-2", "handoff-3"),
      new_revision_handoff_state
    )
    invisible(lapply(states, fixture$store$remember))

    missing <- sync_promise(
      fixture$orchestrator$revise("missing", "Make it smaller.")
    )
    blank <- sync_promise(
      fixture$orchestrator$revise("handoff-1", "   ")
    )

    expect_identical(missing, FALSE)
    expect_identical(blank, FALSE)
    expect_identical(fixture$store$values(), states)
  })

  it("replaces from saved context and releases the old bundle after commit", {
    fixture <- new_transaction_orchestrator(list())
    old_bundle <- fixture$bundle_store$stage(
      list("sales.csv" = charToRaw("old"))
    )
    old_turns <- list(ellmer::AssistantTurn("Saved handoff turn"))
    old <- new_revision_handoff_state(
      turns = old_turns,
      bundle_id = old_bundle@bundle_id,
      bundled_tables = "sales"
    )
    fixture$store$remember(old)
    fixture$chat$state$history <- list(
      ellmer::UserTurn("Unrelated live chat turn")
    )
    replacement_turns <- c(
      old_turns,
      list(
        ellmer::UserTurn("Make it smaller."),
        ellmer::AssistantTurn("Revised handoff")
      )
    )
    fixture$chat$state$stream_results <- list(function(view) {
      expect_identical(fixture$store$get("handoff-1"), old)
      expect_identical(
        fixture$bundle_store$get(old_bundle@bundle_id),
        old_bundle
      )
      new_transaction_handoff_result(
        source = "new source",
        summary = "New summary",
        turns = replacement_turns
      )
    })
    show_handoff <- fixture$view$show_handoff
    fixture$view$show_handoff <- function(state, download_available) {
      expect_identical(fixture$store$get("handoff-1"), old)
      expect_identical(
        fixture$bundle_store$get(old_bundle@bundle_id),
        old_bundle
      )
      show_handoff(state, download_available)
    }
    fixture$journal$events <- list()

    revised <- sync_promise(
      fixture$orchestrator$revise("handoff-1", "Make it smaller.")
    )

    replacement <- fixture$store$get("handoff-1")
    stream <- fixture$chat$state$events[[1]]
    expect_identical(revised, TRUE)
    expect_identical(stream$prompt, "Make it smaller.")
    expect_identical(stream$turns, old_turns)
    expect_identical(
      stream$system_prompt,
      "Saved handoff system prompt"
    )
    expect_identical(replacement@handoff_id, old@handoff_id)
    expect_identical(replacement@handoff_type, old@handoff_type)
    expect_identical(replacement@turns, replacement_turns)
    expect_identical(replacement@source, "new source")
    expect_identical(
      journal_actions(fixture),
      c("stream", "show_handoff", "remember")
    )
    expect_null(fixture$bundle_store$get(old_bundle@bundle_id))
  })

  it("retains a shared old bundle while another state references it", {
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result(source = "new source"))
    )
    shared <- fixture$bundle_store$stage(
      list("sales.csv" = charToRaw("shared"))
    )
    fixture$store$remember(new_revision_handoff_state(
      "handoff-1",
      bundle_id = shared@bundle_id,
      bundled_tables = "sales"
    ))
    retained <- new_revision_handoff_state(
      "handoff-2",
      bundle_id = shared@bundle_id,
      bundled_tables = "sales"
    )
    fixture$store$remember(retained)

    sync_promise(
      fixture$orchestrator$revise("handoff-1", "Make it smaller.")
    )

    expect_identical(fixture$store$get("handoff-2"), retained)
    expect_identical(
      fixture$bundle_store$get(shared@bundle_id),
      shared
    )
  })

  it("rejects a revised language change and restores the old handoff", {
    fixture <- new_transaction_orchestrator(list(
      new_transaction_handoff_result(
        source = "new source",
        language = "python"
      )
    ))
    old <- new_revision_handoff_state()
    fixture$store$remember(old)
    fixture$journal$events <- list()

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$revise("handoff-1", "Rewrite it.")
      )
    )

    expect_identical(fixture$store$get("handoff-1"), old)
    restored <- tail(fixture$view$events, 1L)[[1]]
    expect_identical(restored$state, old)
    expect_identical(restored$download_available, TRUE)
  })

  it("restores state, source, and download after transaction failures", {
    cancellation <- structure(
      list(message = "revision cancelled", call = NULL),
      class = c("mock_handoff_cancellation", "error", "condition")
    )
    cases <- list(
      stream = list(
        results = list(simpleError("revision stream failed")),
        failures = list()
      ),
      validation = list(
        results = list(
          new_transaction_handoff_result(source = " "),
          new_transaction_handoff_result(source = "\n")
        ),
        failures = list()
      ),
      cancellation = list(
        results = list(cancellation),
        failures = list()
      ),
      panel = list(
        results = list(
          new_transaction_handoff_result(source = "new source")
        ),
        failures = list(show_handoff = 1L)
      )
    )

    for (case_name in names(cases)) {
      case <- cases[[case_name]]
      fixture <- new_transaction_orchestrator(
        case$results,
        view_failures = case$failures
      )
      bundle <- fixture$bundle_store$stage(
        list("sales.csv" = charToRaw("old"))
      )
      unrelated <- fixture$bundle_store$stage(
        list("other.csv" = charToRaw("other"))
      )
      old <- new_revision_handoff_state(
        bundle_id = bundle@bundle_id,
        bundled_tables = "sales"
      )
      fixture$store$remember(old)
      fixture$journal$events <- list()

      expect_snapshot(
        error = TRUE,
        sync_promise(
          fixture$orchestrator$revise("handoff-1", "Revise it.")
        )
      )

      expect_identical(fixture$store$get("handoff-1"), old)
      restored <- tail(fixture$view$events, 1L)[[1]]
      expect_identical(restored$state, old, info = case_name)
      expect_identical(
        restored$download_available,
        TRUE,
        info = case_name
      )
      expect_identical(
        fixture$bundle_store$get(bundle@bundle_id),
        bundle,
        info = case_name
      )
      expect_identical(
        fixture$bundle_store$get(unrelated@bundle_id),
        unrelated,
        info = case_name
      )
    }
  })

  it("rethrows the original condition when restoring the view fails", {
    original <- structure(
      list(message = "original revision failure", call = NULL, token = 42L),
      class = c("revision_marker_error", "error", "condition")
    )
    fixture <- new_transaction_orchestrator(
      list(original),
      view_failures = list(show_handoff = 1L)
    )
    old <- new_revision_handoff_state()
    fixture$store$remember(old)

    caught <- tryCatch(
      sync_promise(
        fixture$orchestrator$revise("handoff-1", "Revise it.")
      ),
      error = identity
    )

    expect_identical(caught, original)
    expect_snapshot(error = TRUE, stop(caught))
    expect_identical(fixture$store$get("handoff-1"), old)
  })

  it("keeps the committed revision and view when post-commit cleanup fails", {
    FailingEvictBundleStore <- R6::R6Class(
      "FailingEvictBundleStore",
      inherit = HandoffBundleStore,
      public = list(
        evict = function() {
          stop("evict failed")
        }
      )
    )
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result(source = "new source")),
      bundle_store = FailingEvictBundleStore$new()
    )
    old <- new_revision_handoff_state()
    fixture$store$remember(old)
    fixture$journal$events <- list()

    expect_warning(
      revised <- sync_promise(
        fixture$orchestrator$revise("handoff-1", "Make it smaller.")
      ),
      "post-commit step failed"
    )

    expect_identical(revised, TRUE)
    replacement <- fixture$store$get("handoff-1")
    expect_identical(replacement@source, "new source")
    # The view keeps showing the committed replacement; it is not reverted
    # to the pre-revision state.
    shown <- tail(fixture$view$events, 1L)[[1]]
    expect_identical(shown$action, "show_handoff")
    expect_identical(shown$state, replacement)
  })

  it("stages a fresh bundle for normal-sized data and discards the old one", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result(source = "revised source")),
      data_sources = list(sales = sales$source)
    )
    old_bundle <- fixture$bundle_store$stage(
      list("sales.csv" = charToRaw("old"))
    )
    old <- new_revision_handoff_state(
      bundle_id = old_bundle@bundle_id,
      bundled_tables = "sales"
    )
    fixture$store$remember(old)

    sync_promise(
      fixture$orchestrator$revise("handoff-1", "Make it smaller.")
    )

    replacement <- fixture$store$get("handoff-1")
    expect_identical(replacement@bundled_tables, "sales")
    expect_false(identical(replacement@bundle_id, old_bundle@bundle_id))
    expect_null(fixture$bundle_store$get(old_bundle@bundle_id))
    new_bundle <- fixture$bundle_store$get(replacement@bundle_id)
    expect_identical(names(new_bundle@bundled_files), "sales.csv")
  })

  it("corrects oversized referenced data during revision using every schema", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    orders <- new_fake_handoff_data_source("orders", "PostgreSQL")
    journal <- new_handoff_event_journal()
    chat <- new_recording_handoff_chat(
      stream_results = list(
        new_transaction_handoff_result(),
        new_transaction_handoff_result(source = "print('corrected')")
      ),
      journal = journal
    )
    view <- new_recording_handoff_view(journal = journal)
    store <- new_recording_handoff_store(journal)
    executor <- new_recording_handoff_executor(list(
      sales = "SCHEMA sales amount DOUBLE",
      orders = "SCHEMA orders id INTEGER"
    ))
    orchestrator <- HandoffOrchestrator$new(
      chat = chat$chat,
      data_sources = list(sales = sales$source, orders = orders),
      executor = executor,
      view = view,
      store = store,
      bundle_store = HandoffBundleStore$new(),
      max_bundle_bytes = 1
    )
    old <- new_revision_handoff_state(bundled_tables = "sales")
    store$remember(old)

    sync_promise(orchestrator$revise("handoff-1", "Make it smaller."))

    replacement <- store$get("handoff-1")
    expect_identical(replacement@source, "print('corrected')")
    expect_identical(replacement@bundled_tables, character())
    expect_null(replacement@bundle_id)
    expect_identical(
      vapply(executor$calls, `[[`, character(1), "table_name"),
      c("sales", "orders")
    )
    stream_events <- Filter(
      \(event) identical(event$action, "stream"),
      journal$events
    )
    expect_match(
      stream_events[[2]]$system_prompt,
      "SCHEMA sales",
      fixed = TRUE
    )
    expect_match(
      stream_events[[2]]$system_prompt,
      "SCHEMA orders",
      fixed = TRUE
    )
  })

  it("preserves the current handoff when correction fails during revision", {
    skip_if_no_dataframe_engine()
    sales <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    fixture <- new_transaction_orchestrator(
      list(
        new_transaction_handoff_result(),
        new_transaction_handoff_result(
          source = "print('corrected')",
          referenced_tables = character()
        )
      ),
      data_sources = list(sales = sales$source),
      max_bundle_bytes = 1
    )
    old_bundle <- fixture$bundle_store$stage(
      list("sales.csv" = charToRaw("old"))
    )
    old <- new_revision_handoff_state(
      bundle_id = old_bundle@bundle_id,
      bundled_tables = "sales"
    )
    fixture$store$remember(old)

    expect_snapshot(
      error = TRUE,
      sync_promise(
        fixture$orchestrator$revise("handoff-1", "Make it smaller.")
      )
    )

    expect_identical(fixture$store$get("handoff-1"), old)
    expect_identical(
      fixture$bundle_store$get(old_bundle@bundle_id),
      old_bundle
    )
  })
})

describe("HandoffOrchestrator$show()", {
  it("shows stored handoffs and ignores stale IDs", {
    fixture <- new_transaction_orchestrator(
      list(new_transaction_handoff_result())
    )
    sync_promise(
      fixture$orchestrator$generate(
        transaction_request(),
        "",
        "handoff-1"
      )
    )
    fixture$view$events <- list()

    expect_identical(fixture$orchestrator$show("missing"), FALSE)
    expect_identical(fixture$orchestrator$show("handoff-1"), TRUE)

    expect_length(fixture$view$events, 1L)
    expect_identical(
      fixture$view$events[[1]]$download_available,
      TRUE
    )
  })
})

describe("HandoffOrchestrator$build_download()", {
  it("returns NULL for an unknown handoff ID", {
    fixture <- new_transaction_orchestrator(list())

    expect_null(fixture$orchestrator$build_download("missing"))
  })

  it("builds a source and README ZIP when no data is referenced or bundled", {
    fixture <- new_transaction_orchestrator(list())
    fixture$store$remember(
      new_revision_handoff_state("handoff-1", source = "SELECT 1")
    )

    zip_bytes <- fixture$orchestrator$build_download("handoff-1")

    zip_path <- withr::local_tempfile(fileext = ".zip")
    writeBin(zip_bytes, zip_path)
    expect_setequal(
      zip::zip_list(zip_path)$filename,
      c("handoff.qmd", "README.md")
    )
  })

  it("adds bundled CSVs when a snapshot bundle is present", {
    fixture <- new_transaction_orchestrator(list())
    bundle <- fixture$bundle_store$stage(
      list("sales.csv" = charToRaw("amount\n10\n"))
    )
    fixture$store$remember(
      new_revision_handoff_state(
        "handoff-1",
        bundle_id = bundle@bundle_id,
        bundled_tables = "sales"
      )
    )

    zip_bytes <- fixture$orchestrator$build_download("handoff-1")

    zip_path <- withr::local_tempfile(fileext = ".zip")
    writeBin(zip_bytes, zip_path)
    expect_setequal(
      zip::zip_list(zip_path)$filename,
      c("handoff.qmd", "README.md", "sales.csv")
    )
  })

  it("reports the snapshot as unavailable when bundled tables have no bundle ID", {
    fixture <- new_transaction_orchestrator(list())
    fixture$store$remember(
      new_revision_handoff_state("handoff-1", bundled_tables = "sales")
    )

    expect_snapshot(
      error = TRUE,
      fixture$orchestrator$build_download("handoff-1")
    )
  })

  it("reports the snapshot as unavailable when the bundle ID is missing from the store", {
    fixture <- new_transaction_orchestrator(list())
    fixture$store$remember(
      new_revision_handoff_state(
        "handoff-1",
        bundle_id = "missing-bundle",
        bundled_tables = "sales"
      )
    )

    expect_snapshot(
      error = TRUE,
      fixture$orchestrator$build_download("handoff-1")
    )
  })

  it("never calls live data sources to reconstruct a missing snapshot", {
    skip_if_no_dataframe_engine()
    fixture_data <- local_recording_data_frame_source(
      table_name = "sales",
      engine = "sqlite"
    )
    store <- HandoffStore$new()
    orchestrator <- HandoffOrchestrator$new(
      chat = new_recording_handoff_chat()$chat,
      data_sources = list(sales = fixture_data$source),
      executor = new_recording_handoff_executor(list(
        sales = "SCHEMA sales amount DOUBLE"
      )),
      view = new_recording_handoff_view(),
      store = store
    )
    store$remember(
      new_revision_handoff_state("handoff-1", bundled_tables = "sales")
    )

    expect_error(orchestrator$build_download("handoff-1"))
    expect_identical(fixture_data$state$get_data_calls, 0L)
  })
})
