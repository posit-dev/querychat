new_server_chat_module <- function(
  status = "idle",
  history_save_result = TRUE,
  history_save_error = NULL
) {
  chat <- mock_chat_server_result(structure(list(), class = "MockChat"))
  chat$status_value <- status
  chat$history_saves <- 0L
  chat$on_history_save <- NULL
  chat$history_save_callbacks <- list()
  chat$history_restore_callbacks <- list()
  chat$history$on_save <- function(fn) {
    chat$history_save_callbacks <- c(
      chat$history_save_callbacks,
      list(fn)
    )
    invisible(fn)
  }
  chat$history$on_restore <- function(fn) {
    chat$history_restore_callbacks <- c(
      chat$history_restore_callbacks,
      list(fn)
    )
    invisible(fn)
  }
  chat$run_history_save <- function(values) {
    for (callback in chat$history_save_callbacks) {
      values <- callback(values)
    }
    values
  }
  chat$run_history_restore <- function(values) {
    for (callback in chat$history_restore_callbacks) {
      callback(values)
    }
    invisible(NULL)
  }
  chat$history$save <- function() {
    chat$history_saves <- chat$history_saves + 1L
    if (!is.null(chat$on_history_save)) {
      chat$on_history_save()
    }
    if (!is.null(history_save_error)) {
      stop(history_save_error)
    }
    history_save_result
  }
  chat
}

new_server_orchestrator <- function(
  items = list(),
  recommendation = HandoffRecommendation(
    selected_ids = character(),
    format_id = "quarto-dashboard"
  ),
  recommendation_error = NULL,
  recommendation_promise = NULL,
  generation_error = NULL,
  generation_promise = NULL,
  revision_error = NULL,
  revision_promise = NULL,
  stored_ids = character(),
  download_bytes = NULL
) {
  orchestrator <- new.env(parent = emptyenv())
  orchestrator$calls <- list()
  orchestrator$items <- items
  orchestrator$stored_ids <- stored_ids
  orchestrator$view <- NULL

  record <- function(action, ...) {
    orchestrator$calls[[length(orchestrator$calls) + 1L]] <- list(
      action = action,
      ...
    )
  }
  orchestrator$open_modal <- function() {
    record("open_modal")
    orchestrator$view$show_modal(items)
    items
  }
  orchestrator$recommend <- function(current_items) {
    record("recommend", items = current_items)
    if (!is.null(recommendation_promise)) {
      return(recommendation_promise)
    }
    if (!is.null(recommendation_error)) {
      return(promises::promise_reject(recommendation_error))
    }
    promises::promise_resolve(recommendation)
  }
  orchestrator$generate <- function(request, directions, handoff_id) {
    record(
      "generate",
      request = request,
      directions = directions,
      handoff_id = handoff_id
    )
    if (!is.null(generation_promise)) {
      return(generation_promise)
    }
    if (!is.null(generation_error)) {
      return(promises::promise_reject(generation_error))
    }
    orchestrator$stored_ids <- c(orchestrator$stored_ids, handoff_id)
    promises::promise_resolve(NULL)
  }
  orchestrator$show <- function(handoff_id) {
    record("show", handoff_id = handoff_id)
    handoff_id %in% orchestrator$stored_ids
  }
  orchestrator$build_download <- function(handoff_id) {
    record("build_download", handoff_id = handoff_id)
    download_bytes
  }
  orchestrator$revise <- function(handoff_id, instructions) {
    record(
      "revise",
      handoff_id = handoff_id,
      instructions = instructions
    )
    if (!is.null(revision_promise)) {
      return(revision_promise)
    }
    if (!is.null(revision_error)) {
      return(promises::promise_reject(revision_error))
    }
    revised <- !is.null(handoff_id) && nzchar(trimws(instructions))
    promises::promise_resolve(revised)
  }
  orchestrator
}

new_handoff_deferred <- function() {
  deferred <- new.env(parent = emptyenv())
  deferred$promise <- promises::promise(function(resolve, reject) {
    deferred$resolve <- resolve
    deferred$reject <- reject
  })
  deferred
}

local_server_orchestrator <- function(
  orchestrator,
  view = new_recording_handoff_view(),
  env = parent.frame()
) {
  orchestrator$view <- view
  testthat::local_mocked_bindings(
    HandoffView = list(new = function(...) view),
    HandoffOrchestrator = list(new = function(...) orchestrator),
    .package = "querychat",
    .env = env
  )
  view
}

