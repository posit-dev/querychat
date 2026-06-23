# ToolDef accessors (mirrors commons pattern using S7 props)
td_name <- function(td) S7::prop(td, "name")
td_description <- function(td) S7::prop(td, "description")
td_title <- function(td) {
  ann <- S7::prop(td, "annotations")
  ann$title %||% humanize_measure_name(td_name(td))
}
td_properties <- function(td) {
  S7::prop(S7::prop(td, "arguments"), "properties")
}

humanize_measure_name <- function(x) {
  x <- gsub("_", " ", x, fixed = TRUE)
  paste0(toupper(substr(x, 1, 1)), substr(x, 2, nchar(x)))
}

validate_measures <- function(measures, call = rlang::caller_env()) {
  ok <- vapply(measures, inherits, logical(1), "ellmer::ToolDef")
  if (!all(ok)) {
    cli::cli_abort(
      "Every item in {.arg measures} must be an {.cls ellmer::ToolDef} created by {.fn ellmer::tool}.",
      call = call
    )
  }
  invisible(measures)
}

lexical_rank <- function(query, catalog, n = 5) {
  query_words <- unique(tolower(strsplit(query, "\\W+")[[1]]))
  query_words <- query_words[nzchar(query_words)]
  if (length(query_words) == 0) return(integer(0))
  scores <- vapply(catalog, function(text) {
    text_words <- unique(tolower(strsplit(text, "\\W+")[[1]]))
    sum(query_words %in% text_words)
  }, numeric(1))
  idx <- order(scores, decreasing = TRUE)
  idx <- idx[scores[idx] > 0]
  head(idx, n)
}

measure_arg_line <- function(name, type) {
  cls <- class(type)[[1]]
  kind <- switch(cls,
    "ellmer::TypeEnum" = sprintf("one of {%s}", paste(S7::prop(type, "values"), collapse = ", ")),
    "ellmer::TypeBasic" = S7::prop(type, "type"),
    "string"
  )
  required <- if (isTRUE(S7::prop(type, "required"))) "required" else "optional"
  desc <- S7::prop(type, "description") %||% ""
  sprintf("  - %s (%s, %s) %s", name, kind, required, desc)
}

measure_schema_text <- function(td) {
  props <- td_properties(td)
  args <- if (length(props) == 0) {
    "  (no arguments)"
  } else {
    paste(
      vapply(names(props), function(nm) measure_arg_line(nm, props[[nm]]), character(1)),
      collapse = "\n"
    )
  }
  sprintf("### %s\n%s\n\narguments:\n%s", td_name(td), td_description(td), args)
}

measures_search_text <- function(measures, query) {
  if (length(measures) == 0) {
    return("No measures are registered.")
  }
  catalog <- vapply(
    measures,
    function(td) paste(td_name(td), td_description(td)),
    character(1)
  )
  hits <- lexical_rank(query, catalog, n = 5)
  if (length(hits) == 0) {
    return(sprintf('No measure matches "%s".', query))
  }
  blocks <- vapply(measures[hits], measure_schema_text, character(1))
  paste(blocks, collapse = "\n\n")
}

# Tool builders

tool_search_measures <- function(measures) {
  ellmer::tool(
    function(query) measures_search_text(measures, query),
    interpolate_package("tool-search-measures.md"),
    name = "querychat_search_measures",
    arguments = list(
      query = ellmer::type_string("What you want to compute, in plain language.")
    ),
    annotations = ellmer::tool_annotations(
      title = "Search measures",
      icon = search_icon(),
      read_only_hint = TRUE
    )
  )
}

