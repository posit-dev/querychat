#' Call this once outside of any server function
#'
#' This will perform one-time initialization that can then be shared by all
#' Shiny sessions in the R process.
#'
#' @param data_source A querychat_data_source object created by
#'   `querychat_data_source()`.
#'
#'   To create a data source:
#'   - For data frame: `querychat_data_source(df, tbl_name = "my_table")`
#'   - For database: `querychat_data_source(conn, "table_name")`
#' @param greeting A string in Markdown format, containing the initial message
#'   to display to the user upon first loading the chatbot. If not provided, the
#'   LLM will be invoked at the start of the conversation to generate one.
#' @param data_description A string containing a data description for the chat
#'   model. We have found that formatting the data description as a markdown
#'   bulleted list works best.
#' @param extra_instructions A string containing extra instructions for the
#'   chat model.
#' @param client An `ellmer::Chat` object, a string to be passed to
#'   [ellmer::chat()] describing the model to use (e.g. `"openai/gpt-4o"`), or a
#'   function that creates a chat client. When using a function, the function
#'   should take `system_prompt` as an argument and return an `ellmer::Chat`
#'   object.
#'
#'   If `client` is not provided, querychat consults the `querychat.client` R
#'   option, which can be any of the described options, or the
#'   `QUERYCHAT_CLIENT` environment variable, which can be set to a a
#'   provider-model string. If no option is provided, querychat defaults to
#'   using [ellmer::chat_openai()].
#' @param create_chat_func `r lifecycle::badge('deprecated')`. Use the `client`
#'   argument instead.
#' @param system_prompt A string containing the system prompt for the chat
#'   model. The default generates a generic prompt, which you can enhance via
#'   the `data_description` and `extra_instructions` arguments.
#' @param auto_close_data_source Should the data source connection be
#'   automatically closed when the shiny app stops? Defaults to TRUE.
#'
#' @returns An object that can be passed to `querychat_server()` as the
#'   `querychat_config` argument. By convention, this object should be named
#'   `querychat_config`.
#'
#' @export
querychat_init <- function(
  data_source,
  greeting = NULL,
  data_description = NULL,
  extra_instructions = NULL,
  create_chat_func = deprecated(),
  system_prompt = NULL,
  auto_close_data_source = TRUE,
  client = NULL
) {
  if (lifecycle::is_present(create_chat_func)) {
    lifecycle::deprecate_warn(
      "0.0.1",
      "querychat_init(create_chat_func=)",
      "querychat_init(client =)"
    )
    if (!is.null(client)) {
      rlang::abort(
        "You cannot pass both `create_chat_func` and `client` to `querychat_init()`."
      )
    }
    client <- create_chat_func
  }

  client <- querychat_client(client)

  # If the user passes a data.frame to data_source, create a correct data source for them
  if (inherits(data_source, "data.frame")) {
    data_source <- querychat_data_source(
      data_source,
      table_name = deparse(substitute(data_source))
    )
  }

  # Check that data_source is a querychat_data_source object
  if (!inherits(data_source, "querychat_data_source")) {
    rlang::abort(
      "`data_source` must be a querychat_data_source object. Use querychat_data_source() to create one."
    )
  }

  if (auto_close_data_source) {
    # Close the data source when the Shiny app stops (or, if some reason the
    # querychat_init call is within a specific session, when the session ends)
    shiny::onStop(function() {
      message("Closing data source...")
      cleanup_source(data_source)
    })
  }

  # Generate system prompt if not provided
  if (is.null(system_prompt)) {
    system_prompt <- create_system_prompt(
      data_source,
      data_description = data_description,
      extra_instructions = extra_instructions
    )
  }

  # Validate system prompt
  stopifnot(
    "system_prompt must be a string" = is.character(system_prompt)
  )

  if (!is.null(greeting)) {
    greeting <- paste(collapse = "\n", greeting)
  } else {
    rlang::warn(c(
      "No greeting provided; the LLM will be invoked at the start of the conversation to generate one.",
      "*" = "For faster startup, lower cost, and determinism, please save a greeting and pass it to querychat_init()."
    ))
  }

  structure(
    list(
      data_source = data_source,
      system_prompt = system_prompt,
      greeting = greeting,
      client = client
    ),
    class = "querychat_config"
  )
}