new_handoff_server_function <- function(
  chat_module,
  bookmark_callbacks = NULL
) {
  function(input, output, session) {
    if (!is.null(bookmark_callbacks)) {
      session$onBookmark <- function(fn) {
        bookmark_callbacks$save <- c(
          bookmark_callbacks$save,
          list(fn)
        )
        invisible(fn)
      }
      session$onRestore <- function(fn) {
        bookmark_callbacks$restore <- c(
          bookmark_callbacks$restore,
          list(fn)
        )
        invisible(fn)
      }
    }
    handoff_server(
      input = input,
      output = output,
      session = session,
      chat = structure(list(), class = "MockChat"),
      data_sources = list(),
      executor = new.env(parent = emptyenv()),
      chat_module = chat_module
    )
  }
}

get_registered_handoff_download <- function(
  session,
  name = "handoff_download"
) {
  session$flushReact()
  generators <- session$.__enclos_env__$private$file_generators
  generators$get(session$ns(name))
}

flush_handoff_server <- function(session, iterations = 20L) {
  for (i in seq_len(iterations)) {
    session$flushReact()
    later::run_now(0.01)
  }
}

local_handoff_notifications <- function(env = parent.frame()) {
  notifications <- new.env(parent = emptyenv())
  notifications$values <- list()
  testthat::local_mocked_bindings(
    showNotification = function(
      ui,
      action = NULL,
      duration = 5,
      closeButton = TRUE,
      id = NULL,
      type = "default",
      session = shiny::getDefaultReactiveDomain()
    ) {
      notifications$values[[length(notifications$values) + 1L]] <- list(
        ui = ui,
        duration = duration,
        type = type
      )
      "notification-id"
    },
    .package = "shiny",
    .env = env
  )
  notifications
}

new_server_snapshot_state <- function(
  handoff_id = "handoff-1",
  source = "source",
  bundled_tables = character(),
  bundle_id = NULL
) {
  HandoffState(
    handoff_id = handoff_id,
    handoff_type = resolve_handoff_type("quarto-dashboard", "r"),
    system_prompt = "Saved system prompt",
    source = source,
    turns = list(ellmer::AssistantTurn("Saved handoff")),
    summary = "Saved summary",
    run_instructions = "Run the handoff.",
    referenced_tables = "sales",
    bundled_tables = bundled_tables,
    bundle_id = bundle_id,
    data_instructions = "Use the saved data snapshot."
  )
}

new_server_snapshot_orchestrator <- function(
  states = list(),
  bundle_store = HandoffBundleStore$new(),
  data_sources = list()
) {
  store <- HandoffStore$new()
  invisible(lapply(states, store$remember))
  view <- new_recording_handoff_view()
  orchestrator <- HandoffOrchestrator$new(
    chat = structure(list(), class = "MockChat"),
    data_sources = data_sources,
    executor = new.env(parent = emptyenv()),
    view = view,
    store = store,
    bundle_store = bundle_store
  )
  list(
    orchestrator = orchestrator,
    store = store,
    view = view,
    bundle_store = bundle_store
  )
}

serialize_handoff_test_value <- function(value) {
  jsonlite::serializeJSON(value, digits = NA)
}

local_server_snapshot_orchestrator <- function(
  fixture,
  env = parent.frame()
) {
  testthat::local_mocked_bindings(
    HandoffView = list(new = function(...) fixture$view),
    HandoffOrchestrator = list(new = function(...) fixture$orchestrator),
    .package = "querychat",
    .env = env
  )
  invisible(fixture)
}

describe("build_handoff_snapshot()", {
  it("serializes one exact versioned envelope without bundle bytes", {
    bundle_store <- HandoffBundleStore$new()
    bundle <- bundle_store$stage(
      list("sales.csv" = charToRaw("private data"))
    )
    state <- new_server_snapshot_state(
      bundled_tables = "sales",
      bundle_id = bundle@bundle_id
    )
    fixture <- new_server_snapshot_orchestrator(
      states = list(state),
      bundle_store = bundle_store
    )

    snapshot <- build_handoff_snapshot(fixture$orchestrator)
    decoded <- jsonlite::unserializeJSON(snapshot)

    expect_type(snapshot, "character")
    expect_length(snapshot, 1L)
    expect_named(decoded, c("version", "states"))
    expect_identical(decoded$version, 1L)
    expect_length(decoded$states, 1L)
    expect_identical(
      handoff_state_from_record(decoded$states[[1]]),
      state
    )
    expect_no_match(snapshot, "private data", fixed = TRUE)
  })

  it("serializes an empty state list", {
    fixture <- new_server_snapshot_orchestrator()

    decoded <- jsonlite::unserializeJSON(
      build_handoff_snapshot(fixture$orchestrator)
    )

    expect_identical(decoded, list(version = 1L, states = list()))
  })
})

