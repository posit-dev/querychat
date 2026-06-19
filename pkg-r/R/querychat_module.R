# Main module UI function
mod_ui <- function(id, ..., enable_cancel = TRUE, allow_attachments = TRUE) {
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
      enable_cancel = enable_cancel,
      allow_attachments = allow_attachments,
      ...
    )
  )
}

# Main module server function
mod_server <- function(
  id,
  data_sources,
  executor,
  greeting,
  client,
  tools,
  enable_bookmarking = FALSE
) {
  shiny::moduleServer(id, function(input, output, session) {
    has_greeted <- shiny::reactiveVal(FALSE, label = "has_greeted")
    current_table_val <- shiny::reactiveVal(NULL, label = "current_table")

    # Per-table reactive state
    tables <- list()
    for (name in names(data_sources)) {
      local({
        tbl_name <- name
        sql_val <- shiny::reactiveVal(NULL, label = paste0(tbl_name, "_sql"))
        title_val <- shiny::reactiveVal(
          NULL,
          label = paste0(tbl_name, "_title")
        )
        df_val <- shiny::reactive(label = paste0(tbl_name, "_df"), {
          q <- sql_val()
          if (is.null(q)) {
            data_sources[[tbl_name]]$get_data()
          } else {
            executor$execute_query(q)
          }
        })
        tables[[tbl_name]] <<- list(
          sql = sql_val,
          title = title_val,
          df = df_val
        )
      })
    }

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

    update_dashboard <- function(query, title, table) {
      if (!is.null(query)) {
        tables[[table]]$sql(query)
      }
      if (!is.null(title)) {
        tables[[table]]$title(title)
      }
      current_table_val(table)
    }

    reset_query <- function(table) {
      tables[[table]]$sql(NULL)
      tables[[table]]$title(NULL)
      current_table_val(table)
      querychat_tool_result(
        executor,
        query = NULL,
        action = "reset",
        table_name = table
      )
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
      tbl <- input$chat_update$table
      if (!is.null(tbl) && tbl %in% names(tables)) {
        tables[[tbl]]$sql(input$chat_update$query)
        tables[[tbl]]$title(input$chat_update$title)
        current_table_val(tbl)
      }
    })

    if (enable_bookmarking) {
      shinychat::chat_restore(
        "chat",
        chat,
        restore_ui = FALSE,
        session = session
      )

      shiny::onBookmark(function(state) {
        table_states <- list()
        for (name in names(tables)) {
          table_states[[name]] <- list(
            sql = tables[[name]]$sql(),
            title = tables[[name]]$title()
          )
        }
        state$values$querychat_tables <- table_states
        state$values$querychat_has_greeted <- has_greeted()
        if (length(viz_widgets) > 0) {
          state$values$querychat_viz_widgets <- viz_widgets
        }
      })

      shiny::onRestore(function(state) {
        if (!is.null(state$values$querychat_tables)) {
          last_restored <- NULL
          for (name in names(state$values$querychat_tables)) {
            tbl_state <- state$values$querychat_tables[[name]]
            if (!is.null(tbl_state$sql)) {
              tables[[name]]$sql(tbl_state$sql)
              last_restored <- name
            }
            if (!is.null(tbl_state$title)) {
              tables[[name]]$title(tbl_state$title)
            }
          }
          if (!is.null(last_restored)) {
            current_table_val(last_restored)
          }
        }
        if (!is.null(state$values$querychat_has_greeted)) {
          has_greeted(state$values$querychat_has_greeted)
        }
        if (!is.null(state$values$querychat_viz_widgets)) {
          restored <- restore_viz_widgets(
            executor,
            state$values$querychat_viz_widgets,
            session
          )
          viz_widgets <<- restored
        }
      })
    }

    table_fn <- function(name) {
      if (!name %in% names(tables)) {
        available <- paste0("'", names(tables), "'", collapse = ", ")
        cli::cli_abort(
          "Table {.val {name}} not found. Available: {available}"
        )
      }
      TableAccessor$new(name, data_sources[[name]], state = tables[[name]])
    }

    table_names_fn <- function() names(tables)

    # Backward compat: for single-table, expose sql/title/df directly
    if (length(data_sources) == 1) {
      first <- tables[[1]]
      list(
        client = chat,
        sql = first$sql,
        title = first$title,
        df = first$df,
        table = table_fn,
        table_names = table_names_fn,
        current_table = current_table_val,
        .tables = tables
      )
    } else {
      single_table_error <- function(method) {
        function(...) {
          cli::cli_abort(
            "Multiple tables registered. Use {.code qc_vals$table('name')${method}()} instead."
          )
        }
      }
      list(
        client = chat,
        sql = single_table_error("sql"),
        title = single_table_error("title"),
        df = single_table_error("df"),
        table = table_fn,
        table_names = table_names_fn,
        current_table = current_table_val,
        .tables = tables
      )
    }
  })
}

# TODO: Make this dependent on enabled tools
GREETING_PROMPT <- paste(
  "Please give me a friendly greeting.",
  "Include a few sample suggestions grouped under ##### headings,",
  "using the suggestion card format from your instructions."
)

restore_viz_widgets <- function(executor, saved_widgets, session) {
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
        spec <- execute_ggsql(executor, validated)
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