#' UI components for querychat
#'
#' These functions create UI components for the querychat interface.
#' `querychat_ui()` creates a basic chat interface, while `querychat_sidebar()`
#' wraps the chat interface in a [bslib::sidebar()] component designed to be
#' used as the `sidebar` argument to [bslib::page_sidebar()].
#'
#' @param id The ID of the module instance.
#' @param width,height In `querychat_sidebar()`: the width and height of the
#'   sidebar.
#' @param ... In `querychat_sidebar()`: additional arguments passed to
#'   [bslib::sidebar()].
#'
#' @return A UI object that can be embedded in a Shiny app.
#'
#' @name querychat_ui
#' @export
querychat_sidebar <- function(id, width = 400, height = "100%", ...) {
  bslib::sidebar(
    width = width,
    height = height,
    class = "querychat-sidebar",
    ...,
    # purposely NOT using ns() for `id`, we're just a passthrough
    querychat_ui(id)
  )
}

#' @rdname querychat_ui
#' @export
querychat_ui <- function(id) {
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

#' Initalize the querychat server
#'
#' @param id The ID of the module instance. Must match the ID passed to
#'   the corresponding call to `querychat_ui()`.
#' @param querychat_config An object created by `querychat_init()`.
#'
#' @returns A querychat instance, which is a named list with the following
#' elements:
#'
#' - `sql`: A reactive that returns the current SQL query.
#' - `title`: A reactive that returns the current title.
#' - `df`: A reactive that returns the filtered data as a data.frame.
#' - `chat`: The [ellmer::Chat] object that powers the chat interface.
#'
#' @export
querychat_server <- function(id, querychat_config) {
  shiny::moduleServer(id, function(input, output, session) {
    # 🔄 Reactive state/computation --------------------------------------------

    data_source <- querychat_config[["data_source"]]
    system_prompt <- querychat_config[["system_prompt"]]
    greeting <- querychat_config[["greeting"]]
    client <- querychat_config[["client"]]

    current_title <- shiny::reactiveVal(NULL)
    current_query <- shiny::reactiveVal("")
    filtered_df <- shiny::reactive({
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

    # Preload the conversation with the system prompt. These are instructions for
    # the chat model, and must not be shown to the end user.
    chat <- client$clone()
    chat$set_turns(list())
    chat$set_system_prompt(system_prompt)
    chat$register_tool(
      tool_update_dashboard(data_source, current_query, current_title)
    )
    chat$register_tool(tool_query(data_source))
    chat$register_tool(tool_reset_dashboard(reset_query))

    # Prepopulate the chat UI with a welcome message that appears to be from the
    # chat model (but is actually hard-coded). This is just for the user, not for
    # the chat model to see.
    if (!is.null(greeting)) {
      if (isTRUE(any(nzchar(greeting)))) {
        shinychat::chat_append("chat", greeting)
      }
    } else {
      shinychat::chat_append(
        "chat",
        chat$stream_async(
          "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."
        )
      )
    }

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

    shiny::observeEvent(input$chat_user_input, {
      append_stream_task$invoke(chat, input$chat_user_input)
    })

    shiny::observeEvent(input$chat_update, {
      current_query(input$chat_update$query)
      current_title(input$chat_update$title)
    })

    list(
      chat = chat,
      sql = shiny::reactive(current_query()),
      title = shiny::reactive(current_title()),
      df = filtered_df,
      update_query = function(query, title = NULL) {
        current_query(query)
        current_title(title)
      }
    )
  })
}

df_to_html <- function(df, maxrows = 5) {
  df_short <- if (nrow(df) > 10) utils::head(df, maxrows) else df

  tbl_html <- utils::capture.output(
    df_short |>
      xtable::xtable() |>
      print(
        type = "html",
        include.rownames = FALSE,
        html.table.attributes = NULL
      )
  ) |>
    paste(collapse = "\n")

  if (nrow(df_short) != nrow(df)) {
    rows_notice <- paste0(
      "\n\n(Showing only the first ",
      maxrows,
      " rows out of ",
      nrow(df),
      ".)\n"
    )
  } else {
    rows_notice <- ""
  }

  paste0(tbl_html, "\n", rows_notice)
}
