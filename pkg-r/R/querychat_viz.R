# Create a visualization tool for the dashboard.
# @param data_source A querychat DataSource R6 object.
# @param update_fn A function that will be called with a list containing
#   `ggsql`, `title`, and `widget_id` when a visualization succeeds.
tool_visualize_dashboard <- function(
  data_source,
  session,
  update_fn = function(data) {
  },
  has_tool_query = FALSE
) {
  check_data_source(data_source)
  check_function(update_fn)
  if (is.null(session)) {
    cli::cli_abort(
      "{.fn tool_visualize_dashboard} requires an active Shiny {.arg session}."
    )
  }

  db_type <- data_source$get_db_type()

  ellmer::tool(
    tool_visualize_impl(data_source, session, update_fn),
    name = "querychat_visualize",
    description = render_viz_tool_description(
      db_type = db_type,
      has_tool_query = has_tool_query
    ),
    arguments = list(
      ggsql = ellmer::type_string(
        ellmer::interpolate(
          "A full ggsql query. Must include a VISUALISE clause and at least one DRAW clause. The SELECT portion uses {{db_type}} SQL; VISUALISE and MAPPING accept column names only, not expressions. Do NOT include `LABEL title => ...` in the query — use the `title` parameter instead.",
          db_type = db_type
        )
      ),
      title = ellmer::type_string(
        "A brief, user-friendly title for this visualization. This is displayed as the card header above the chart."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Query Visualization",
      icon = viz_icon()
    )
  )
}

tool_visualize_impl <- function(data_source, session, update_fn) {
  force(data_source)
  force(session)
  force(update_fn)

  function(ggsql, title) {
    visualize_result(data_source, session, update_fn, ggsql, title)
  }
}

# Execute a ggsql query and return a ContentToolResult with a visualization.
# @param data_source A querychat DataSource R6 object.
# @param update_fn Callback called with list(ggsql, title, widget_id) on success.
# @param ggsql_str The full ggsql query string.
# @param title A title for the visualization.
visualize_result <- function(
  data_source,
  session,
  update_fn,
  ggsql_str,
  title
) {
  rlang::check_installed("ggsql", reason = "for visualization support.")

  validated <- ggsql::ggsql_validate(ggsql_str)
  has_visual <- ggsql::ggsql_has_visual(validated)

  if (!has_visual) {
    has_keyword <- grepl("VISUALIS[EZ]", ggsql_str, ignore.case = TRUE)
    if (has_keyword) {
      rlang::abort(
        "VISUALISE clause was not recognized. VISUALISE and MAPPING accept column names only — no SQL expressions, CAST(), or functions. Move all data transformations to the SELECT clause, then reference the resulting column by name in VISUALISE."
      )
    }
    rlang::abort(
      "Query must include a VISUALISE clause. Use querychat_query for queries without visualization."
    )
  }

  spec <- execute_ggsql(data_source, validated)

  # Generate a unique widget ID without requiring the uuid package
  widget_id <- paste0(
    "querychat_viz_",
    format(as.hexmode(sample.int(.Machine$integer.max, 1)), width = 8)
  )

  # Register a dynamic Shiny output via ggsql's official binding
  viz_container <- NULL
  if (!is.null(session)) {
    session$output[[widget_id]] <- ggsql::renderGgsql(spec)
    viz_container <- htmltools::div(
      class = "querychat-viz-container",
      ggsql::ggsqlOutput(session$ns(widget_id)),
      viz_dep()
    )
  }

  # PNG for LLM feedback (best-effort; requires V8 + rsvg)
  png_content <- tryCatch(
    {
      png_file <- tempfile(fileext = ".png")
      ggsql::ggsql_save(spec, png_file, width = 500, height = 300)
      ellmer::content_image_file(png_file)
    },
    error = function(e) NULL
  )

  title_display <- if (nzchar(title)) {
    sprintf(" with title '%s'", title)
  } else {
    ""
  }
  text <- sprintf("Chart displayed%s.", title_display)

  # All list elements must be Content S7 objects for ellmer's
  # expand_content_if_needed() to handle mixed text+image results.
  value <- if (!is.null(png_content)) {
    list(ellmer::ContentText(text), png_content)
  } else {
    text
  }

  update_fn(list(ggsql = ggsql_str, title = title, widget_id = widget_id))

  extra <- list()
  if (!is.null(viz_container)) {
    footer <- build_viz_footer(ggsql_str, title, widget_id)
    extra <- list(
      display = list(
        html = viz_container,
        title = if (nzchar(title)) title else "Query Visualization",
        show_request = FALSE,
        open = querychat_tool_starts_open("visualize"),
        full_screen = TRUE,
        icon = viz_icon(),
        footer = footer
      )
    )
  }

  ellmer::ContentToolResult(value = value, extra = extra)
}

# Build the footer HTML for a visualization tool result.
# @param ggsql_str The full ggsql query string.
# @param title The visualization title.
# @param widget_id The unique widget ID for the visualization.
build_viz_footer <- function(ggsql_str, title, widget_id) {
  footer_id <- paste0(
    "querychat_footer_",
    format(as.hexmode(sample.int(.Machine$integer.max, 1)), width = 8)
  )
  query_section_id <- paste0(footer_id, "_query")
  code_editor_id <- paste0(footer_id, "_code")

  code_editor <- bslib::input_code_editor(
    id = code_editor_id,
    value = ggsql_str,
    language = "ggsql",
    read_only = TRUE,
    line_numbers = FALSE,
    height = "auto",
    theme_dark = "github-dark"
  )

  query_section <- shiny::tags$div(
    class = "querychat-query-section",
    id = query_section_id,
    code_editor
  )

  buttons_row <- shiny::tags$div(
    class = "querychat-footer-buttons",
    # Left: Show Query toggle
    shiny::tags$div(
      class = "querychat-footer-left",
      shiny::tags$button(
        class = "querychat-show-query-btn",
        `data-target` = query_section_id,
        shiny::tags$span(class = "querychat-query-chevron", "\u25b6"),
        shiny::tags$span(class = "querychat-query-label", "Show Query")
      )
    ),
    # Right: Save dropdown
    shiny::tags$div(
      class = "querychat-footer-right",
      shiny::tags$div(
        class = "querychat-save-dropdown",
        shiny::tags$button(
          class = "querychat-save-btn",
          `data-widget-id` = widget_id,
          bsicons::bs_icon("download", class = "querychat-icon"),
          "Save",
          bsicons::bs_icon("chevron-down", class = "querychat-dropdown-chevron")
        ),
        shiny::tags$div(
          class = "querychat-save-menu",
          shiny::tags$button(
            class = "querychat-save-png-btn",
            `data-widget-id` = widget_id,
            `data-title` = title,
            "Save as PNG"
          ),
          shiny::tags$button(
            class = "querychat-save-svg-btn",
            `data-widget-id` = widget_id,
            `data-title` = title,
            "Save as SVG"
          )
        )
      )
    )
  )

  htmltools::tagList(buttons_row, query_section)
}

# Returns the graph-up SVG icon string for the visualize tool.
viz_icon <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/></svg>'
}