tool_call_measure <- function(measures) {
  ellmer::tool(
    function(name, arguments = "{}") {
      td <- measures[[name]]
      if (is.null(td)) {
        available <- paste0('"', names(measures), '"', collapse = ", ")
        cli::cli_abort(c(
          "No measure named {.val {name}}.",
          "i" = "Registered measures: {available}."
        ))
      }
      args <- parse_measure_args(arguments)
      result <- do.call(td, args)
      body <- format_measure_value(result)
      ellmer::ContentToolResult(
        value = body,
        extra = list(display = list(
          title = sprintf("Measure: %s", td_title(td)),
          icon = shield_check_icon(),
          open = TRUE,
          show_request = FALSE
        ))
      )
    },
    interpolate_package("tool-call-measure.md"),
    name = "querychat_call_measure",
    arguments = list(
      name = ellmer::type_string("The measure name exactly as returned by querychat_search_measures."),
      arguments = ellmer::type_string(
        'A JSON object of the measure\'s arguments, e.g. {"region": "West"}. Use {} for no arguments.',
        required = FALSE
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Measure",
      icon = shield_check_icon()
    )
  )
}

# Helpers for argument parsing and value formatting

parse_measure_args <- function(x) {
  if (is.null(x) || identical(x, "") || identical(x, "{}")) return(list())
  if (is.list(x)) return(x)
  if (is.na(x) || length(x) == 0) return(list())
  as.list(jsonlite::fromJSON(x, simplifyVector = TRUE))
}

format_measure_value <- function(value) {
  if (inherits(value, "tbl_sql")) {
    rlang::check_installed("dplyr")
    value <- dplyr::collect(value)
  }
  if (is.data.frame(value)) {
    return(df_to_markdown(value))
  }
  if (is.atomic(value) && length(value) <= 20) {
    return(paste(format(value, trim = TRUE, big.mark = ","), collapse = ", "))
  }
  paste(utils::capture.output(print(value)), collapse = "\n")
}

df_to_markdown <- function(df, max_rows = 50) {
  rlang::check_installed("knitr", reason = "to format data frame results as markdown tables.")
  if (nrow(df) > max_rows) {
    df <- head(df, max_rows)
  }
  paste(knitr::kable(df, format = "markdown"), collapse = "\n")
}

derive_measure_tag <- function(turn_calls) {
  measure_tools <- c(
    "querychat_search_measures", "querychat_call_measure",
    "querychat_run_measures", "querychat_prepare_visualization",
    "querychat_visualize_measures"
  )
  sql_tools <- c("querychat_query", "querychat_update_dashboard")
  if (any(sql_tools %in% turn_calls)) return("B")
  if (any(measure_tools %in% turn_calls)) return("A")
  NA_character_
}

trusted_icon_svg <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16"><path d="M5.338 1.59a61 61 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.7 10.7 0 0 0 2.287 2.233c.346.244.652.42.893.533q.18.085.293.118a1 1 0 0 0 .201 0q.114-.034.294-.118c.24-.113.547-.29.893-.533a10.7 10.7 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524z"/><path d="M10.854 5.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 7.793l2.646-2.647a.5.5 0 0 1 .708 0z"/></svg>'
}

warning_icon_svg <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16"><path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.15.15 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.2.2 0 0 1-.054.06.1.1 0 0 1-.066.017H1.146a.1.1 0 0 1-.066-.017.2.2 0 0 1-.054-.06.18.18 0 0 1 .002-.183L7.884 2.073a.15.15 0 0 1 .054-.057m1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767z"/><path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0M7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/></svg>'
}

provenance_pill_html <- function(tag) {
  if (is.na(tag)) return(NULL)
  switch(
    tag,
    A = htmltools::tags$span(
      class = "querychat-answer-pill querychat-answer-pill-trusted",
      `data-querychat-tooltip` = "This answer comes from a trusted measure registered by a domain expert.",
      tabindex = "0",
      htmltools::HTML(trusted_icon_svg()),
      htmltools::tags$span("Verified answer")
    ),
    B = htmltools::tags$span(
      class = "querychat-answer-pill querychat-answer-pill-caution",
      `data-querychat-tooltip` = "This answer was generated from available data, but was not produced by a trusted measure.",
      htmltools::HTML(warning_icon_svg()),
      htmltools::tags$span("AI can be wrong.")
    ),
    NULL
  )
}

# Icons (inline SVG strings)

