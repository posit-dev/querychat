# Main module UI function
mod_ui <- function(id) {
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
      fill = TRUE,
      class = "querychat"
    )
  )
}

# Main module server function
mod_server <- function(id, data_source, greeting, client) {
  shiny::moduleServer(id, function(input, output, session) {
    current_title <- shiny::reactiveVal(NULL, label = "current_title")
    current_query <- shiny::reactiveVal("", label = "current_query")
    filtered_df <- shiny::reactive(label = "filtered_df", {
      execute_query(data_source, query = DBI::SQL(current_query()))
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

    reset_query <- function() {
      current_query("")
      current_title(NULL)
      querychat_tool_result(action = "reset")
    }

    # Set up the chat object for this session
    chat <- client$clone()
    chat$register_tool(
      tool_update_dashboard(data_source, current_query, current_title)
    )
    chat$register_tool(tool_query(data_source))
    chat$register_tool(tool_reset_dashboard(reset_query))

    # Prepopulate the chat UI with a welcome message that appears to be from the
    # chat model (but is actually hard-coded). This is just for the user, not for
    # the chat model to see.
    greeting_content <- if (!is.null(greeting) && any(nzchar(greeting))) {
      greeting
    } else {
      # Generate greeting on the fly if none provided
      rlang::warn(c(
        "No greeting provided; generating one now. This adds latency and cost.",
        "i" = "Consider using $generate_greeting() to create a reusable greeting."
      ))
      chat_temp <- client$clone()
      prompt <- "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."
      chat_temp$stream_async(prompt)
    }

    shinychat::chat_append("chat", greeting_content)

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

    list(
      chat = chat,
      sql = current_query,
      title = current_title,
      df = filtered_df
    )
  })
}