# Returns the htmltools HTMLDependency for querychat viz assets.
viz_dep <- function() {
  htmltools::htmlDependency(
    name = "querychat-viz",
    version = utils::packageVersion("querychat"),
    package = "querychat",
    src = "htmldep",
    stylesheet = "viz.css",
    script = "viz.js"
  )
}

# Load and render the tool-visualize.md description with the available tools.
render_viz_tool_description <- function(db_type, has_tool_query = FALSE) {
  path <- system.file("prompts", "tool-visualize.md", package = "querychat")
  stopifnot(nzchar(path), file.exists(path))
  template <- paste(readLines(path, warn = FALSE), collapse = "\n")
  whisker::whisker.render(
    template,
    list(
      db_type = db_type,
      has_tool_query = if (isTRUE(has_tool_query)) "true"
    )
  )
}

#' Execute a pre-validated ggsql query against a DataSource
#'
#' Executes the SQL portion through a DataSource (preserving database pushdown),
#' then feeds the result into a ggsql DuckDB reader to produce a Spec.
#'
#' @param data_source A querychat DataSource R6 object.
#' @param validated A pre-validated ggsql query (from `ggsql::ggsql_validate()`).
#'   Must be a list with `$sql` and `$visual` fields.
#'
#' @return A `ggsql::Spec` R6 object (the writer-independent plot specification).
#'
#' @keywords internal
execute_ggsql <- function(data_source, validated) {
  rlang::check_installed("ggsql", reason = "for visualization support.")

  visual <- validated$visual

  if (has_layer_level_source(visual)) {
    cli::cli_abort(
      "Layer-specific sources are not currently supported in querychat visual queries. Rewrite the query so that all layers come from the final SQL result."
    )
  }

  df <- data_source$execute_query(validated$sql)
  # Snowflake (and some other backends) uppercase unquoted identifiers,
  # but the LLM writes lowercase aliases in the VISUALISE clause.
  # DuckDB is case-insensitive, so lowercasing here lets both match.
  names(df) <- tolower(names(df))

  reader <- ggsql::duckdb_reader()
  table <- extract_visualise_table(visual)

  if (!is.null(table)) {
    # VISUALISE [mappings] FROM <table> — register data under the
    # referenced table name and execute the visual part directly.
    name <- if (startsWith(table, '"') && endsWith(table, '"')) {
      substr(table, 2, nchar(table) - 1)
    } else {
      table
    }
    ggsql::ggsql_register(reader, df, name)
    ggsql::ggsql_execute(reader, visual)
  } else {
    # SELECT ... VISUALISE — no FROM in VISUALISE clause, so register
    # under a synthetic name and prepend a SELECT.
    ggsql::ggsql_register(reader, df, "_data")
    ggsql::ggsql_execute(reader, paste("SELECT * FROM _data", visual))
  }
}

