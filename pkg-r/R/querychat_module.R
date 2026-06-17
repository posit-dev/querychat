# Main module UI function
mod_ui <- function(
  id,
  ...,
  greeting = NULL,
  enable_cancel = TRUE,
  allow_attachments = TRUE
) {
  ns <- shiny::NS(id)

  if (!is.null(greeting) && any(nzchar(greeting))) {
    greeting <- chat_greeting_persistent(greeting)
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

mod_ui_cards <- function(id, ...) {
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
    viz_dep(),
    shiny::uiOutput(ns("cards"), ...)
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
  enable_bookmarking = FALSE,
  card_placeholder = "Insights will appear here",
  card_layout = NULL
) {
  shiny::moduleServer(id, function(input, output, session) {
    current_table_val <- shiny::reactiveVal(NULL, label = "current_table")
    # Holds a generated greeting so it can be saved and restored on bookmark.
    # Static greetings live in the UI (chat_ui(greeting=)) and persist already.
    # Workaround for posit-dev/shinychat#253: shinychat does not bookmark
    # greetings or expose their state. If that issue is fixed, this reactiveVal,
    # the last_turn() capture below, and the greeting handling in
    # onBookmark/onRestore can be dropped (and the shinychat minimum bumped).
    current_greeting <- shiny::reactiveVal(NULL, label = "current_greeting")
    cards <- shiny::reactiveVal(list(), label = "cards")

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

    cards_summary <- function(card_list) {
      if (length(card_list) == 0) {
        return("No cards on the dashboard.")
      }
      descriptor <- function(cd) {
        if (identical(cd$type, "value_box")) "value_box" else cd$display
      }
      items <- vapply(
        card_list,
        function(cd) sprintf("[%s] %s (%s)", cd$id, cd$title, descriptor(cd)),
        character(1)
      )
      sprintf(
        "%d card%s: %s",
        length(card_list),
        if (length(card_list) == 1) "" else "s",
        paste(items, collapse = ", ")
      )
    }

    manage_card <- function(action, id = NULL, card = NULL) {
      card_list <- shiny::isolate(cards())
      if (action == "get") {
        idx <- which(vapply(
          card_list,
          function(cd) identical(cd$id, id),
          logical(1)
        ))
        return(if (length(idx) > 0) card_list[[idx[[1]]]] else NULL)
      }
      if (action == "remove") {
        card_list <- Filter(function(cd) !identical(cd$id, id), card_list)
      } else if (action == "replace") {
        idx <- which(vapply(
          card_list,
          function(cd) identical(cd$id, id),
          logical(1)
        ))
        if (length(idx) > 0) {
          card_list[[idx[[1]]]] <- card
        } else {
          card_list <- c(card_list, list(card))
        }
      } else {
        card_list <- c(card_list, list(card))
      }
      cards(card_list)
      cards_summary(card_list)
    }

    # Set up the chat object for this session
    check_function(client)
    chat <- client(
      update_dashboard = update_dashboard,
      reset_dashboard = reset_query,
      visualize = on_visualize,
      card = manage_card,
      tools = tools,
      session = session
    )

    if (is.null(greeting)) {
      shiny::observeEvent(
        input$chat_greeting_requested,
        label = "on_greeting_requested",
        {
          # Re-display a restored greeting rather than generating a new one.
          # On empty-chat restore both this and onRestore set the greeting
          # (harmless, identical content); on non-empty restore this never fires,
          # so onRestore is the only path that re-displays.
          if (!is.null(current_greeting())) {
            shinychat::chat_set_greeting(
              "chat",
              chat_greeting_persistent(current_greeting())
            )
            return()
          }
          cli::cli_warn(c(
            "No {.arg greeting} provided to {.fn QueryChat}. Using the LLM {.arg client} to generate one now.",
            "i" = "For faster startup, lower cost, and determinism, consider providing a {.arg greeting} to {.fn QueryChat}.",
            "i" = "You can use your {.help querychat::QueryChat} object's {.fn $generate_greeting} method to generate a greeting."
          ))
          greeter$generate_stream(
            greeting_reactive = current_greeting,
            base = greeting_base
          )
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
      tbl <- input$chat_update$table
      if (!is.null(tbl) && tbl %in% names(tables)) {
        q <- input$chat_update$query
        ttl <- input$chat_update$title
        tables[[tbl]]$sql(if (nzchar(q %||% "")) q else NULL)
        tables[[tbl]]$title(if (nzchar(ttl %||% "")) ttl else NULL)
        current_table_val(tbl)
      }
    })

    output$cards <- shiny::renderUI({
      card_list <- cards()
      if (length(card_list) == 0) {
        if (is.null(card_placeholder)) {
          return(NULL)
        }
        return(htmltools::div(
          class = "querychat-cards-placeholder text-muted",
          card_placeholder
        ))
      }
      card_uis <- lapply(card_list, function(cd) {
        render_card(cd, executor, session)
      })
      card_layout <- card_layout %||% list()
      bslib::layout_columns(
        !!!card_uis,
        col_widths = card_layout$col_widths %||% NA,
        row_heights = card_layout$row_heights %||% NA
      )
    })

    if (enable_bookmarking) {
      shinychat::chat_restore(
        "chat",
        chat,
        restore_ui = FALSE,
        session = session
      )
      shiny::setBookmarkExclude("chat_update", session = session)

      shiny::onBookmark(function(state) {
        table_states <- list()
        for (name in names(tables)) {
          table_states[[name]] <- list(
            sql = tables[[name]]$sql(),
            title = tables[[name]]$title()
          )
        }
        state$values$querychat_tables <- table_states
        if (!is.null(current_greeting())) {
          state$values$querychat_greeting <- current_greeting()
        }
        if (length(viz_widgets) > 0) {
          state$values$querychat_viz_widgets <- viz_widgets
        }
        if (length(cards()) > 0) {
          state$values$querychat_cards <- cards()
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
        if (!is.null(state$values$querychat_greeting)) {
          current_greeting(state$values$querychat_greeting)
          shinychat::chat_set_greeting(
            "chat",
            chat_greeting_persistent(state$values$querychat_greeting),
            session = session
          )
        }
        if (!is.null(state$values$querychat_viz_widgets)) {
          restored <- restore_viz_widgets(
            executor,
            restore_record_list(state$values$querychat_viz_widgets),
            session
          )
          viz_widgets <<- restored
        }
        if (!is.null(state$values$querychat_cards)) {
          cards(state$values$querychat_cards)
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
        cards = cards,
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
        cards = cards,
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

render_card <- function(card, data_source, session) {
  if (identical(card$type, "value_box")) {
    tryCatch(
      {
        df <- data_source$execute_query(card$value)
        scalar <- as.character(df[[1]][1])
        showcase <- if (!is.null(card$icon)) {
          bsicons::bs_icon(card$icon)
        } else {
          NULL
        }
        subtitle_content <- if (!is.null(card$subtitle)) {
          shiny::p(card$subtitle)
        } else {
          NULL
        }
        bslib::value_box(
          title = card$title,
          value = scalar,
          subtitle_content,
          showcase = showcase,
          theme = card$theme %||% "primary"
        )
      },
      error = function(e) {
        bslib::value_box(
          title = card$title,
          value = "Error",
          shiny::p(conditionMessage(e)),
          theme = "danger"
        )
      }
    )
  } else if (identical(card$display, "table")) {
    rlang::check_installed("DT", reason = "for table cards.")
    content_panel <- tryCatch(
      {
        df <- data_source$execute_query(card$value)
        if (inherits(df, "tbl_sql")) {
          df <- dplyr::collect(df)
        }
        DT::datatable(
          df,
          fillContainer = TRUE,
          options = list(pageLength = 10, scrollX = TRUE)
        )
      },
      error = function(e) {
        htmltools::div(conditionMessage(e))
      }
    )
    bslib::navset_card_underline(
      title = card$title,
      full_screen = TRUE,
      footer = if (!is.null(card$footer)) bslib::card_footer(card$footer),
      bslib::nav_spacer(),
      bslib::nav_panel(
        bsicons::bs_icon("table"),
        content_panel
      ),
      bslib::nav_panel(
        bsicons::bs_icon("code-slash"),
        bslib::input_code_editor(
          id = session$ns(paste0("querychat_card_code_", card$id)),
          value = card$value,
          language = "sql",
          read_only = TRUE,
          height = "auto"
        )
      )
    )
  } else if (identical(card$display, "visualization")) {
    widget_id <- paste0("querychat_card_viz_", card$id)
    content_panel <- tryCatch(
      {
        validated <- ggsql::ggsql_validate(card$value)
        spec <- execute_ggsql(data_source, validated)
        session$output[[widget_id]] <- ggsql::renderGgsql(spec)
        htmltools::div(
          class = "querychat-viz-container",
          bslib::as_fill_carrier(),
          ggsql::ggsqlOutput(session$ns(widget_id))
        )
      },
      error = function(e) {
        htmltools::div(conditionMessage(e))
      }
    )
    bslib::navset_card_underline(
      title = card$title,
      full_screen = TRUE,
      footer = if (!is.null(card$footer)) bslib::card_footer(card$footer),
      bslib::nav_spacer(),
      bslib::nav_panel(
        bsicons::bs_icon("bar-chart-fill"),
        content_panel
      ),
      bslib::nav_panel(
        bsicons::bs_icon("code-slash"),
        bslib::input_code_editor(
          id = session$ns(paste0("querychat_card_code_", card$id)),
          value = card$value,
          language = "ggsql",
          read_only = TRUE,
          height = "auto"
        )
      )
    )
  } else {
    bslib::card(
      bslib::card_header(card$title),
      bslib::card_body(shiny::markdown(card$value)),
      if (!is.null(card$footer)) bslib::card_footer(card$footer)
    )
  }
}
