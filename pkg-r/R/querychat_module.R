# Main module UI function
mod_ui <- function(id, ...) {

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
      shiny::NS(id, "chat"),
      height = "100%",
      class = "querychat",
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
  greeter = NULL,
  greeting_base = NULL,
  enable_bookmarking = FALSE
) {
  shiny::moduleServer(id, function(input, output, session) {
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

    viz_widgets <- list()
    on_visualize <- function(data) {
      viz_widgets[[length(viz_widgets) + 1L]] <<- list(
        widget_id = data$widget_id,
        ggsql = data$ggsql
      )
    }

    check_function(client)
    pre_built_client <- client(
      update_dashboard = update_dashboard,
      reset_dashboard = reset_query,
      visualize = on_visualize,
      tools = tools,
      session = session
    )

    greeting_arg <- if (is.null(greeting)) {
      function() {
        cli::cli_warn(c(
          "No {.arg greeting} provided to {.fn QueryChat}. Using the LLM {.arg client} to generate one now.",
          "i" = "For faster startup, lower cost, and determinism, consider providing a {.arg greeting} to {.fn QueryChat}.",
          "i" = "You can use your {.help querychat::QueryChat} object's {.fn $generate_greeting} method to generate a greeting."
        ))
        greeting_client <- greeter$build_client(greeting_base)
        stream <- greeting_client$stream_async(GREETING_PROMPT)
        shinychat::chat_greeting(stream, persistent = TRUE)
      }
    } else {
      shinychat::chat_greeting(greeting, persistent = TRUE)
    }

    chat_module <- shinychat::chat_server("chat", pre_built_client, greeting = greeting_arg)

    shiny::observeEvent(
      input$chat_update,
      label = "on_chat_update",
      {
        upd <- input$chat_update
        tbl <- upd$table
        if (!is.null(tbl) && tbl %in% names(tables)) {
          q <- upd$query
          ttl <- upd$title
          tables[[tbl]]$sql(if (nzchar(q %||% "")) q else NULL)
          tables[[tbl]]$title(if (nzchar(ttl %||% "")) ttl else NULL)
          current_table_val(tbl)
        }
      }
    )

    if (enable_bookmarking) {
      shiny::setBookmarkExclude("chat_update")

      shiny::onBookmark(function(state) {
        table_states <- list()
        for (name in names(tables)) {
          table_states[[name]] <- list(
            sql = tables[[name]]$sql(),
            title = tables[[name]]$title()
          )
        }
        state$values$querychat_tables <- table_states
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
        if (!is.null(state$values$querychat_viz_widgets)) {
          restored <- restore_viz_widgets(
            executor,
            restore_record_list(state$values$querychat_viz_widgets),
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

    if (length(data_sources) == 1) {
      first <- tables[[1]]
      list(
        client = chat_module$client,
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
        client = chat_module$client,
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

# A list of records (named lists) bookmarked to the URL comes back from Shiny's
# decoder as a data.frame, because jsonlite simplifies a JSON array of objects
# (simplifyDataFrame = TRUE). Rebuild the list-of-lists shape row by row,
# dropping absent (NA) optional fields. A value restored from a server-side
# store (or already a list) is passed through unchanged.
restore_record_list <- function(x) {
  if (is.null(x)) {
    return(NULL)
  }
  if (is.data.frame(x)) {
    return(lapply(seq_len(nrow(x)), function(i) {
      row <- as.list(x[i, , drop = FALSE])
      row <- lapply(row, function(v) {
        if (length(v) == 1 && is.na(v)) NULL else v
      })
      row[!vapply(row, is.null, logical(1))]
    }))
  }
  as.list(x)
}

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
