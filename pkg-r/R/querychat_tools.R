# Modifies the data presented in the data dashboard, based on the given SQL
# query, and also updates the title.
# @param query A SQL query; must be a SELECT statement.
# @param title A title to display at the top of the data dashboard,
#   summarizing the intent of the SQL query.
tool_update_dashboard <- function(
  data_source,
  current_query,
  current_title
) {
  db_type <- data_source$get_db_type()

  ellmer::tool(
    tool_update_dashboard_impl(data_source, current_query, current_title),
    name = "querychat_update_dashboard",
    description = interpolate_package(
      "tool-update-dashboard.md",
      db_type = db_type
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
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Update Dashboard",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-funnel-fill" viewBox="0 0 16 16"><path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/></svg>'
    )
  )
}

tool_update_dashboard_impl <- function(
  data_source,
  current_query,
  current_title
) {
  force(data_source)

  function(query, title) {
    res <- querychat_tool_result(
      data_source,
      query = query,
      title = title,
      action = "update"
    )

    if (is.null(res@error)) {
      if (!is.null(query)) {
        current_query(query)
      }
      if (!is.null(title)) {
        current_title(title)
      }
    }

    res
  }
}


tool_reset_dashboard <- function(reset_fn) {
  ellmer::tool(
    reset_fn,
    name = "querychat_reset_dashboard",
    description = interpolate_package("tool-reset-dashboard.md"),
    arguments = list(),
    annotations = ellmer::tool_annotations(
      title = "Reset Dashboard",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-arrow-counterclockwise " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path fill-rule="evenodd" d="M8 3a5 5 0 1 1-4.546 2.914.5.5 0 0 0-.908-.417A6 6 0 1 0 8 2v1z"></path><path d="M8 4.466V.534a.25.25 0 0 0-.41-.192L5.23 2.308a.25.25 0 0 0 0 .384l2.36 1.966A.25.25 0 0 0 8 4.466z"></path></svg>'
    )
  )
}

# Perform a SQL query on the data, and return the results as JSON.
# @param query A SQL query; must be a SELECT statement.
# @return The results of the query as a data frame.
tool_query <- function(data_source) {
  force(data_source)
  db_type <- data_source$get_db_type()

  ellmer::tool(
    function(query, `_intent` = "") {
      querychat_tool_result(data_source, query, action = "query")
    },
    name = "querychat_query",
    description = interpolate_package("tool-query.md", db_type = db_type),
    arguments = list(
      query = ellmer::type_string(
        ellmer::interpolate(
          "A valid {{db_type}} SQL SELECT statement. Must follow the database schema provided in the system prompt. Use clear column aliases (e.g., 'AVG(price) AS avg_price') and include SQL comments for complex logic. Subqueries and CTEs are encouraged for readability.",
          db_type = db_type
        )
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
    cli::cli_warn(c(
      "Invalid value for {.code querychat.tool_details} option or {.envvar QUERYCHAT_TOOL_DETAILS} environment variable: {.val {setting}}",
      "i" = "Must be one of: {.or {.val {valid_settings}}}"
    ))
    return(NULL)
  }

  setting
}

querychat_tool_starts_open <- function(action) {
  setting <- querychat_tool_details_option()

  if (is.null(setting)) {
    return(action != "reset")
  }

  switch(
    setting,
    "expanded" = TRUE,
    "collapsed" = FALSE,
    action != "reset"
  )
}

querychat_tool_result <- function(
  data_source,
  query,
  title = NULL,
  action = "update"
) {
  action <- arg_match(action, c("update", "query", "reset"))

  if (action == "reset") {
    query <- ""
    title <- NULL
  }

  res <- tryCatch(
    switch(
      action,
      update = {
        data_source$test_query(query)
        NULL
      },
      query = data_source$execute_query(query),
      reset = "The dashboard has been reset to show all data."
    ),
    error = function(err) err
  )

  is_error <- is_condition(res)

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
        switch(action, update = "Apply Filter", reset = "Reset Filter")
      )
    )
    output <- paste0("\n\n", output)
  }

  value <-
    switch(
      action,
      update = "Dashboard updated. Use `querychat_query` tool to review results, if needed.",
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
        open = querychat_tool_starts_open(action)
      )
    )
  )
}