#' Extract the table name from a VISUALISE clause's FROM, if present
#'
#' Looks only in the portion of the visual string before the first DRAW keyword,
#' so FROM clauses inside DRAW (e.g., MAPPING x FROM other) are ignored.
#'
#' @param visual A ggsql VISUALISE string.
#' @return The table name string (possibly quoted), or `NULL` if not present.
#'
#' @keywords internal
extract_visualise_table <- function(visual) {
  draw_pos <- regexpr("\\bDRAW\\b", visual, ignore.case = TRUE, perl = TRUE)
  vis_clause <- if (draw_pos > 0) substr(visual, 1, draw_pos - 1L) else visual
  m <- regmatches(
    vis_clause,
    regexpr(
      '\\bFROM\\s+("[^"]+?"|\\S+)',
      vis_clause,
      ignore.case = TRUE,
      perl = TRUE
    )
  )
  if (length(m) == 0 || !nzchar(m)) {
    return(NULL)
  }
  sub("^(?i)FROM\\s+", "", m, perl = TRUE)
}

#' Detect whether a VISUALISE string has a layer-level FROM source
#'
#' Returns `TRUE` when a DRAW clause defines its own `FROM <source>` via a
#' MAPPING sub-clause. Querychat replays VISUALISE against a single local
#' relation, so layer-specific sources cannot be preserved reliably.
#'
#' @param visual A ggsql VISUALISE string.
#' @return `TRUE` if any DRAW clause contains a MAPPING ... FROM source.
#'
#' @keywords internal
has_layer_level_source <- function(visual) {
  # Split at clause boundaries (DRAW, SCALE, etc.) using a lookbehind for
  # whitespace rather than \b, which can split mid-word in R's PCRE engine.
  clauses <- strsplit(
    visual,
    "(?i)(?<=\\s)(?=DRAW|SCALE|PROJECT|FACET|PLACE|LABEL|THEME)",
    perl = TRUE
  )[[1]]
  for (clause in clauses) {
    if (!grepl("^\\s*DRAW\\b", clause, ignore.case = TRUE, perl = TRUE)) {
      next
    }
    if (
      grepl(
        "\\bMAPPING\\b[\\s\\S]*?\\bFROM\\s+(\"[^\"]+?\"|\\S+)",
        clause,
        ignore.case = TRUE,
        perl = TRUE
      )
    ) {
      return(TRUE)
    }
  }
  FALSE
}
