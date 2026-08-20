#' @noRd
GetSchemaResult <- S7::new_class(
  "GetSchemaResult",
  parent = ellmer::ContentToolResult,
  properties = list(
    table_name = S7::class_character
  )
)

tool_get_schema <- function(
  data_dicts,
  executor,
  table_names,
  categorical_threshold
) {
  ellmer::tool(
    function(table_name) {
      if (!table_name %in% table_names) {
        available <- paste0("'", table_names, "'", collapse = ", ")
        cli::cli_abort(
          "Table {.val {table_name}} not found. Available: {available}"
        )
      }
      table_spec <- NULL
      for (dd in data_dicts) {
        if (!is.null(dd[["tables"]][[table_name]])) {
          table_spec <- dd[["tables"]][[table_name]]
          break
        }
      }
      schema_result <- executor$get_schema_result(
        table_name,
        categorical_threshold,
        table_spec = table_spec
      )
      column_count <- length(schema_result$columns)
      GetSchemaResult(
        value = schema_result$text,
        table_name = table_name,
        extra = list(
          display = shinychat::tool_result_display(
            label = table_name,
            value_preview = paste(
              column_count,
              if (column_count == 1) "column" else "columns"
            ),
            html = schema_table(schema_result$columns),
            show_request = FALSE,
            open = FALSE
          )
        )
      )
    },
    name = "querychat_get_schema",
    description = interpolate_package("tool-get-schema.md"),
    arguments = list(
      table_name = ellmer::type_string(
        "The name of the table to retrieve schema for."
      )
    ),
    annotations = ellmer::tool_annotations(title = "Fetch schemas")
  )
}

