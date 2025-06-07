#' Call this once outside of any server function
#'
#' This will perform one-time initialization that can then be shared by all
#' Shiny sessions in the R process.
#'
#' @param data_source Either a data frame or a database_source object created by 
#'   `database_source()`. For backwards compatibility, `df` can also be used.
#' @param df Deprecated. Use `data_source` instead. A data frame.
#' @param tbl_name A string containing a valid table name for the data frame,
#'   that will appear in SQL queries. Ensure that it begins with a letter, and
#'   contains only letters, numbers, and underscores. By default, querychat will
#'   try to infer a table name using the name of the `df` argument. Not used 
#'   when `data_source` is a database_source object.
#' @param greeting A string in Markdown format, containing the initial message
#'   to display to the user upon first loading the chatbot. If not provided, the
#'   LLM will be invoked at the start of the conversation to generate one.
#' @param data_description A string in plain text or Markdown format, containing
#'   a description of the data frame or any additional context that might be
#'   helpful in understanding the data. This will be included in the system
#'   prompt for the chat model. If a `system_prompt` argument is provided, the
#'   `data_description` argument will be ignored.
#' @param extra_instructions A string in plain text or Markdown format, containing
#'   any additional instructions for the chat model. These will be appended at
#'   the end of the system prompt. If a `system_prompt` argument is provided,
#'   the `extra_instructions` argument will be ignored.
#' @param create_chat_func A function that takes a system prompt and returns a
#'   chat object. The default uses `ellmer::chat_openai()`.
#' @param system_prompt A string containing the system prompt for the chat model.
#'   The default uses `querychat_system_prompt()` to generate a generic prompt,
#'   which you can enhance via the `data_description` and `extra_instructions`
#'   arguments.
#'
#' @returns An object that can be passed to `querychat_server()` as the
#'   `querychat_config` argument. By convention, this object should be named
#'   `querychat_config`.
#'
#' @export
querychat_init <- function(
  data_source = NULL,
  df = NULL,
  tbl_name = NULL,
  greeting = NULL,
  data_description = NULL,
  extra_instructions = NULL,
  create_chat_func = purrr::partial(ellmer::chat_openai, model = "gpt-4o"),
  system_prompt = NULL
) {
  # Handle backwards compatibility and argument validation
  if (!is.null(df) && !is.null(data_source)) {
    rlang::abort("Cannot specify both `df` and `data_source` arguments")
  }
  
  if (!is.null(df)) {
    rlang::warn("`df` argument is deprecated. Use `data_source` instead.")
    data_source <- df
  }
  
  if (is.null(data_source)) {
    rlang::abort("Must provide either `data_source` or `df` argument")
  }
  
  force(create_chat_func)
  
  # Determine source type and setup
  is_database_source <- inherits(data_source, "database_source")
  is_dataframe <- is.data.frame(data_source)
  
  if (!is_database_source && !is_dataframe) {
    rlang::abort("`data_source` must be either a data frame or database_source object")
  }
  
  if (is_database_source) {
    # Using database source
    db_source <- data_source
    conn <- db_source$conn
    tbl_name <- db_source$table_name
    df <- NULL  # No data frame for database sources
    
    # Generate system prompt if not provided
    if (is.null(system_prompt)) {
      system_prompt <- querychat_system_prompt_database(
        db_source,
        data_description = data_description,
        extra_instructions = extra_instructions
      )
    }
  } else {
    # Using data frame source - set up DuckDB 
    if (is.null(tbl_name)) {
      tbl_name <- deparse(substitute(data_source))
      if (is.null(tbl_name) || tbl_name == "NULL") {
        rlang::abort("Unable to infer table name. Please specify `tbl_name` argument explicitly.")
      }
    }
    
    is_tbl_name_ok <- is.character(tbl_name) &&
      length(tbl_name) == 1 &&
      grepl("^[a-zA-Z][a-zA-Z0-9_]*$", tbl_name, perl = TRUE)
    if (!is_tbl_name_ok) {
      rlang::abort("`tbl_name` argument must be a string containing a valid table name.")
    }
    
    df <- data_source
    conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
    duckdb::duckdb_register(conn, tbl_name, df, experimental = FALSE)
    shiny::onStop(function() DBI::dbDisconnect(conn))
    
    # Generate system prompt if not provided
    if (is.null(system_prompt)) {
      system_prompt <- querychat_system_prompt(
        df,
        tbl_name,
        data_description = data_description,
        extra_instructions = extra_instructions
      )
    }
    
    db_source <- NULL
  }
  
  # Validate system prompt and create_chat_func
  stopifnot(
    "system_prompt must be a string" = is.character(system_prompt),
    "create_chat_func must be a function" = is.function(create_chat_func)
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
      df = df,
      conn = conn,
      db_source = db_source,
      system_prompt = system_prompt,
      greeting = greeting,
      create_chat_func = create_chat_func,
      is_database_source = is_database_source,
      table_name = tbl_name
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

    df <- querychat_config[["df"]]
    conn <- querychat_config[["conn"]]
    db_source <- querychat_config[["db_source"]]
    is_database_source <- querychat_config[["is_database_source"]]
    table_name <- querychat_config[["table_name"]]
    system_prompt <- querychat_config[["system_prompt"]]
    greeting <- querychat_config[["greeting"]]
    create_chat_func <- querychat_config[["create_chat_func"]]

    current_title <- shiny::reactiveVal(NULL)
    current_query <- shiny::reactiveVal("")
    filtered_df <- shiny::reactive({
      if (current_query() == "") {
        if (is_database_source) {
          # For database sources, return lazy tbl (no data transfer)
          get_database_data(db_source)
        } else {
          # For data frames, return the original data frame
          df
        }
      } else {
        if (is_database_source) {
          # For database sources, return lazy tbl with custom query
          # Parse and create a lazy tbl from the SQL query
          dplyr::tbl(conn, dplyr::sql(current_query()))
        } else {
          # For data frames, execute query and return result
          DBI::dbGetQuery(conn, current_query())
        }
      }
    })

    append_output <- function(...) {
      txt <- paste0(...)
      shinychat::chat_append_message(
        session$ns("chat"),
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
      append_output("\n```sql\n", query, "\n```\n")

      tryCatch(
        {
          # Execute the query and return the results as a data frame
          # This tool is for answering questions, so we need actual results
          DBI::dbGetQuery(conn, query)
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
        shinychat::chat_append(session$ns("chat"), greeting)
      }
    } else {
      shinychat::chat_append(
        session$ns("chat"),
        chat$stream_async(
          "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."
        )
      )
    }

    # Handle user input
    shiny::observeEvent(input$chat_user_input, {
      # Add user message to the chat history
      shinychat::chat_append(
        session$ns("chat"),
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
