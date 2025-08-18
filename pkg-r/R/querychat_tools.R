# Modifies the data presented in the data dashboard, based on the given SQL
# query, and also updates the title.
# @param query A SQL query; must be a SELECT statement.
# @param title A title to display at the top of the data dashboard,
#   summarizing the intent of the SQL query.
tool_update_dashboard <- function(
  data_source,
  current_query,
  current_title,
  filtered_df
) {
  ellmer::tool(
    tool_update_dashboard_impl(data_source, current_query, current_title),
    name = "querychat_update_dashboard",
    description = "Modifies the data presented in the data dashboard, based on the given SQL query, and also updates the title.",
    arguments = list(
      query = ellmer::type_string(
        "A SQL query; must be a SELECT statement."
      ),
      title = ellmer::type_string(
        "A title to display at the top of the data dashboard, summarizing the intent of the SQL query."
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

# Perform a SQL query on the data, and return the results as JSON.
# @param query A SQL query; must be a SELECT statement.
# @return The results of the query as a data frame.
tool_query <- function(data_source) {
  force(data_source)

  ellmer::tool(
    function(query) {
      querychat_tool_result(data_source, query, action = "query")
    },
    name = "querychat_query",
    description = "Perform a SQL query on the data, and return the results.",
    arguments = list(
      query = ellmer::type_string(
        "A SQL query; must be a SELECT statement."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Query Data",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16"><path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/></svg>'
    )
  )
}

querychat_tool_result <- function(
  data_source,
  query,
  title = NULL,
  action = "update"
) {
  action <- rlang::arg_match(action, c("update", "query"))

  res <- tryCatch(
    switch(
      action,
      update = {
        test_query(data_source, query)
        NULL
      },
      query = execute_query(data_source, query)
    ),
    error = function(err) err
  )

  is_error <- rlang::is_condition(res) || inherits(res, "error")

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

  if (!is_error && action == "update") {
    output <- format(
      shiny::tags$button(
        class = "btn btn-outline-primary btn-sm float-end mt-3 querychat-update-dashboard-btn",
        "data-query" = query,
        "data-title" = title,
        "Apply Filter"
      )
    )
    output <- paste0("\n\n", output)
  }

  value <-
    switch(
      action,
      query = res,
      update = "Dashboard updated. Use `querychat_query` tool to review results, if needed."
    )

  ellmer::ContentToolResult(
    value = if (!is_error) value,
    error = if (is_error) res,
    extra = list(
      display = list(
        show_request = is_error,
        markdown = sprintf("```sql\n%s\n```%s", query, output),
        open = !is_error
      )
    )
  )
}
