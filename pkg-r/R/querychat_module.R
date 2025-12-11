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

    # Set up the chat object for this session
    if (is_function(client)) {
      # This is the `QueryChat$client` function, or generally a function that
      # takes the update/reset callbacks and returns a realized QC chat client
      chat <- client(
        update_dashboard = update_dashboard,
        reset_dashboard = reset_query
      )
    } else {
      chat <- client$clone()
      chat$register_tool(
        tool_update_dashboard(data_source, update_fn = update_dashboard)
      )
      chat$register_tool(tool_query(data_source))
      chat$register_tool(tool_reset_dashboard(reset_query))
    }

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
        cli::cli_warn(c(
          "No {.arg greeting} provided to {.fn QueryChat}. Using the LLM {.arg client} to generate one now.",
          "i" = "For faster startup, lower cost, and determinism, consider providing a {.arg greeting} to {.fn QueryChat}.",
          "i" = "You can use your {.help querychat::QueryChat} object's {.fn $generate_greeting} method to generate a greeting."
        ))
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


GREETING_PROMPT <- "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."
