build_handoff_snapshot <- function(orchestrator) {
  envelope <- list(
    version = 1L,
    states = lapply(
      orchestrator$snapshot(),
      handoff_state_record
    )
  )
  jsonlite::serializeJSON(envelope, digits = NA)
}

apply_handoff_snapshot <- function(
  orchestrator,
  value,
  active_handoff_id
) {
  states <- list()
  if (!is.null(value)) {
    if (
      !is.character(value) ||
        length(value) != 1L ||
        is.na(value)
    ) {
      cli::cli_abort(
        "Handoff snapshot must be a single serialized string."
      )
    }
    envelope <- jsonlite::unserializeJSON(value)
    check_plain_list(envelope, "Handoff snapshot", named = TRUE)
    check_exact_fields(
      envelope,
      c("version", "states"),
      "Handoff snapshot"
    )
    if (!identical(envelope$version, 1L)) {
      cli::cli_abort("Handoff snapshot version must be exactly 1.")
    }
    check_plain_list(
      envelope$states,
      "Handoff snapshot `states`",
      named = FALSE
    )
    states <- envelope$states
  }

  orchestrator$restore_snapshot(states)
  active_handoff_id(NULL)
  orchestrator$close_panel()
  invisible(NULL)
}

handoff_server <- function(
  input,
  output,
  session,
  chat,
  data_sources,
  executor,
  chat_module
) {
  view <- HandoffView$new(session, chat_module)
  orchestrator <- HandoffOrchestrator$new(
    chat = chat,
    data_sources = data_sources,
    executor = executor,
    view = view
  )
  active_handoff_id <- shiny::reactiveVal(
    NULL,
    label = "active_handoff_id"
  )
  save_handoffs <- function(values) {
    values$querychat_handoffs <- build_handoff_snapshot(orchestrator)
    values
  }
  restore_handoffs <- function(values) {
    apply_handoff_snapshot(
      orchestrator,
      values[["querychat_handoffs"]],
      active_handoff_id
    )
  }

  session$onBookmark(function(state) {
    state$values <- save_handoffs(state$values)
  })
  session$onRestore(function(state) {
    restore_handoffs(state$values)
  })
  chat_module$history$on_save(save_handoffs)
  chat_module$history$on_restore(restore_handoffs)

  task_handoff_id <- shiny::reactiveVal(
    NULL,
    label = "handoff_task_id"
  )
  task_operation <- shiny::reactiveVal(
    NULL,
    label = "handoff_task_operation"
  )

  recommendation_task <- shiny::ExtendedTask$new(function(items) {
    orchestrator$recommend(items)
  })
  handoff_task <- shiny::ExtendedTask$new(
    function(operation, handoff_id, value, directions) {
      task <- if (identical(operation, "generate")) {
        orchestrator$generate(value, directions, handoff_id)
      } else {
        orchestrator$revise(handoff_id, value)
      }
      promises::then(task, function(committed) {
        if (identical(operation, "revise") && identical(committed, FALSE)) {
          return(FALSE)
        }
        # The pinned shinychat history API is still in flux: the
        # `dev/querychat-pr311-history-save` branch's history object
        # exposes `on_save`/`on_restore` but no `save()` method. A missing
        # or failing history save must never mask a committed handoff by
        # rejecting this task.
        save_history <- chat_module$history$save
        if (is.function(save_history)) {
          tryCatch(
            save_history(),
            error = function(error) {
              shiny::showNotification(
                paste(
                  "The handoff was saved, but updating the chat",
                  "history failed:",
                  conditionMessage(error)
                ),
                type = "warning",
                session = session
              )
            }
          )
        }
        TRUE
      })
    }
  )

  open_handoff <- function() {
    status <- shiny::isolate(chat_module$status())
    if (status %in% c("running", "streaming")) {
      chat_module$append(
        paste(
          "Please wait for the current response to finish before",
          "preparing a handoff."
        )
      )
      return(invisible(NULL))
    }
    if (
      identical(
        shiny::isolate(recommendation_task$status()),
        "running"
      )
    ) {
      shiny::showNotification(
        "A handoff recommendation is already in progress.",
        type = "warning",
        session = session
      )
      return(invisible(NULL))
    }

    items <- orchestrator$open_modal()
    if (length(items) > 0L) {
      recommendation_task$invoke(items)
    }
    invisible(NULL)
  }

  chat_module$slash_command(
    "handoff",
    paste(
      "Prepare a shareable handoff document or webapp",
      "using the current chat context."
    ),
    open_handoff,
    echo = FALSE
  )

  output$handoff_download <- shiny::downloadHandler(
    filename = function() "handoff.zip",
    content = function(file) {
      data <- orchestrator$build_download(active_handoff_id())
      if (!is.null(data)) {
        writeBin(data, file)
      }
    }
  )

  shiny::observeEvent(
    recommendation_task$status(),
    label = "on_handoff_recommendation",
    ignoreInit = TRUE,
    {
      status <- recommendation_task$status()
      if (identical(status, "success")) {
        view$show_recommendation(recommendation_task$result())
      } else if (identical(status, "error")) {
        error_message <- tryCatch(
          {
            recommendation_task$result()
            "Unknown error"
          },
          error = function(error) conditionMessage(error)
        )
        shiny::showNotification(
          paste("Auto-recommend failed:", error_message),
          type = "error",
          duration = NULL,
          session = session
        )
        view$show_recommendation_error(error_message)
      }
    }
  )

  shiny::observeEvent(
    input$handoff_generate,
    label = "on_handoff_generate",
    {
      if (
        identical(
          shiny::isolate(handoff_task$status()),
          "running"
        )
      ) {
        shiny::showNotification(
          "A handoff is already being generated. Please wait for it to finish.",
          type = "warning",
          session = session
        )
        return()
      }

      request <- tryCatch(
        parse_handoff_generate_request(
          input$handoff_generate,
          names(handoff_registry())[[1]]
        ),
        error = function(error) {
          shiny::showNotification(
            conditionMessage(error),
            type = "error",
            duration = NULL,
            session = session
          )
          NULL
        }
      )
      if (is.null(request)) {
        return()
      }
      if (
        identical(request@type_id, "other") &&
          !nzchar(trimws(request@freeform))
      ) {
        shiny::showNotification(
          "Please enter a format name for 'Other'.",
          type = "warning",
          session = session
        )
        return()
      }

      directions <- input$handoff_directions %||% ""
      if (
        !is.character(directions) ||
          length(directions) != 1L ||
          is.na(directions)
      ) {
        directions <- ""
      }
      handoff_id <- new_handoff_id()
      active_handoff_id(handoff_id)
      task_handoff_id(handoff_id)
      task_operation("generate")
      view$set_panel_open(TRUE)
      handoff_task$invoke("generate", handoff_id, request, directions)
    }
  )

  shiny::observeEvent(
    input$handoff_revise_text,
    label = "on_handoff_revise",
    {
      if (
        identical(
          shiny::isolate(handoff_task$status()),
          "running"
        )
      ) {
        shiny::showNotification(
          "A handoff is already being generated or revised.",
          type = "warning",
          session = session
        )
        return()
      }

      handoff_id <- active_handoff_id()
      instructions <- input$handoff_revise_text
      task_handoff_id(handoff_id)
      task_operation("revise")
      handoff_task$invoke("revise", handoff_id, instructions, "")
    }
  )

  shiny::observeEvent(
    handoff_task$status(),
    label = "on_handoff_task",
    ignoreInit = TRUE,
    {
      status <- handoff_task$status()
      if (!identical(status, "error")) {
        return()
      }
      error_message <- tryCatch(
        {
          handoff_task$result()
          "Unknown error"
        },
        error = function(error) conditionMessage(error)
      )
      shiny::showNotification(
        error_message,
        type = "error",
        duration = NULL,
        session = session
      )

      if (!identical(task_operation(), "generate")) {
        return()
      }
      handoff_id <- task_handoff_id()
      committed <- tryCatch(
        isTRUE(orchestrator$show(handoff_id)),
        error = function(error) FALSE
      )
      if (!committed && identical(active_handoff_id(), handoff_id)) {
        active_handoff_id(NULL)
        view$set_panel_open(FALSE)
      }
    }
  )

  shiny::observeEvent(
    input$handoff_close,
    label = "on_handoff_close",
    {
      active_handoff_id(NULL)
      view$set_panel_open(FALSE)
    }
  )

  shiny::observeEvent(
    input$handoff_open,
    label = "on_handoff_open",
    {
      if (
        identical(
          shiny::isolate(handoff_task$status()),
          "running"
        )
      ) {
        shiny::showNotification(
          "A handoff is being generated or revised. Please wait before switching.",
          type = "warning",
          session = session
        )
        return()
      }

      handoff_id <- input$handoff_open
      if (isTRUE(orchestrator$show(handoff_id))) {
        active_handoff_id(handoff_id)
        view$set_panel_open(TRUE)
      }
    }
  )

  invisible(NULL)
}

new_handoff_id <- function() {
  paste0(
    sample(c(0:9, letters[1:6]), 32L, replace = TRUE),
    collapse = ""
  )
}