describe("apply_handoff_snapshot()", {
  it("replaces the store, clears the active ID, and closes the panel", {
    saved <- new_server_snapshot_state("restored", source = "restored")
    source_fixture <- new_server_snapshot_orchestrator(list(saved))
    target_fixture <- new_server_snapshot_orchestrator(
      list(new_server_snapshot_state("old"))
    )
    active_handoff_id <- shiny::reactiveVal("old")

    apply_handoff_snapshot(
      target_fixture$orchestrator,
      build_handoff_snapshot(source_fixture$orchestrator),
      active_handoff_id
    )

    expect_identical(target_fixture$store$values(), list(saved))
    expect_null(shiny::isolate(active_handoff_id()))
    expect_identical(
      target_fixture$view$events,
      list(list(action = "set_panel_open", open = FALSE))
    )
  })

  it("treats a missing key as an empty snapshot", {
    fixture <- new_server_snapshot_orchestrator(
      list(new_server_snapshot_state())
    )
    active_handoff_id <- shiny::reactiveVal("handoff-1")

    apply_handoff_snapshot(
      fixture$orchestrator,
      NULL,
      active_handoff_id
    )

    expect_length(fixture$store$values(), 0L)
    expect_null(shiny::isolate(active_handoff_id()))
    expect_identical(
      fixture$view$events,
      list(list(action = "set_panel_open", open = FALSE))
    )
  })

  it("rejects malformed and unsupported envelopes without partial restore", {
    old <- new_server_snapshot_state("old")
    fixture <- new_server_snapshot_orchestrator(list(old))
    active_handoff_id <- shiny::reactiveVal("old")
    malformed_states <- serialize_handoff_test_value(list(
      version = 1L,
      states = "not a list"
    ))
    unsupported <- serialize_handoff_test_value(list(
      version = 2L,
      states = list()
    ))
    extra_field <- serialize_handoff_test_value(list(
      version = 1L,
      states = list(),
      bundles = list()
    ))

    expect_snapshot(
      error = TRUE,
      apply_handoff_snapshot(
        fixture$orchestrator,
        "{not json",
        active_handoff_id
      )
    )
    expect_snapshot(
      error = TRUE,
      apply_handoff_snapshot(
        fixture$orchestrator,
        malformed_states,
        active_handoff_id
      )
    )
    expect_snapshot(
      error = TRUE,
      apply_handoff_snapshot(
        fixture$orchestrator,
        unsupported,
        active_handoff_id
      )
    )
    expect_snapshot(
      error = TRUE,
      apply_handoff_snapshot(
        fixture$orchestrator,
        extra_field,
        active_handoff_id
      )
    )

    expect_identical(fixture$store$values(), list(old))
    expect_identical(shiny::isolate(active_handoff_id()), "old")
    expect_length(fixture$view$events, 0L)
  })

  it("restores source without materializing missing bundles", {
    calls <- new.env(parent = emptyenv())
    calls$get_data <- 0L
    data_source <- new.env(parent = emptyenv())
    data_source$get_data <- function() {
      calls$get_data <- calls$get_data + 1L
      stop("get_data() must not be called")
    }
    state <- new_server_snapshot_state(
      source = "restored source",
      bundled_tables = "sales",
      bundle_id = "missing-bundle"
    )
    source_fixture <- new_server_snapshot_orchestrator(list(state))
    target_fixture <- new_server_snapshot_orchestrator(
      data_sources = list(sales = data_source)
    )

    apply_handoff_snapshot(
      target_fixture$orchestrator,
      build_handoff_snapshot(source_fixture$orchestrator),
      shiny::reactiveVal(NULL)
    )
    shown <- target_fixture$orchestrator$show("handoff-1")

    expect_identical(shown, TRUE)
    expect_identical(
      tail(target_fixture$view$events, 1L)[[1]],
      list(
        action = "show_handoff",
        state = state,
        download_available = FALSE
      )
    )
    expect_identical(calls$get_data, 0L)
  })
})

