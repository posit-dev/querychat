# Main module UI function
mod_ui <- function(id, ...) {
  ns <- shiny::NS(id)
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
  tools = c("update", "query"),
  enable_bookmarking = FALSE
) {
  shiny::moduleServer(id, function(input, output, session) {
    current_title <- shiny::reactiveVal(NULL, label = "current_title")
    current_query <- shiny::reactiveVal(NULL, label = "current_query")
    has_greeted <- shiny::reactiveVal(FALSE, label = "has_greeted")
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

    # Prepopulate the chat UI with a welcome message that appears to be from the
    # chat model (but is actually hard-coded). This is just for the user, not for
    # the chat model to see.
    shiny::observe(label = "greet_on_startup", {
      if (has_greeted()) {
        return()
      }

      greeting_content <- if (!is.null(greeting) && any(nzchar(greeting))) {
        greeting
      } else {
        cli::cli_warn(
          c(
            "No {.arg greeting} provided to {.fn QueryChat}. Using the LLM {.arg client} to generate one now.",
            "i" = "For faster startup, lower cost, and determinism, consider providing a {.arg greeting} to {.fn QueryChat}.",
            "i" = "You can use your {.help querychat::QueryChat} object's {.fn $generate_greeting} method to generate a greeting."
          )
        )
        chat$stream_async(GREETING_PROMPT)
      }

      shinychat::chat_append("chat", greeting_content)
      has_greeted(TRUE)
    })

    append_stream_task <- shiny::ExtendedTask$new(
      function(client, user_input) {
        stream <- client$stream_async(
          user_input,
          stream = "content"
        )

        p <- promises::promise_resolve(stream)
        promises::then(p, function(stream) {
          shinychat::chat_append("chat", stream)
        })
      }
    )

    shiny::observeEvent(input$chat_user_input, label = "on_chat_user_input", {
      append_stream_task$invoke(chat, input$chat_user_input)
    })

    shiny::observeEvent(input$chat_update, label = "on_chat_update", {
      current_query(input$chat_update$query)
      current_title(input$chat_update$title)
    })

    if (enable_bookmarking) {
      shinychat::chat_restore("chat", chat, session = session)

      shiny::onBookmark(function(state) {
        state$values$querychat_sql <- current_query()
        state$values$querychat_title <- current_title()
        state$values$querychat_has_greeted <- has_greeted()
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
        if (!is.null(state$values$querychat_has_greeted)) {
          has_greeted(state$values$querychat_has_greeted)
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
GREETING_PROMPT <- "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."

restore_viz_widgets <- function(data_source, saved_widgets, session) {
  rlang::check_installed("ggsql", reason = "for visualization support.")

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
