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

# Valid bookmark categories
BOOKMARK_CATEGORIES <- c("conversation", "cards")

# Normalize the `bookmark_enable` argument to a character vector of
# categories. Accepts TRUE (all), FALSE/NULL (none), or a character subset of
# `BOOKMARK_CATEGORIES`.
normalize_bookmark_categories <- function(bookmark_enable) {
  if (is.null(bookmark_enable) || length(bookmark_enable) == 0) {
    return(character(0))
  }
  if (is.logical(bookmark_enable)) {
    if (length(bookmark_enable) != 1 || is.na(bookmark_enable)) {
      cli::cli_abort(
        "{.arg bookmark_enable} must be {.code TRUE}, {.code FALSE}, or a character vector of {.or {.val {BOOKMARK_CATEGORIES}}}."
      )
    }
    return(if (bookmark_enable) BOOKMARK_CATEGORIES else character(0))
  }
  if (is.character(bookmark_enable)) {
    return(rlang::arg_match(
      bookmark_enable,
      BOOKMARK_CATEGORIES,
      multiple = TRUE
    ))
  }
  cli::cli_abort(
    "{.arg bookmark_enable} must be {.code TRUE}, {.code FALSE}, or a character vector of {.or {.val {BOOKMARK_CATEGORIES}}}."
  )
}

