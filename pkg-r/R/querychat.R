#' Call this once outside of any server function
#'
#' This will perform one-time initialization that can then be shared by all
#' Shiny sessions in the R process.
#'
#' @param data_source A querychat_data_source object created by `querychat_data_source()`.
#'   To create a data source:
#'   - For data frame: `querychat_data_source(df, tbl_name = "my_table")`
#'   - For database: `querychat_data_source(conn, "table_name")`
#' @param greeting A string in Markdown format, containing the initial message
#'   to display to the user upon first loading the chatbot. If not provided, the
#'   LLM will be invoked at the start of the conversation to generate one.
#' @param data_description A string containing a data description for the chat model. We have found
#'   that formatting the data description as a markdown bulleted list works best.
#' @param extra_instructions A string containing extra instructions for the chat model.
#' @param create_chat_func A function that takes a system prompt and returns a
#'   chat object. The default uses `ellmer::chat_openai()`.
#' @param system_prompt A string containing the system prompt for the chat model.
#'   The default generates a generic prompt, which you can enhance via the `data_description` and 
#'   `extra_instructions` arguments.
#' @param auto_close_data_source Should the data source connection be automatically
#'   closed when the shiny app stops? Defaults to TRUE.
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
  create_chat_func = purrr::partial(ellmer::chat_openai, model = "gpt-4o"),
  system_prompt = NULL,
  auto_close_data_source = TRUE
) {
  force(create_chat_func)

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

  # Validate system prompt and create_chat_func
  stopifnot(
    "system_prompt must be a string" = is.character(system_prompt),
    "create_chat_func must be a function" = is.function(create_chat_func)
  )

  if ("table_name" %in% names(attributes(system_prompt))) {
    # If available, be sure to use the `table_name` argument to `querychat_init()`
    # matches the one supplied to the system prompt
    if (table_name != attr(system_prompt, "table_name")) {
      rlang::abort(
        "`querychat_init(table_name=)` must match system prompt `table_name` supplied to `querychat_system_prompt()`."
      )
    }
  }
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
      create_chat_func = create_chat_func
    ),
    class = "querychat_config"
  )
}

#' UI components for querychat
#'
#' These functions create UI components for the querychat interface.
#' `querychat_ui` creates a basic chat interface, while `querychat_sidebar`
#' wraps the chat interface in a `bslib::sidebar` component designed to be used
#' as the `sidebar` argument to `bslib::page_sidebar`.
#'
#' @param id The ID of the module instance.
#' @param width The width of the sidebar (when using `querychat_sidebar`).
#' @param height The height of the sidebar (when using `querychat_sidebar`).
#' @param ... Additional arguments passed to `bslib::sidebar` (when using `querychat_sidebar`).
#'
#' @return A UI object that can be embedded in a Shiny app.
#'
#' @name querychat_ui
#' @export
querychat_sidebar <- function(id, width = 400, height = "100%", ...) {
  bslib::sidebar(
    width = width,
    height = height,
    ...,
    querychat_ui(id) # purposely NOT using ns() here, we're just a passthrough
  )
}

#' @rdname querychat_ui
#' @export
querychat_ui <- function(id) {
  ns <- shiny::NS(id)
  htmltools::tagList(
    # TODO: Make this into a proper HTML dependency
    shiny::includeCSS(system.file("www", "styles.css", package = "querychat")),
    shinychat::chat_ui(ns("chat"), height = "100%", fill = TRUE)
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
#' - `df`: A reactive that returns the filtered data. For data frame sources,
#'   this returns a data.frame. For database sources, this returns a lazy
#'   dbplyr tbl that can be further manipulated with dplyr verbs before
#'   calling collect() to materialize the results.
#' - `chat`: The [ellmer::Chat] object that powers the chat interface.
#'
#' By convention, this object should be named `querychat_config`.
#'
#' @export
querychat_server <- function(id, querychat_config) {
  shiny::moduleServer(id, function(input, output, session) {
    # 🔄 Reactive state/computation --------------------------------------------

    data_source <- querychat_config[["data_source"]]
    system_prompt <- querychat_config[["system_prompt"]]
    greeting <- querychat_config[["greeting"]]
    create_chat_func <- querychat_config[["create_chat_func"]]

    current_title <- shiny::reactiveVal(NULL)
    current_query <- shiny::reactiveVal("")
    filtered_df <- shiny::reactive({
      execute_query(data_source, query = dplyr::sql(current_query()))
    })
    filtered_tbl <- shiny::reactive({
      get_lazy_data(data_source, query = dplyr::sql(current_query()))
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

    # Modifies the data presented in the data dashboard, based on the given SQL
    # query, and also updates the title.
    # @param query A SQL query; must be a SELECT statement.
    # @param title A title to display at the top of the data dashboard,
    #   summarizing the intent of the SQL query.
    update_dashboard <- function(query, title) {
      append_output("\n```sql\n", query, "\n```\n\n")

      tryCatch(
        {
          # Try it to see if it errors; if so, the LLM will see the error
          test_query(data_source, query)
        },
        error = function(err) {
          append_output("> Error: ", conditionMessage(err), "\n\n")
          stop(err)
        }
      )

      if (!is.null(query)) {
        current_query(query)
      }
      if (!is.null(title)) {
        current_title(title)
      }
    }

    # Perform a SQL query on the data, and return the results as JSON.
    # @param query A SQL query; must be a SELECT statement.
    # @return The results of the query as a data frame.
    query <- function(query) {
      # Do this before query, in case it errors
      append_output("\n```sql\n", query, "\n```\n")

      tryCatch(
        {
          # Execute the query and return the results
          execute_query(data_source, query)
        },
        error = function(e) {
          append_output("> Error: ", conditionMessage(e), "\n\n")
          stop(e)
        }
      )
    }

    # Preload the conversation with the system prompt. These are instructions for
    # the chat model, and must not be shown to the end user.
    chat <- create_chat_func(system_prompt = system_prompt)
    chat$register_tool(ellmer::tool(
      update_dashboard,
      "Modifies the data presented in the data dashboard, based on the given SQL query, and also updates the title.",
      query = ellmer::type_string(
        "A SQL query; must be a SELECT statement."
      ),
      title = ellmer::type_string(
        "A title to display at the top of the data dashboard, summarizing the intent of the SQL query."
      )
    ))
    chat$register_tool(ellmer::tool(
      query,
      "Perform a SQL query on the data, and return the results.",
      query = ellmer::type_string(
        "A SQL query; must be a SELECT statement."
      )
    ))

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

    # Handle user input
    shiny::observeEvent(input$chat_user_input, {
      # Add user message to the chat history
      shinychat::chat_append(
        "chat",
        chat$stream_async(input$chat_user_input)
      )
    })

    list(
      chat = chat,
      sql = shiny::reactive(current_query()),
      title = shiny::reactive(current_title()),
      df = filtered_df,
      tbl = filtered_tbl
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
    rows_notice <- glue::glue(
      "\n\n(Showing only the first {maxrows} rows out of {nrow(df)}.)\n"
    )
  } else {
    rows_notice <- ""
  }

  paste0(tbl_html, "\n", rows_notice)
}