# Modifies the data presented in the data dashboard, based on the given SQL
# query, and also updates the title.
# @param query A SQL query; must be a SELECT statement.
# @param title A title to display at the top of the data dashboard,
#   summarizing the intent of the SQL query.
tool_update_dashboard <- function(
  executor,
  table_names,
  update_fn = function(query, title, table) {}
) {
  check_function(update_fn)
  has_args <- intersect(fn_fmls_names(update_fn), c("query", "title", "table"))
  if (length(has_args) != 3) {
    missing_args <- setdiff(c("query", "title", "table"), has_args)
    cli::cli_abort(
      c(
        "{.arg update_fn} must accept at least three named arguments: {.val query}, {.val title}, and {.val table}.",
        "x" = "{.val {missing_args}} argument{?s} {?was/were} missing."
      )
    )
  }

  db_type <- executor$get_db_type()
  multi_table <- length(table_names) > 1

  ellmer::tool(
    tool_update_dashboard_impl(executor, table_names, update_fn),
    name = "querychat_update_dashboard",
    description = interpolate_package(
      "tool-update-dashboard.md",
      db_type = db_type,
      multi_table = multi_table
    ),
    arguments = list(
      query = ellmer::type_string(
        ellmer::interpolate(
          "A {{db_type}} SQL SELECT query that MUST return all existing schema columns (use SELECT * or explicitly list all columns). May include additional computed columns, subqueries, CTEs, WHERE clauses, ORDER BY, and any {{db_type}}-supported SQL functions.",
          db_type = db_type
        )
      ),
      title = ellmer::type_string(
        "A brief title for display purposes, summarizing the intent of the SQL query."
      ),
      table = ellmer::type_string(
        "The name of the table to update the dashboard for."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Update Dashboard",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-funnel-fill" viewBox="0 0 16 16"><path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/></svg>'
    )
  )
}

tool_update_dashboard_impl <- function(executor, table_names, update_fn) {
  force(executor)
  force(table_names)

  function(query, title, table) {
    res <- querychat_tool_result(
      executor,
      query = query,
      title = title,
      action = "update",
      table_name = table
    )

    if (is.null(res@error)) {
      update_fn(query, title, table)
    }

    res
  }
}

tool_reset_dashboard <- function(
  reset_fn = function(table) {},
  table_names
) {
  check_function(reset_fn)

  ellmer::tool(
    function(table) {
      if (!table %in% table_names) {
        available <- paste0("'", table_names, "'", collapse = ", ")
        cli::cli_abort(
          "Table {.val {table}} not found. Available: {available}"
        )
      }
      reset_fn(table)
    },
    name = "querychat_reset_dashboard",
    description = interpolate_package("tool-reset-dashboard.md"),
    arguments = list(
      table = ellmer::type_string(
        "The name of the table to reset the dashboard for."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Reset Dashboard",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-arrow-counterclockwise " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path fill-rule="evenodd" d="M8 3a5 5 0 1 1-4.546 2.914.5.5 0 0 0-.908-.417A6 6 0 1 0 8 2v1z"></path><path d="M8 4.466V.534a.25.25 0 0 0-.41-.192L5.23 2.308a.25.25 0 0 0 0 .384l2.36 1.966A.25.25 0 0 0 8 4.466z"></path></svg>'
    )
  )
}

# Perform a SQL query on the data, and return the results as JSON.
# @param query A SQL query; must be a SELECT statement.
# @return The results of the query as a data frame.
tool_query <- function(executor, multi_table = FALSE) {
  db_type <- executor$get_db_type()

  ellmer::tool(
    function(query, collapsed = NULL, `_intent` = "") {
      querychat_tool_result(
        executor,
        query,
        action = "query",
        collapsed = collapsed
      )
    },
    name = "querychat_query",
    description = interpolate_package(
      "tool-query.md",
      db_type = db_type,
      multi_table = multi_table
    ),
    arguments = list(
      query = ellmer::type_string(
        ellmer::interpolate(
          "A valid {{db_type}} SQL SELECT statement. Must follow the database schema provided in the system prompt. Use clear column aliases (e.g., 'AVG(price) AS avg_price') and include SQL comments for complex logic. Subqueries and CTEs are encouraged for readability.",
          db_type = db_type
        )
      ),
      collapsed = ellmer::type_boolean(
        "Optional (default: true). The result card starts collapsed by default; the user can expand it to see the query and results. Set to false when the query result table is the primary answer to the user's question and should be immediately visible without expanding.",
        required = FALSE
      ),
      `_intent` = ellmer::type_string(
        "A brief, user-friendly description of what this query calculates or retrieves."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Query Data",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16"><path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/></svg>'
    )
  )
}

querychat_tool_details_option <- function() {
  opt <- getOption("querychat.tool_details", NULL)
  if (!is.null(opt)) {
    setting <- opt
  } else {
    env <- Sys.getenv("QUERYCHAT_TOOL_DETAILS", "")
    if (nzchar(env)) {
      setting <- env
    } else {
      return(NULL)
    }
  }

  setting <- tolower(setting)
  valid_settings <- c("expanded", "collapsed", "default")

  if (!setting %in% valid_settings) {
    cli::cli_warn(
      c(
        "Invalid value for {.code querychat.tool_details} option or {.envvar QUERYCHAT_TOOL_DETAILS} environment variable: {.val {setting}}",
        "i" = "Must be one of: {.or {.val {valid_settings}}}"
      )
    )
    return(NULL)
  }

  setting
}

querychat_tool_starts_open <- function(action) {
  setting <- querychat_tool_details_option()

  if (is.null(setting)) {
    return(action %in% c("update", "visualize"))
  }

  switch(
    setting,
    "expanded" = TRUE,
    "collapsed" = FALSE,
    action %in% c("update", "visualize")
  )
}

querychat_tool_result <- function(
  executor,
  query,
  title = NULL,
  action = "update",
  table_name = NULL,
  collapsed = NULL
) {
  action <- arg_match(action, c("update", "query", "reset"))

  if (action == "reset") {
    query <- NULL
    title <- NULL
  }

  res <- tryCatch(
    switch(
      action,
      update = {
        executor$test_query(
          query,
          table_name = table_name,
          require_all_columns = TRUE
        )
        NULL
      },
      query = executor$execute_query(query),
      reset = "The dashboard has been reset to show all data."
    ),
    error = function(err) err
  )

  is_error <- is_condition(res)

  # Materialize lazy query results (e.g. TblSqlSource returns a lazy tbl)
  if (!is_error && action == "query" && !is.data.frame(res)) {
    res <- tryCatch(as.data.frame(res), error = function(err) err)
    is_error <- is_condition(res)
  }

  output <- ""
  if (!is_error && action == "query") {
    output <- utils::capture.output(print(res))
    output <- paste(
      c(
        "\n\n<details open><summary>Result</summary>\n\n```",
        output,
        "```\n\n</details>"
      ),
      collapse = "\n"
    )
  }

  if (!is_error && action %in% c("update", "reset")) {
    output <- format(
      shiny::tags$button(
        class = "btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn",
        "data-query" = query,
        "data-title" = title,
        "data-table" = table_name,
        switch(action, update = "Apply Filter", reset = "Reset Filter")
      )
    )
    output <- paste0("\n\n", output)
  }

  value <-
    switch(
      action,
      update = "Dashboard updated. Use `querychat_query` tool to review results, if needed.",
      # Send query results as a JSON string: ellmer no longer coerces data
      # frame tool values, and providers reject a raw JSON array.
      query = if (!is_error) {
        jsonlite::toJSON(res, dataframe = "rows", auto_unbox = TRUE)
      },
      res
    )

  display_md <- switch(
    action,
    reset = output,
    sprintf("```sql\n%s\n```%s", query, output)
  )

  ellmer::ContentToolResult(
    value = if (!is_error) value,
    error = if (is_error) res,
    extra = list(
      display = list(
        title = if (action == "update" && !is.null(title)) title,
        show_request = is_error,
        markdown = display_md,
        open = if (!is.null(collapsed)) {
          !collapsed
        } else {
          querychat_tool_starts_open(action)
        }
      )
    )
  )
}

schema_table <- function(columns) {
  headers <- c(
    "Column",
    "Type",
    "Description",
    "Constraints",
    "Range / Values"
  )
  rows <- lapply(columns, function(column) {
    units <- schema_scalar_text(column$units)
    type_cell <- htmltools::tagList(
      htmltools::tags$span(schema_scalar_text(column$sql_type)),
      if (nzchar(units)) {
        htmltools::tagList(
          " ",
          htmltools::tags$span(units, class = "text-body-secondary")
        )
      }
    )

    constraints <- vapply(
      column$constraints,
      schema_scalar_text,
      character(1)
    )
    constraints <- paste(constraints[nzchar(constraints)], collapse = ", ")

    categories <- vapply(
      column$categories,
      schema_scalar_text,
      character(1)
    )
    categories <- categories[nzchar(categories)]
    min_val <- schema_scalar_text(column$min_val)
    max_val <- schema_scalar_text(column$max_val)
    range_values <- if (nzchar(min_val) && nzchar(max_val)) {
      paste(min_val, "to", max_val)
    } else if (length(categories) > 0) {
      paste0("'", categories, "'", collapse = ", ")
    } else {
      ""
    }

    htmltools::tags$tr(
      htmltools::tags$th(
        htmltools::tags$code(schema_scalar_text(column$name)),
        scope = "row"
      ),
      htmltools::tags$td(type_cell),
      htmltools::tags$td(schema_scalar_text(column$description)),
      htmltools::tags$td(constraints),
      htmltools::tags$td(range_values)
    )
  })

  htmltools::tags$div(
    htmltools::tags$table(
      htmltools::tags$thead(
        htmltools::tags$tr(
          lapply(headers, function(header) {
            htmltools::tags$th(header, scope = "col")
          })
        ),
        class = "table-light"
      ),
      htmltools::tags$tbody(rows),
      class = "table table-sm table-hover align-middle mb-0"
    ),
    class = "table-responsive"
  )
}

schema_scalar_text <- function(value) {
  if (is.null(value) || length(value) == 0 || is.na(value[[1]])) {
    return("")
  }

  as.character(value[[1]])
}
