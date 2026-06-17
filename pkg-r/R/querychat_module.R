# Main module UI function
mod_ui <- function(id, ..., greeting = NULL, enable_cancel = TRUE, allow_attachments = TRUE) {
  ns <- shiny::NS(id)

  if (!is.null(greeting) && any(nzchar(greeting))) {
    greeting <- shinychat::chat_greeting(greeting, dismissible = FALSE)
  } else {
    greeting <- NULL
  }

  htmltools::tagList(
    htmltools::htmlDependency(
      "querychat",
      version = "0.0.1",
      package = "querychat",
      src = "htmldep",
      script = "querychat.js",
      stylesheet = "styles.css"
    ),
    shinychat::chat_ui(
      ns("chat"),
      height = "100%",
      class = "querychat",
      enable_cancel = enable_cancel,
      allow_attachments = allow_attachments,
      greeting = greeting,
      ...
    )
  )
}

# Main module server function
mod_server <- function(
  id,
  data_source,
  greeting,
  client,
  tools,
  enable_bookmarking = FALSE
) {
  shiny::moduleServer(id, function(input, output, session) {
    current_title <- shiny::reactiveVal(NULL, label = "current_title")
    current_query <- shiny::reactiveVal(NULL, label = "current_query")
    # Holds a generated greeting so it can be saved and restored on bookmark.
    # Static greetings live in the UI (chat_ui(greeting=)) and persist already.
    current_greeting <- shiny::reactiveVal(NULL, label = "current_greeting")
    filtered_df <- shiny::reactive(label = "filtered_df", {
      data_source$execute_query(query = current_query())
    })

    append_output <- function(...) {
      txt <- paste0(...)
      shinychat::chat_append_message(
        "chat",
        list(role = "assistant", content = txt),
        chunk = TRUE,
        operation = "append",
        session = session
      )
    }

    update_dashboard <- function(query, title) {
      if (!is.null(query)) {
        current_query(query)
      }
      if (!is.null(title)) {
        current_title(title)
      }
    }

    reset_query <- function() {
      current_query(NULL)
      current_title(NULL)
      querychat_tool_result(action = "reset")
    }

    # Non-reactive bookkeeping for bookmark save/restore of viz widgets
    viz_widgets <- list()

    on_visualize <- function(data) {
      viz_widgets[[length(viz_widgets) + 1L]] <<- list(
        widget_id = data$widget_id,
        ggsql = data$ggsql
      )
    }

    # Set up the chat object for this session
    check_function(client)
    chat <- client(
      update_dashboard = update_dashboard,
      reset_dashboard = reset_query,
      visualize = on_visualize,
      tools = tools,
      session = session
    )

    if (is.null(greeting)) {
      shiny::observeEvent(
        input$chat_greeting_requested,
        label = "on_greeting_requested",
        {
          # Re-display a restored greeting rather than generating a new one.
          if (!is.null(current_greeting())) {
            shinychat::chat_set_greeting(
              "chat",
              shinychat::chat_greeting(current_greeting(), dismissible = FALSE)
            )
            return()
          }
          cli::cli_warn(c(
            "No {.arg greeting} provided to {.fn QueryChat}. Using the LLM {.arg client} to generate one now.",
            "i" = "For faster startup, lower cost, and determinism, consider providing a {.arg greeting} to {.fn QueryChat}.",
            "i" = "You can use your {.help querychat::QueryChat} object's {.fn $generate_greeting} method to generate a greeting."
          ))
          greeting_client <- client(tools = NULL)
          stream <- greeting_client$stream_async(GREETING_PROMPT)
          p <- shinychat::chat_set_greeting(
            "chat",
            shinychat::chat_greeting(stream, dismissible = FALSE)
          )
          # Capture the generated greeting so it can be bookmarked and restored.
          promises::then(p, function(value) {
            current_greeting(greeting_client$last_turn()@text)
          })
        }
      )
    }

    ctrl <- ellmer::stream_controller()

    append_stream_task <- shiny::ExtendedTask$new(
      function(client, user_input, controller = NULL) {
        user_input_parts <- if (is.list(user_input)) {
          user_input
        } else {
          list(user_input)
        }
        stream <- client$stream_async(
          !!!user_input_parts,
          stream = "content",
          controller = controller
        )

        p <- promises::promise_resolve(stream)
        promises::then(p, function(stream) {
          shinychat::chat_append("chat", stream)
        })
      }
    )

    shiny::observeEvent(input$chat_user_input, label = "on_chat_user_input", {
      append_stream_task$invoke(chat, input$chat_user_input, controller = ctrl)
    })

    shiny::observeEvent(input$chat_cancel, label = "on_chat_cancel", {
      ctrl$cancel()
    })

    shiny::observeEvent(input$chat_update, label = "on_chat_update", {
      current_query(input$chat_update$query)
      current_title(input$chat_update$title)
    })

    if (enable_bookmarking) {
      shinychat::chat_restore("chat", chat, session = session)
      shiny::setBookmarkExclude("chat_update", session = session)

      shiny::onBookmark(function(state) {
        state$values$querychat_sql <- current_query()
        state$values$querychat_title <- current_title()
        if (!is.null(current_greeting())) {
          state$values$querychat_greeting <- current_greeting()
        }
        if (length(viz_widgets) > 0) {
          state$values$querychat_viz_widgets <- viz_widgets
        }
      })

      shiny::onRestore(function(state) {
        if (!is.null(state$values$querychat_sql)) {
          current_query(state$values$querychat_sql)
        }
        if (!is.null(state$values$querychat_title)) {
          current_title(state$values$querychat_title)
        }
        if (!is.null(state$values$querychat_greeting)) {
          current_greeting(state$values$querychat_greeting)
          shinychat::chat_set_greeting(
            "chat",
            shinychat::chat_greeting(
              state$values$querychat_greeting,
              dismissible = FALSE
            ),
            session = session
          )
        }
        if (!is.null(state$values$querychat_viz_widgets)) {
          restored <- restore_viz_widgets(
            data_source,
            state$values$querychat_viz_widgets,
            session
          )
          viz_widgets <<- restored
        }
      })
    }

    list(
      client = chat,
      sql = current_query,
      title = current_title,
      df = filtered_df
    )
  })
}

# TODO: Make this dependent on enabled tools
GREETING_PROMPT <- paste(
  "Please give me a friendly greeting.",
  "Include a few sample suggestions grouped under ##### headings,",
  "using the suggestion card format from your instructions."
)

restore_viz_widgets <- function(data_source, saved_widgets, session) {
  if (!rlang::is_installed("ggsql")) {
    warning(
      "ggsql is not installed; skipping restoration of visualization widgets.",
      call. = FALSE
    )
    return(list())
  }

  restored <- list()
  for (entry in saved_widgets) {
    tryCatch(
      {
        validated <- ggsql::ggsql_validate(entry$ggsql)
        spec <- execute_ggsql(data_source, validated)
        session$output[[entry$widget_id]] <- ggsql::renderGgsql(spec)
        restored <- c(restored, list(entry))
      },
      error = function(e) {
        warning(
          sprintf(
            "Failed to restore visualization widget '%s' on bookmark restore.",
            entry$widget_id
          ),
          call. = FALSE
        )
      }
    )
  }
  restored
}