shield_check_icon <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-shield-check" viewBox="0 0 16 16"><path d="M5.338 1.59a61 61 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.7 10.7 0 0 0 2.287 2.233c.346.244.652.42.893.533q.18.085.293.118a1 1 0 0 0 .101.025 1 1 0 0 0 .1-.025q.114-.034.294-.118c.24-.113.547-.29.893-.533a10.7 10.7 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.8 11.8 0 0 1-2.517 2.453 7 7 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7 7 0 0 1-1.048-.625 11.8 11.8 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 63 63 0 0 1 5.072.56z"/><path d="M10.854 5.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 7.793l2.646-2.647a.5.5 0 0 1 .708 0z"/></svg>'
}

search_icon <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/></svg>'
}

parse_calls_json <- function(x) {
  if (is.null(x) || identical(x, "[]") || identical(x, "")) return(list())
  if (is.list(x)) return(x)
  parsed <- jsonlite::fromJSON(x, simplifyVector = FALSE)
  if (is.data.frame(parsed)) {
    lapply(seq_len(nrow(parsed)), function(i) as.list(parsed[i, ]))
  } else {
    parsed
  }
}

col_schema_text <- function(df) {
  types <- vapply(df, function(col) class(col)[[1]], character(1))
  paste(
    sprintf("  - %s (%s)", names(types), types),
    collapse = "\n"
  )
}

