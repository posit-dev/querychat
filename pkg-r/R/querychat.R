#' Call this once outside of any server function
#'
#' This will perform one-time initialization that can then be shared by all
#' Shiny sessions in the R process.
#'
#' @param df A data frame.
#' @param table_name A string containing a valid table name for the data frame,
#'   that will appear in SQL queries. Ensure that it begins with a letter, and
#'   contains only letters, numbers, and underscores. By default, querychat will
#'   try to infer a table name using the name of the `df` argument.
#' @param greeting Optional string or existing file path. The contents
#'   should be in plain text or Markdown format, containing the initial message
#'   to display to the user upon first loading the chatbot. If not provided, the
#'   LLM will be invoked at the start of the conversation to generate one.
#' @param ... Additional arguments passed to the `querychat_system_prompt()`
#'   function, such as `categorical_threshold`. If a
#'   `system_prompt` argument is provided, the `...` arguments will be silently
#'   ignored.
#' @inheritParams querychat_system_prompt
#' @param system_prompt A string containing the system prompt for the chat model.
#'   The default uses `querychat_system_prompt()` to generate a generic prompt,
#'   which you can enhance via the `data_description` and `extra_instructions`
#'   arguments.
#' @param create_chat_func A function that takes a system prompt and returns a
#'   chat object. The default uses `ellmer::chat_openai()`.
#' @returns An object that can be passed to `querychat_server()` as the
#'   `querychat_config` argument. By convention, this object should be named
#'   `querychat_config`.
#'
#' @export
querychat_init <- function(
  df,
  ...,
  table_name = deparse(substitute(df)),
  greeting = NULL,
  data_description = NULL,
  extra_instructions = NULL,
  prompt_template = NULL,
  system_prompt = querychat_system_prompt(
    df,
    table_name,
    # By default, pass through any params supplied to querychat_init()
    ...,
    data_description = data_description,
    extra_instructions = extra_instructions,
    prompt_template = prompt_template
  ),
  create_chat_func = purrr::partial(ellmer::chat_openai, model = "gpt-4o")
) {
  is_table_name_ok <- is.character(table_name) &&
    length(table_name) == 1 &&
    grepl("^[a-zA-Z][a-zA-Z0-9_]*$", table_name, perl = TRUE)
  if (!is_table_name_ok) {
    if (missing(table_name)) {
      rlang::abort(
        "Unable to infer table name from `df` argument. Please specify `table_name` argument explicitly."
      )
    } else {
      rlang::abort(
        "`table_name` argument must be a string containing a valid table name."
      )
    }
  }

  force(df)
  force(system_prompt) # Have default `...` params evaluated
  force(create_chat_func)

  # TODO: Provide nicer looking errors here
  stopifnot(
    "df must be a data frame" = is.data.frame(df),
    "table_name must be a string" = is.character(table_name),
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
    greeting <- read_path_or_string(greeting, "greeting")
  } else {
    rlang::warn(c(
      "No greeting provided; the LLM will be invoked at the start of the conversation to generate one.",
      "*" = "For faster startup, lower cost, and determinism, please save a greeting and pass it to querychat_init()."
    ))
  }

  conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
  duckdb::duckdb_register(conn, table_name, df, experimental = FALSE)
  shiny::onStop(function() DBI::dbDisconnect(conn))

  structure(
    list(
      df = df,
      conn = conn,
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
#' - `df`: A reactive that returns the data frame, filtered and sorted by the
#'   current SQL query.
#' - `chat`: The [ellmer::Chat] object that powers the chat interface.
#'
#' By convention, this object should be named `querychat_config`.
#'
#' @export
querychat_server <- function(id, querychat_config) {
  shiny::moduleServer(id, function(input, output, session) {
    # 🔄 Reactive state/computation --------------------------------------------

    df <- querychat_config[["df"]]
    conn <- querychat_config[["conn"]]
    system_prompt <- querychat_config[["system_prompt"]]
    greeting <- querychat_config[["greeting"]]
    create_chat_func <- querychat_config[["create_chat_func"]]

    current_title <- shiny::reactiveVal(NULL)
    current_query <- shiny::reactiveVal("")
    filtered_df <- shiny::reactive({
      if (current_query() == "") {
        df
      } else {
        DBI::dbGetQuery(conn, current_query())
      }
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
    # @param query A DuckDB SQL query; must be a SELECT statement.
    # @param title A title to display at the top of the data dashboard,
    #   summarizing the intent of the SQL query.
    update_dashboard <- function(query, title) {
      append_output("\n```sql\n", query, "\n```\n\n")

      tryCatch(
        {
          # Try it to see if it errors; if so, the LLM will see the error
          DBI::dbGetQuery(conn, query)
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
    # @param query A DuckDB SQL query; must be a SELECT statement.
    # @return The results of the query as a JSON string.
    query <- function(query) {
      # Do this before query, in case it errors
      append_output("\n```sql\n", query, "\n```\n\n")

      tryCatch(
        {
          df <- DBI::dbGetQuery(conn, query)
        },
        error = function(e) {
          append_output("> Error: ", conditionMessage(e), "\n\n")
          stop(e)
        }
      )

      tbl_html <- df_to_html(df, maxrows = 5)
      append_output(tbl_html, "\n\n")

      df |> jsonlite::toJSON(auto_unbox = TRUE)
    }

    # Preload the conversation with the system prompt. These are instructions for
    # the chat model, and must not be shown to the end user.
    chat <- create_chat_func(system_prompt = system_prompt)
    chat$register_tool(ellmer::tool(
      update_dashboard,
      "Modifies the data presented in the data dashboard, based on the given SQL query, and also updates the title.",
      query = ellmer::type_string(
        "A DuckDB SQL query; must be a SELECT statement."
      ),
      title = ellmer::type_string(
        "A title to display at the top of the data dashboard, summarizing the intent of the SQL query."
      )
    ))
    chat$register_tool(ellmer::tool(
      query,
      "Perform a SQL query on the data, and return the results as JSON.",
      query = ellmer::type_string(
        "A DuckDB SQL query; must be a SELECT statement."
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
      df = filtered_df
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