# Resolve the Shiny bookmark store from the (possibly NULL) `bookmark_store`
# argument and the normalized bookmark categories. Returns one of "url",
# "server", "disable", or NULL. NULL means "defer to whatever the app author
# already set via shiny::enableBookmarking()" -- passing NULL to
# shiny::shinyApp(enableBookmarking=) makes Shiny latch that existing option.
#
# Only meaningful at the app level (the layer that owns the shinyApp() call);
# `$server()` never sets a store.
resolve_bookmark_store <- function(bookmark_store, bookmark_cats) {
  # Nothing to save.
  if (length(bookmark_cats) == 0) {
    return("disable")
  }
  # The author chose a store explicitly.
  if (!is.null(bookmark_store)) {
    return(rlang::arg_match0(bookmark_store, c("url", "server", "disable")))
  }
  # The author already called shiny::enableBookmarking(); defer to it.
  if (!is.null(shiny::getShinyOption("bookmarkStore"))) {
    return(NULL)
  }
  # The chat transcript is unbounded and overflows URL length limits, so a
  # conversation bookmark needs server storage.
  if ("conversation" %in% bookmark_cats) {
    return("server")
  }
  # On a hosting platform, server storage is available and reliable.
  hosted <- tolower(Sys.getenv("R_CONFIG_ACTIVE")) %in%
    c("connect", "shinyapps", "rsconnect", "connect_cloud", "rstudio_cloud")
  if (hosted) {
    return("server")
  }
  # Cards-only, run locally: small payload that is shareable via the URL.
  "url"
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
  bookmark_enable = FALSE,
  card_placeholder = "Insights will appear here",
  seed_cards = NULL
) {
  bookmark_cats <- normalize_bookmark_categories(bookmark_enable)
  shiny::moduleServer(id, function(input, output, session) {
    current_table_val <- shiny::reactiveVal(NULL, label = "current_table")
    # Holds a generated greeting so it can be saved and restored on bookmark.
    # Static greetings live in the UI (chat_ui(greeting=)) and persist already.
    # Workaround for posit-dev/shinychat#253: shinychat does not bookmark
    # greetings or expose their state. If that issue is fixed, this reactiveVal,
    # the last_turn() capture below, and the greeting handling in
    # onBookmark/onRestore can be dropped (and the shinychat minimum bumped).
    current_greeting <- shiny::reactiveVal(NULL, label = "current_greeting")

    # Build the initial card list from seed_cards (author-supplied at $new()
    # time). This is the INITIAL state only; the URL reader and onRestore both
    # call cards(...) and will overwrite it when they fire.
    initial_cards <- if (is.null(seed_cards)) {
      list()
    } else {
      # Validate each seed card and assign unique ids within this batch.
      # We can't use new_card_id() here because it reads from the live cards
      # store (via manage_card), which doesn't exist yet. Instead, we track
      # used ids ourselves and generate unique ones via random_hex(2).
      used_ids <- character(0)
      validated <- vector("list", length(seed_cards))
      for (i in seq_along(seed_cards)) {
        card <- tryCatch(
          validate_and_build_card(executor, seed_cards[[i]]),
          error = function(e) {
            cli::cli_abort(
              "Seed card {i} is invalid: {conditionMessage(e)}",
              call = NULL
            )
          }
        )
        # Prefer the card's own id if supplied and not already used; otherwise
        # generate a fresh one.
        preferred_id <- seed_cards[[i]][["id"]]
        id <- if (
          !is.null(preferred_id) &&
            is.character(preferred_id) &&
            nzchar(preferred_id) &&
            !preferred_id %in% used_ids
        ) {
          preferred_id
        } else {
          repeat {
            candidate <- random_hex(2)
            if (!candidate %in% used_ids) break
          }
          candidate
        }
        used_ids <- c(used_ids, id)
        card$id <- id
        validated[[i]] <- card
      }
      validated
    }
    cards <- shiny::reactiveVal(initial_cards, label = "cards")

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

    manage_card <- function(action, id = NULL, card = NULL) {
      card_list <- shiny::isolate(cards())
      if (action == "get") {
        if (is.null(id)) {
          return(card_list)
        }
        idx <- which(map_lgl(
          card_list,
          function(cd) identical(cd$id, id)
        ))
        return(if (length(idx) > 0) card_list[[idx[[1]]]] else NULL)
      }
      if (action == "remove") {
        card_list <- discard(card_list, function(cd) identical(cd$id, id))
      } else if (action == "replace") {
        idx <- which(map_lgl(card_list, function(cd) identical(cd$id, id)))
        if (length(idx) > 0) {
          card_list[[idx[[1]]]] <- card
        } else {
          card_list <- c(card_list, list(card))
        }
      } else {
        card_list <- c(card_list, list(card))
      }
      cards(card_list)
      invisible(card_list)
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

    # Seed cards from the `querychat_cards` query parameter if present.
    # session$ns("querychat_cards") == paste0(module_id, "-querychat_cards"),
    # which is the key written by $cards_url() / $cards_set_url().
    url_cards_seeded <- FALSE
    local({
      qs <- shiny::isolate(
        shiny::parseQueryString(session$clientData$url_search)
      )
      key <- session$ns("querychat_cards")
      raw <- qs[[key]]
      if (!is.null(raw) && nzchar(raw)) {
        decoded <- tryCatch(
          payload_to_cards(raw),
          error = function(e) {
            cli::cli_warn(
              c(
                "Could not decode {.arg querychat_cards} URL parameter.",
                "x" = conditionMessage(e)
              )
            )
            NULL
          }
        )
        if (!is.null(decoded)) {
          validated <- vector("list", length(decoded))
          n_valid <- 0L
          for (i in seq_along(decoded)) {
            tryCatch(
              {
                card <- validate_and_build_card(executor, decoded[[i]])
                card$id <- new_card_id(manage_card)
                n_valid <- n_valid + 1L
                validated[[n_valid]] <- card
              },
              error = function(e) {
                cli::cli_warn(
                  "Skipping URL card {i}: {conditionMessage(e)}",
                  .envir = parent.env(environment())
                )
              }
            )
          }
          if (n_valid > 0L) {
            cards(validated[seq_len(n_valid)])
            url_cards_seeded <<- TRUE
          }
        }
      }
    })

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
      runs <- coalesce_card_runs(card_list)
      blocks <- lapply(runs, function(run) {
        is_vb <- identical(run$kind, "value_box")
        uis <- lapply(run$cards, function(cd) {
          render_card(cd, executor, session)
        })
        if (is_vb) {
          bslib::layout_column_wrap(width = "200px", !!!uis)
        } else {
          bslib::layout_column_wrap(
            width = "400px",
            heights_equal = "row",
            !!!uis
          )
        }
      })
      htmltools::tagList(!!!blocks)
    })

    if (length(bookmark_cats) > 0) {
      shiny::setBookmarkExclude("chat_update", session = session)
      bookmark_conversation <- "conversation" %in% bookmark_cats
      bookmark_cards <- "cards" %in% bookmark_cats

      # Bookmark state keys. Shiny's module scope automatically namespaces these
      # per module id (it writes `state$values[[ns(key)]]` on save and strips the
      # prefix on restore), so multiple QueryChat instances do not collide and we
      # must NOT pre-namespace with session$ns() (that double-prefixes the key).
      key_tables <- "querychat_tables"
      key_greeting <- "querychat_greeting"
      key_viz_widgets <- "querychat_viz_widgets"
      key_cards <- "querychat_cards"

      if (bookmark_conversation) {
        # shinychat owns the transcript state and the bookmark trigger
        # (observes chat input/response -> doBookmark) plus updateQueryString.
        shinychat::chat_restore(
          "chat",
          chat,
          restore_ui = FALSE,
          session = session
        )
      } else {
        # Cards-only: drive the bookmark trigger ourselves when cards change,
        # mirroring shinychat's onBookmarked -> updateQueryString.
        shiny::observeEvent(cards(), ignoreInit = TRUE, {
          session$doBookmark()
        })
        shiny::withReactiveDomain(
          session$rootScope(),
          shiny::onBookmarked(function(url) {
            shiny::updateQueryString(url)
          })
        )
      }

      shiny::onBookmark(function(state) {
        if (bookmark_conversation) {
          table_states <- list()
          for (name in names(tables)) {
            table_states[[name]] <- list(
              sql = tables[[name]]$sql(),
              title = tables[[name]]$title()
            )
          }
          state$values[[key_tables]] <- table_states
          if (!is.null(current_greeting())) {
            state$values[[key_greeting]] <- current_greeting()
          }
          if (length(viz_widgets) > 0) {
            state$values[[key_viz_widgets]] <- viz_widgets
          }
        }
        if (bookmark_cards && length(cards()) > 0) {
          state$values[[key_cards]] <- cards()
        }
      })

      shiny::onRestore(function(state) {
        if (bookmark_conversation) {
          if (!is.null(state$values[[key_tables]])) {
            last_restored <- NULL
            for (name in names(state$values[[key_tables]])) {
              tbl_state <- state$values[[key_tables]][[name]]
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
          if (!is.null(state$values[[key_greeting]])) {
            current_greeting(state$values[[key_greeting]])
            shinychat::chat_set_greeting(
              "chat",
              chat_greeting_persistent(state$values[[key_greeting]]),
              session = session
            )
          }
          if (!is.null(state$values[[key_viz_widgets]])) {
            restored <- restore_viz_widgets(
              executor,
              restore_record_list(state$values[[key_viz_widgets]]),
              session
            )
            viz_widgets <<- restored
          }
        }
        # URL param takes precedence: skip bookmark restore when URL seeded cards.
        if (
          bookmark_cards &&
            !is.null(state$values[[key_cards]]) &&
            !isTRUE(url_cards_seeded)
        ) {
          cards(restore_record_list(state$values[[key_cards]]))
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
      compact(lapply(row, function(v) {
        if (length(v) == 1 && is.na(v)) NULL else v
      }))
    }))
  }
  as.list(x)
}

# Migrate legacy card field names from persisted state. Copies `caption` to
# `text` (for non-markdown cards) and `value` to `query` when the new field is
# absent, so bookmarked or server-restored cards created before the rename
# still render correctly.
migrate_card_fields <- function(card) {
  if (!is.null(card$caption) && is.null(card$text) && !identical(card$display, "markdown")) {
    card$text <- card$caption
  }
  card$caption <- NULL
  if (!is.null(card$value) && is.null(card$query)) {
    card$query <- card$value
  }
  card$value <- NULL
  card
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

# Split a flat card list into consecutive runs of the same kind.
# Returns a list of run objects: list(kind = "value_box" | "content", cards = list(...))
coalesce_card_runs <- function(card_list) {
  if (length(card_list) == 0) {
    return(list())
  }
  kinds <- map_chr(card_list, function(cd) {
    if (identical(cd$display, "value_box")) "value_box" else "content"
  })
  runs <- list()
  run_start <- 1L
  for (i in seq_along(kinds)) {
    if (i == length(kinds) || kinds[i + 1L] != kinds[i]) {
      runs <- c(
        runs,
        list(list(
          kind = kinds[i],
          cards = card_list[run_start:i]
        ))
      )
      run_start <- i + 1L
    }
  }
  runs
}

card_header_with_icon <- function(title, icon) {
  if (!is.null(icon)) {
    bslib::card_header(bsicons::bs_icon(icon), title)
  } else {
    bslib::card_header(title)
  }
}

navset_title_with_icon <- function(title, icon) {
  if (!is.null(icon)) {
    htmltools::tagList(bsicons::bs_icon(icon), title)
  } else {
    title
  }
}

render_card <- function(card, executor, session) {
  card <- migrate_card_fields(card)
  tryCatch(
    switch(
      card$display %||% "markdown",
      value_box = render_card_value_box(card, executor, session),
      table = render_card_table(card, executor, session),
      visualization = render_card_visualization(card, executor, session),
      render_card_markdown(card, executor, session)
    ),
    error = function(e) render_card_error(card, conditionMessage(e))
  )
}

render_card_error <- function(card, message) {
  bslib::card(
    class = "border-danger",
    card_header_with_icon(card$title, card$icon),
    bslib::card_body(class = "text-danger", message)
  )
}

render_card_value_box <- function(card, executor, session) {
  col_or <- function(row, col_name, fallback) {
    val <- row[[col_name]]
    if (!is.null(val) && !is.na(val) && nzchar(as.character(val))) {
      as.character(val)
    } else {
      fallback
    }
  }

  df <- executor$execute_query(card$query)
  row <- as.list(df[1, , drop = FALSE])

  scalar <- if ("value" %in% names(row)) {
    as.character(row[["value"]])
  } else {
    as.character(row[[1]])
  }

  effective_title <- col_or(row, "title", card$title)
  effective_text <- col_or(row, "text", card$text)
  effective_theme <- col_or(row, "theme", card$theme %||% "primary")
  effective_icon <- col_or(row, "icon", card$icon)

  showcase <- if (!is.null(effective_icon) && nzchar(effective_icon)) {
    bsicons::bs_icon(effective_icon)
  }
  subtitle_content <- if (
    !is.null(effective_text) && nzchar(effective_text)
  ) {
    shiny::p(effective_text)
  }

  sql_viewer <- htmltools::div(
    class = "querychat-vb-sql",
    htmltools::p(class = "h5 mb-2 mt-4", "SQL Query"),
    bslib::input_code_editor(
      id = session$ns(paste0("querychat_card_code_", card$id)),
      value = card$query,
      language = "sql",
      read_only = TRUE,
      height = "200px"
    )
  )

  bslib::value_box(
    title = effective_title,
    value = scalar,
    subtitle_content,
    sql_viewer,
    showcase = showcase,
    theme = effective_theme,
    full_screen = TRUE
  )
}

render_card_table <- function(card, executor, session) {
  rlang::check_installed("DT", reason = "for table cards.")
  df <- executor$execute_query(card$query)
  if (inherits(df, "tbl_sql")) {
    df <- dplyr::collect(df)
  }
  content_panel <- DT::datatable(
    df,
    fillContainer = TRUE,
    options = list(pageLength = 10, scrollX = TRUE)
  )
  bslib::navset_card_underline(
    title = navset_title_with_icon(card$title, card$icon),
    full_screen = TRUE,
    footer = if (!is.null(card$text)) bslib::card_footer(card$text),
    bslib::nav_spacer(),
    bslib::nav_panel(
      bsicons::bs_icon("table"),
      content_panel
    ),
    bslib::nav_panel(
      bsicons::bs_icon("code-slash"),
      bslib::input_code_editor(
        id = session$ns(paste0("querychat_card_code_", card$id)),
        value = card$query,
        language = "sql",
        read_only = TRUE,
        height = "auto"
      )
    )
  )
}

render_card_visualization <- function(card, executor, session) {
  widget_id <- paste0("querychat_card_viz_", card$id)
  validated <- ggsql::ggsql_validate(card$query)
  spec <- execute_ggsql(executor, validated)
  session$output[[widget_id]] <- ggsql::renderGgsql(spec)
  content_panel <- htmltools::div(
    class = "querychat-viz-container",
    bslib::as_fill_carrier(),
    ggsql::ggsqlOutput(session$ns(widget_id))
  )
  bslib::navset_card_underline(
    title = navset_title_with_icon(card$title, card$icon),
    full_screen = TRUE,
    footer = if (!is.null(card$text)) bslib::card_footer(card$text),
    bslib::nav_spacer(),
    bslib::nav_panel(
      bsicons::bs_icon("bar-chart-fill"),
      content_panel
    ),
    bslib::nav_panel(
      bsicons::bs_icon("code-slash"),
      bslib::input_code_editor(
        id = session$ns(paste0("querychat_card_code_", card$id)),
        value = card$query,
        language = "ggsql",
        read_only = TRUE,
        height = "auto"
      )
    )
  )
}

render_card_markdown <- function(card, executor, session) {
  rendered_text <- if (!is.null(card$query)) {
    df <- executor$execute_query(card$query)
    row <- as.list(df[1, , drop = FALSE])
    whisker::whisker.render(card$text, row)
  } else {
    card$text
  }

  if (!is.null(card$query)) {
    bslib::navset_card_underline(
      title = navset_title_with_icon(card$title, card$icon),
      full_screen = TRUE,
      bslib::nav_spacer(),
      bslib::nav_panel(
        bsicons::bs_icon("file-text"),
        bslib::card_body(shiny::markdown(rendered_text))
      ),
      bslib::nav_panel(
        bsicons::bs_icon("code-slash"),
        bslib::input_code_editor(
          id = session$ns(paste0("querychat_card_code_", card$id)),
          value = card$query,
          language = "sql",
          read_only = TRUE,
          height = "auto"
        )
      )
    )
  } else {
    bslib::card(
      card_header_with_icon(card$title, card$icon),
      bslib::card_body(shiny::markdown(rendered_text))
    )
  }
}