tool_run_measures <- function(measures, ephemeral_db) {
  force(measures)
  force(ephemeral_db)
  ellmer::tool(
    function(calls) {
      call_list <- parse_calls_json(calls)
      lines <- character()
      for (entry in call_list) {
        name <- entry[["name"]]
        args <- parse_measure_args(entry[["arguments"]] %||% list())
        td <- measures[[name]]
        if (is.null(td)) {
          lines <- c(lines, sprintf("ERROR: No measure named '%s'.", name))
          next
        }
        value <- do.call(td, args)
        if (inherits(value, "tbl_sql")) {
          rlang::check_installed("dplyr")
          value <- dplyr::collect(value)
        }
        if (is.data.frame(value)) {
          tbl_name <- ephemeral_db$register(value)
          schema <- col_schema_text(value)
          lines <- c(lines, sprintf(
            "Measure '%s' → table `%s` (%d rows)\nColumns:\n%s",
            name, tbl_name, nrow(value), schema
          ))
        } else {
          formatted <- format_measure_value(value)
          lines <- c(lines, sprintf("Measure '%s' → %s", name, formatted))
        }
      }
      if (length(lines) == 0) {
        lines <- "No measures were executed."
      }
      summary <- paste(lines, collapse = "\n\n")
      ellmer::ContentToolResult(
        value = summary,
        extra = list(display = list(
          title = "Run measures",
          icon = shield_check_icon(),
          open = TRUE,
          show_request = FALSE
        ))
      )
    },
    interpolate_package("tool-run-measures.md"),
    name = "querychat_run_measures",
    arguments = list(
      calls = ellmer::type_string(
        'JSON array of {"name": "<measure_name>", "arguments": {<args>}} objects.'
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Run measures",
      icon = shield_check_icon()
    )
  )
}

tool_prepare_visualization <- function(ephemeral_db) {
  force(ephemeral_db)
  ellmer::tool(
    function(preparations) {
      prep_list <- parse_calls_json(preparations)
      staged <- character()
      run_tables <- grep("^_run_", ephemeral_db$list_tables(), value = TRUE)
      for (entry in prep_list) {
        name <- entry[["name"]]
        query <- entry[["query"]]
        ephemeral_db$create_table(name, query)
        staged <- c(staged, name)
      }
      ephemeral_db$drop_tables(run_tables)
      summary <- if (length(staged) > 0) {
        sprintf(
          "Staged tables ready for visualization: %s",
          paste0('"', staged, '"', collapse = ", ")
        )
      } else {
        "No tables staged."
      }
      ellmer::ContentToolResult(
        value = summary,
        extra = list(display = list(
          title = "Prepare visualization",
          open = FALSE,
          show_request = FALSE
        ))
      )
    },
    interpolate_package("tool-prepare-visualization.md"),
    name = "querychat_prepare_visualization",
    arguments = list(
      preparations = ellmer::type_string(
        'JSON array of {"name": "<table_name>", "query": "<SELECT ...>"} objects.'
      )
    ),
    annotations = ellmer::tool_annotations(title = "Prepare visualization")
  )
}

tool_visualize_measures <- function(ephemeral_db, session, update_fn = function(data) {}) {
  force(ephemeral_db)
  force(session)
  force(update_fn)
  ellmer::tool(
    function(ggsql, title = "") {
      rlang::check_installed("ggsql", reason = "for measure visualization.")
      staged_tables <- grep("^_run_", ephemeral_db$list_tables(), invert = TRUE, value = TRUE)
      on.exit(ephemeral_db$drop_tables(staged_tables), add = TRUE, after = TRUE)

      validated <- ggsql::ggsql_validate(ggsql)
      has_visual <- ggsql::ggsql_has_visual(validated)
      if (!has_visual) {
        cli::cli_abort("Query must include a VISUALISE clause.")
      }
      if (!isTRUE(validated$valid)) {
        cli::cli_abort(collapse_validation_errors(validated))
      }

      ephemeral_executor <- list(
        execute_query = function(sql) ephemeral_db$execute(sql)
      )
      spec <- execute_ggsql(ephemeral_executor, validated)

      widget_id <- paste0("querychat_viz_", random_hex())

      if (is.null(session)) {
        print(spec)
        update_fn(list(ggsql = ggsql, title = title, widget_id = widget_id))
        return(ellmer::ContentToolResult(value = "Chart displayed."))
      }

      session$output[[widget_id]] <- ggsql::renderGgsql(spec)
      viz_container <- htmltools::div(
        class = "querychat-viz-container",
        bslib::as_fill_carrier(),
        ggsql::ggsqlOutput(session$ns(widget_id)),
        viz_dep()
      )

      png_file <- tempfile(fileext = ".png")
      on.exit(unlink(png_file), add = TRUE, after = TRUE)
      png_content <- tryCatch(
        {
          ggsql::ggsql_save(spec, png_file, width = 500, height = 300)
          ellmer::content_image_file(png_file)
        },
        error = function(e) NULL
      )

      title_display <- if (nzchar(title)) sprintf(" with title '%s'", title) else ""
      text <- sprintf("Chart displayed%s.", title_display)
      value <- if (!is.null(png_content)) list(ellmer::ContentText(text), png_content) else text

      update_fn(list(ggsql = ggsql, title = title, widget_id = widget_id))

      ellmer::ContentToolResult(
        value = value,
        extra = list(display = list(
          html = viz_container,
          title = if (nzchar(title)) title else "Measure Visualization",
          show_request = FALSE,
          open = querychat_tool_starts_open("visualize"),
          full_screen = TRUE,
          icon = viz_icon()
        ))
      )
    },
    interpolate_package("tool-visualize-measures.md"),
    name = "querychat_visualize_measures",
    arguments = list(
      ggsql = ellmer::type_string(
        "A full ggsql query referencing the tables created by querychat_prepare_visualization."
      ),
      title = ellmer::type_string(
        "A brief title for the visualization card.",
        required = FALSE
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Visualize measures",
      icon = viz_icon()
    )
  )
}

new_ephemeral_db <- function() {
  rlang::check_installed("duckdb", reason = "for measure visualization support.")
  con <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
  run_counter <- 0L

  list(
    register = function(df) {
      run_counter <<- run_counter + 1L
      name <- paste0("_run_", run_counter)
      duckdb::duckdb_register(con, name, df)
      name
    },
    execute = function(sql) {
      DBI::dbGetQuery(con, sql)
    },
    create_table = function(name, sql) {
      DBI::dbExecute(
        con,
        sprintf('CREATE OR REPLACE TABLE "%s" AS %s', name, sql)
      )
      invisible(NULL)
    },
    drop_tables = function(names) {
      for (nm in names) {
        tryCatch(
          DBI::dbExecute(con, sprintf('DROP TABLE IF EXISTS "%s"', nm)),
          error = function(e) NULL
        )
        tryCatch(
          duckdb::duckdb_unregister(con, nm),
          error = function(e) NULL
        )
      }
      invisible(NULL)
    },
    list_tables = function() DBI::dbListTables(con),
    cleanup = function() {
      tryCatch(
        DBI::dbDisconnect(con, shutdown = TRUE),
        error = function(e) NULL
      )
      invisible(NULL)
    }
  )
}