describe("handoff_server()", {
  it("registers composable Shiny bookmark callbacks", {
    state <- new_server_snapshot_state()
    fixture <- new_server_snapshot_orchestrator(list(state))
    local_server_snapshot_orchestrator(fixture)
    chat_module <- new_server_chat_module()
    callbacks <- new.env(parent = emptyenv())
    callbacks$save <- list()
    callbacks$restore <- list()

    shiny::testServer(
      new_handoff_server_function(chat_module, callbacks),
      {
        expect_length(callbacks$save, 1L)
        expect_length(callbacks$restore, 1L)

        bookmark_state <- new.env(parent = emptyenv())
        bookmark_state$values <- list(unrelated = "kept")
        callbacks$save[[1]](bookmark_state)
        expect_identical(bookmark_state$values$unrelated, "kept")
        expect_type(bookmark_state$values$querychat_handoffs, "character")

        fixture$orchestrator$restore_snapshot(list())
        callbacks$restore[[1]](bookmark_state)
        expect_identical(fixture$store$values(), list(state))
      }
    )
  })

  it("composes history round-trips for tables, visualizations, and handoffs", {
    state <- new_server_snapshot_state()
    fixture <- new_server_snapshot_orchestrator(list(state))
    local_server_snapshot_orchestrator(fixture)
    chat_module <- new_server_chat_module()
    restored <- new.env(parent = emptyenv())
    restored$tables <- NULL
    restored$visualizations <- NULL

    shiny::testServer(new_handoff_server_function(chat_module), {
      chat_module$history$on_save(function(values) {
        utils::modifyList(
          values,
          list(
            querychat_tables = list(
              sales = list(
                sql = "SELECT * FROM sales",
                title = "Sales"
              )
            ),
            querychat_viz_widgets = list(list(
              widget_id = "querychat_viz_1",
              ggsql = "SELECT 1 VISUALISE 1 AS x DRAW point"
            ))
          )
        )
      })
      chat_module$history$on_restore(function(values) {
        restored$tables <- values$querychat_tables
        restored$visualizations <- values$querychat_viz_widgets
      })

      values <- chat_module$run_history_save(list(unrelated = "kept"))

      expect_identical(values$unrelated, "kept")
      expect_type(values$querychat_handoffs, "character")
      expect_identical(
        values$querychat_tables$sales$sql,
        "SELECT * FROM sales"
      )
      expect_identical(
        values$querychat_viz_widgets[[1]]$widget_id,
        "querychat_viz_1"
      )

      fixture$orchestrator$restore_snapshot(list())
      chat_module$run_history_restore(values)

      expect_identical(fixture$store$values(), list(state))
      expect_identical(restored$tables, values$querychat_tables)
      expect_identical(
        restored$visualizations,
        values$querychat_viz_widgets
      )
    })
  })

  it("treats a legacy handoff key as a missing snapshot", {
    current <- new_server_snapshot_state("current")
    legacy <- new_server_snapshot_state("legacy")
    fixture <- new_server_snapshot_orchestrator(list(current))
    legacy_fixture <- new_server_snapshot_orchestrator(list(legacy))
    local_server_snapshot_orchestrator(fixture)
    chat_module <- new_server_chat_module()
    values <- list(
      querychat_handoffs_legacy = build_handoff_snapshot(
        legacy_fixture$orchestrator
      )
    )

    shiny::testServer(new_handoff_server_function(chat_module), {
      chat_module$run_history_restore(values)

      expect_length(fixture$store$values(), 0L)
      expect_identical(
        fixture$view$events,
        list(list(action = "set_panel_open", open = FALSE))
      )
    })
  })

  it("registers the approved slash command without echo", {
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator()
    local_server_orchestrator(orchestrator)

    shiny::testServer(new_handoff_server_function(chat_module), {
      command <- chat_module$commands$handoff
      expect_identical(command$name, "handoff")
      expect_identical(
        command$description,
        paste(
          "Prepare a shareable handoff document or webapp",
          "using the current chat context."
        )
      )
      expect_identical(command$echo, FALSE)
      expect_true(is.function(command$handler))
    })
  })

  it("registers a handoff.zip download that streams the active handoff", {
    orchestrator <- new_server_orchestrator(
      stored_ids = "handoff-1",
      download_bytes = charToRaw("archive-bytes")
    )
    local_server_orchestrator(orchestrator)
    chat_module <- new_server_chat_module()

    shiny::testServer(new_handoff_server_function(chat_module), {
      download <- get_registered_handoff_download(session)
      expect_identical(download$filename(), "handoff.zip")

      session$setInputs(handoff_open = "handoff-1")
      flush_handoff_server(session)

      out_file <- withr::local_tempfile()
      download$content(out_file)

      expect_identical(
        readBin(out_file, "raw", file.info(out_file)$size),
        charToRaw("archive-bytes")
      )
      expect_identical(
        orchestrator$calls[[length(orchestrator$calls)]],
        list(action = "build_download", handoff_id = "handoff-1")
      )
    })
  })

  it("writes no file when there is no active handoff to download", {
    orchestrator <- new_server_orchestrator(download_bytes = NULL)
    local_server_orchestrator(orchestrator)
    chat_module <- new_server_chat_module()

    shiny::testServer(new_handoff_server_function(chat_module), {
      download <- get_registered_handoff_download(session)

      out_file <- withr::local_tempfile()
      download$content(out_file)

      expect_false(file.exists(out_file))
      expect_identical(
        orchestrator$calls[[length(orchestrator$calls)]],
        list(action = "build_download", handoff_id = NULL)
      )
    })
  })

  it("appends a wait message while the main chat is streaming", {
    chat_module <- new_server_chat_module(status = "streaming")
    orchestrator <- new_server_orchestrator()
    view <- local_server_orchestrator(orchestrator)

    shiny::testServer(new_handoff_server_function(chat_module), {
      chat_module$commands$handoff$handler()
      flush_handoff_server(session)

      expect_identical(
        chat_module$appended[[1]]$response,
        paste(
          "Please wait for the current response to finish before",
          "preparing a handoff."
        )
      )
      expect_length(orchestrator$calls, 0L)
      expect_length(view$events, 0L)
    })
  })

  it("opens the modal and recommends only for a nonempty gallery", {
    item <- HandoffQueryItem(
      id = "query-0",
      title = "Sales",
      sql = "SELECT * FROM sales"
    )
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator(items = list(item))
    view <- local_server_orchestrator(orchestrator)

    shiny::testServer(new_handoff_server_function(chat_module), {
      chat_module$commands$handoff$handler()
      flush_handoff_server(session)

      expect_identical(
        vapply(orchestrator$calls, `[[`, character(1), "action"),
        c("open_modal", "recommend")
      )
      expect_identical(
        vapply(view$events, `[[`, character(1), "action"),
        c("show_modal", "show_recommendation")
      )
    })

    empty_orchestrator <- new_server_orchestrator(items = list())
    empty_view <- local_server_orchestrator(empty_orchestrator)
    empty_chat <- new_server_chat_module()

    shiny::testServer(new_handoff_server_function(empty_chat), {
      empty_chat$commands$handoff$handler()
      flush_handoff_server(session)

      expect_identical(
        vapply(
          empty_orchestrator$calls,
          `[[`,
          character(1),
          "action"
        ),
        "open_modal"
      )
      expect_identical(
        vapply(empty_view$events, `[[`, character(1), "action"),
        "show_modal"
      )
    })
  })

  it("notifies and unlocks manual selection after recommendation failure", {
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator(
      items = list(HandoffQueryItem(
        id = "query-0",
        title = "Sales",
        sql = "SELECT * FROM sales"
      )),
      recommendation_error = simpleError("recommend failed")
    )
    view <- local_server_orchestrator(orchestrator)
    notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(chat_module), {
      chat_module$commands$handoff$handler()
      expect_snapshot(flush_handoff_server(session))

      expect_length(notifications$values, 1L)
      expect_match(
        as.character(notifications$values[[1]]$ui),
        "recommend failed",
        fixed = TRUE
      )
      expect_identical(notifications$values[[1]]$type, "error")
      expect_identical(
        tail(view$events, 1L)[[1]],
        list(
          action = "show_recommendation_error",
          error = "recommend failed"
        )
      )
    })
  })

  it("ignores a second modal request while recommendation is running", {
    item <- HandoffQueryItem(
      id = "query-0",
      title = "Sales",
      sql = "SELECT * FROM sales"
    )
    recommendation <- HandoffRecommendation(
      selected_ids = "query-0",
      format_id = "quarto-dashboard"
    )
    deferred <- new_handoff_deferred()
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator(
      items = list(item),
      recommendation_promise = deferred$promise
    )
    view <- local_server_orchestrator(orchestrator)
    notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(chat_module), {
      chat_module$commands$handoff$handler()
      flush_handoff_server(session)
      chat_module$commands$handoff$handler()
      flush_handoff_server(session)

      expect_identical(
        vapply(orchestrator$calls, `[[`, character(1), "action"),
        c("open_modal", "recommend")
      )
      expect_identical(
        vapply(view$events, `[[`, character(1), "action"),
        "show_modal"
      )
      expect_length(notifications$values, 1L)
      expect_match(
        as.character(notifications$values[[1]]$ui),
        "recommendation is already in progress",
        fixed = TRUE
      )

      deferred$resolve(recommendation)
      flush_handoff_server(session)

      expect_identical(
        vapply(view$events, `[[`, character(1), "action"),
        c("show_modal", "show_recommendation")
      )
      expect_identical(view$events[[2]]$value, recommendation)
    })
  })

  it("notifies without generation for malformed and blank Other payloads", {
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator()
    local_server_orchestrator(orchestrator)
    notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(handoff_generate = list(selected_ids = 1))
      flush_handoff_server(session)
      session$setInputs(
        handoff_generate = list(
          selected_ids = character(),
          type = "other",
          language = "r",
          freeform = " "
        )
      )
      flush_handoff_server(session)

      expect_length(notifications$values, 2L)
      expect_match(
        as.character(notifications$values[[2]]$ui),
        "format name",
        fixed = TRUE
      )
      expect_length(
        Filter(
          \(call) identical(call$action, "generate"),
          orchestrator$calls
        ),
        0L
      )
    })
  })

  it("opens a new panel before generation and closes failed work", {
    chat_module <- new_server_chat_module()
    journal <- new_handoff_event_journal()
    view <- new_recording_handoff_view(journal = journal)
    orchestrator <- new_server_orchestrator(
      generation_error = simpleError("generation failed")
    )
    original_generate <- orchestrator$generate
    orchestrator$generate <- function(request, directions, handoff_id) {
      append_handoff_journal(
        journal,
        list(action = "generate", handoff_id = handoff_id)
      )
      original_generate(request, directions, handoff_id)
    }
    local_server_orchestrator(orchestrator, view)
    notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(
        handoff_generate = list(
          selected_ids = character(),
          type = "quarto-dashboard",
          language = "r",
          freeform = ""
        )
      )
      expect_snapshot(flush_handoff_server(session))

      actions <- vapply(journal$events, `[[`, character(1), "action")
      expect_identical(
        actions,
        c("set_panel_open", "generate", "set_panel_open")
      )
      expect_identical(journal$events[[1]]$open, TRUE)
      expect_identical(journal$events[[3]]$open, FALSE)
      expect_match(
        as.character(notifications$values[[1]]$ui),
        "generation failed",
        fixed = TRUE
      )
      generate_call <- Filter(
        \(call) identical(call$action, "generate"),
        orchestrator$calls
      )[[1]]
      expect_match(
        generate_call$handoff_id,
        "^[a-f0-9]{32}$"
      )
    })
  })

  it("rejects a second generation while the first is running", {
    deferred <- new_handoff_deferred()
    chat_module <- new_server_chat_module()
    journal <- new_handoff_event_journal()
    view <- new_recording_handoff_view(journal = journal)
    orchestrator <- new_server_orchestrator(
      generation_promise = deferred$promise
    )
    local_server_orchestrator(orchestrator, view)
    notifications <- local_handoff_notifications()
    payload <- list(
      selected_ids = character(),
      type = "quarto-dashboard",
      language = "r",
      freeform = ""
    )

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(handoff_generate = payload)
      flush_handoff_server(session)
      first_call <- Filter(
        \(call) identical(call$action, "generate"),
        orchestrator$calls
      )[[1]]

      session$setInputs(handoff_generate = payload)
      flush_handoff_server(session)

      expect_length(
        Filter(
          \(call) identical(call$action, "generate"),
          orchestrator$calls
        ),
        1L
      )
      expect_identical(
        vapply(view$events, `[[`, character(1), "action"),
        "set_panel_open"
      )
      expect_length(notifications$values, 1L)
      expect_match(
        as.character(notifications$values[[1]]$ui),
        "already being generated",
        fixed = TRUE
      )

      deferred$reject(simpleError("first generation failed"))
      expect_snapshot(flush_handoff_server(session))

      show_calls <- Filter(
        \(call) identical(call$action, "show"),
        orchestrator$calls
      )
      expect_length(show_calls, 1L)
      expect_identical(
        show_calls[[1]]$handoff_id,
        first_call$handoff_id
      )
      expect_identical(
        tail(view$events, 1L)[[1]],
        list(action = "set_panel_open", open = FALSE)
      )
    })
  })

  it("ignores stale handoff pill IDs", {
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator(stored_ids = "known")
    view <- local_server_orchestrator(orchestrator)

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(handoff_open = "stale")
      flush_handoff_server(session)

      expect_identical(
        orchestrator$calls[[1]],
        list(action = "show", handoff_id = "stale")
      )
      expect_length(view$events, 0L)
    })
  })

  it("saves history after successful generation commits", {
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator()
    local_server_orchestrator(orchestrator)
    chat_module$on_history_save <- function() {
      expect_length(orchestrator$stored_ids, 1L)
    }

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(
        handoff_generate = list(
          selected_ids = character(),
          type = "quarto-dashboard",
          language = "r",
          freeform = ""
        )
      )
      flush_handoff_server(session)

      expect_identical(chat_module$history_saves, 1L)
      expect_length(orchestrator$stored_ids, 1L)
    })
  })

  it("allows a FALSE history save after generation", {
    chat_module <- new_server_chat_module(history_save_result = FALSE)
    orchestrator <- new_server_orchestrator()
    local_server_orchestrator(orchestrator)
    notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(
        handoff_generate = list(
          selected_ids = character(),
          type = "quarto-dashboard",
          language = "r",
          freeform = ""
        )
      )
      flush_handoff_server(session)

      expect_identical(chat_module$history_saves, 1L)
      expect_length(orchestrator$stored_ids, 1L)
      expect_length(notifications$values, 0L)
    })
  })

  it("keeps committed generation visible when history save fails", {
    chat_module <- new_server_chat_module(
      history_save_error = simpleError("history save failed")
    )
    orchestrator <- new_server_orchestrator()
    view <- local_server_orchestrator(orchestrator)
    notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(
        handoff_generate = list(
          selected_ids = character(),
          type = "quarto-dashboard",
          language = "r",
          freeform = ""
        )
      )
      expect_snapshot(flush_handoff_server(session))

      expect_identical(chat_module$history_saves, 1L)
      expect_length(orchestrator$stored_ids, 1L)
      show_call <- Filter(
        \(call) identical(call$action, "show"),
        orchestrator$calls
      )[[1]]
      expect_identical(show_call$handoff_id, orchestrator$stored_ids[[1]])
      expect_identical(
        vapply(view$events, `[[`, character(1), "action"),
        "set_panel_open"
      )
      expect_match(
        as.character(notifications$values[[1]]$ui),
        "history save failed",
        fixed = TRUE
      )
    })
  })

  it("revises the active handoff and saves only after commit", {
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator(stored_ids = "known")
    local_server_orchestrator(orchestrator)
    chat_module$on_history_save <- function() {
      expect_identical(
        tail(orchestrator$calls, 1L)[[1]]$action,
        "revise"
      )
    }

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(handoff_open = "known")
      flush_handoff_server(session)
      session$setInputs(handoff_revise_text = "Make it smaller.")
      flush_handoff_server(session)

      revise_call <- Filter(
        \(call) identical(call$action, "revise"),
        orchestrator$calls
      )[[1]]
      expect_identical(revise_call$handoff_id, "known")
      expect_identical(revise_call$instructions, "Make it smaller.")
      expect_identical(chat_module$history_saves, 1L)
    })
  })

  it("does not save history for no-op revisions", {
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator(stored_ids = "known")
    local_server_orchestrator(orchestrator)

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(handoff_revise_text = "No active handoff.")
      flush_handoff_server(session)
      session$setInputs(handoff_open = "known")
      flush_handoff_server(session)
      session$setInputs(handoff_revise_text = " ")
      flush_handoff_server(session)

      revise_calls <- Filter(
        \(call) identical(call$action, "revise"),
        orchestrator$calls
      )
      expect_length(revise_calls, 2L)
      expect_null(revise_calls[[1]]$handoff_id)
      expect_identical(revise_calls[[2]]$handoff_id, "known")
      expect_identical(chat_module$history_saves, 0L)
    })
  })

  it("allows FALSE revision saves and preserves commits on save errors", {
    false_chat <- new_server_chat_module(history_save_result = FALSE)
    false_orchestrator <- new_server_orchestrator(stored_ids = "known")
    local_server_orchestrator(false_orchestrator)
    false_notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(false_chat), {
      session$setInputs(handoff_open = "known")
      flush_handoff_server(session)
      session$setInputs(handoff_revise_text = "Revise once.")
      flush_handoff_server(session)

      expect_identical(false_chat$history_saves, 1L)
      expect_length(false_notifications$values, 0L)
    })

    error_chat <- new_server_chat_module(
      history_save_error = simpleError("revision save failed")
    )
    error_orchestrator <- new_server_orchestrator(stored_ids = "known")
    view <- local_server_orchestrator(error_orchestrator)
    notifications <- local_handoff_notifications()

    shiny::testServer(new_handoff_server_function(error_chat), {
      session$setInputs(handoff_open = "known")
      flush_handoff_server(session)
      session$setInputs(handoff_revise_text = "Revise twice.")
      expect_snapshot(flush_handoff_server(session))

      expect_identical(error_chat$history_saves, 1L)
      expect_length(
        Filter(
          \(call) identical(call$action, "revise"),
          error_orchestrator$calls
        ),
        1L
      )
      expect_identical(
        tail(view$events, 1L)[[1]],
        list(action = "set_panel_open", open = TRUE)
      )
      expect_match(
        as.character(notifications$values[[1]]$ui),
        "revision save failed",
        fixed = TRUE
      )
    })
  })

  it("blocks switching while tasks run and keeps invocation-bound IDs", {
    revision <- new_handoff_deferred()
    chat_module <- new_server_chat_module()
    orchestrator <- new_server_orchestrator(
      revision_promise = revision$promise,
      stored_ids = c("first", "second")
    )
    view <- local_server_orchestrator(orchestrator)
    notifications <- local_handoff_notifications()
    payload <- list(
      selected_ids = character(),
      type = "quarto-dashboard",
      language = "r",
      freeform = ""
    )

    shiny::testServer(new_handoff_server_function(chat_module), {
      session$setInputs(handoff_open = "first")
      flush_handoff_server(session)
      session$setInputs(handoff_revise_text = "First revision.")
      flush_handoff_server(session)

      calls_before_switch <- length(orchestrator$calls)
      view_events_before_switch <- length(view$events)
      session$setInputs(handoff_open = "second")
      flush_handoff_server(session)

      expect_length(orchestrator$calls, calls_before_switch)
      expect_length(view$events, view_events_before_switch)
      expect_length(notifications$values, 1L)
      expect_identical(notifications$values[[1]]$type, "warning")

      session$setInputs(handoff_revise_text = "Second revision.")
      session$setInputs(handoff_generate = payload)
      flush_handoff_server(session)

      expect_length(
        Filter(
          \(call) identical(call$action, "revise"),
          orchestrator$calls
        ),
        1L
      )
      expect_length(
        Filter(
          \(call) identical(call$action, "generate"),
          orchestrator$calls
        ),
        0L
      )
      revise_call <- Filter(
        \(call) identical(call$action, "revise"),
        orchestrator$calls
      )[[1]]
      expect_identical(revise_call$handoff_id, "first")
      expect_gte(length(notifications$values), 2L)

      revision$resolve(TRUE)
      flush_handoff_server(session)

      expect_identical(chat_module$history_saves, 1L)
      expect_identical(revise_call$handoff_id, "first")

      session$setInputs(handoff_open = "first")
      flush_handoff_server(session)
      session$setInputs(handoff_open = "second")
      flush_handoff_server(session)

      show_calls <- Filter(
        \(call) identical(call$action, "show"),
        orchestrator$calls
      )
      expect_identical(
        vapply(show_calls, `[[`, character(1), "handoff_id"),
        c("first", "first", "second")
      )
      expect_identical(
        tail(view$events, 1L)[[1]],
        list(action = "set_panel_open", open = TRUE)
      )

      session$setInputs(handoff_revise_text = "Revision after switch.")
      flush_handoff_server(session)

      revise_calls <- Filter(
        \(call) identical(call$action, "revise"),
        orchestrator$calls
      )
      expect_identical(
        vapply(revise_calls, `[[`, character(1), "handoff_id"),
        c("first", "second")
      )
      expect_identical(chat_module$history_saves, 2L)
    })
  })
})
