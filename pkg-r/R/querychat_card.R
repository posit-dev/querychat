tool_card <- function(executor, manage_card) {
  check_function(manage_card)

  db_type <- executor$get_db_type()

  ellmer::tool(
    tool_card_impl(executor, manage_card),
    name = "querychat_card",
    description = interpolate_package("tool-card.md", db_type = db_type),
    arguments = list(
      action = ellmer::type_enum(
        c("add", "replace", "patch", "remove"),
        "Action to perform on a dashboard card. Use 'add' to create a new card, 'replace' to fully overwrite an existing card, 'patch' to change only the fields you supply on an existing card, or 'remove' to delete a card by id."
      ),
      id = ellmer::type_string(
        "Card id, required for replace, patch, and remove.",
        required = FALSE
      ),
      type = ellmer::type_enum(
        c("card", "value_box"),
        "Card type. Use 'card' for a general content card (table, visualization, or markdown), or 'value_box' for a single highlighted metric.",
        required = FALSE
      ),
      display = ellmer::type_enum(
        c("table", "visualization", "markdown"),
        "Display mode for a 'card' type. 'table' renders SQL query results as a table, 'visualization' renders a ggsql chart, 'markdown' renders static markdown text.",
        required = FALSE
      ),
      title = ellmer::type_string(
        "Card title displayed in the card header.",
        required = FALSE
      ),
      value = ellmer::type_string(
        ellmer::interpolate(
          "The card content. For 'value_box': a {{db_type}} SQL SELECT query returning exactly one row and one column. For 'card'+'table': a {{db_type}} SQL SELECT query. For 'card'+'visualization': a full ggsql query including a VISUALISE clause. For 'card'+'markdown': markdown text to render.",
          db_type = db_type
        ),
        required = FALSE
      ),
      footer = ellmer::type_string(
        "Optional footer text for a 'card' type.",
        required = FALSE
      ),
      subtitle = ellmer::type_string(
        "Value box subtitle.",
        required = FALSE
      ),
      theme = ellmer::type_string(
        "Value box bslib theme name.",
        required = FALSE
      ),
      icon = ellmer::type_string(
        "Value box bsicons icon name.",
        required = FALSE
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Update Cards",
      icon = card_icon()
    )
  )
}

tool_card_impl <- function(executor, manage_card) {
  force(executor)
  force(manage_card)

  function(
    action,
    id = NULL,
    type = NULL,
    display = NULL,
    title = NULL,
    value = NULL,
    footer = NULL,
    subtitle = NULL,
    theme = NULL,
    icon = NULL
  ) {
    if (action == "remove") {
      if (is.null(id)) {
        rlang::abort("'id' is required for action 'remove'.")
      }
      summary <- manage_card("remove", id = id)
      return(card_tool_result(id, "removed", summary))
    }

    if (action %in% c("replace", "patch") && is.null(id)) {
      rlang::abort(sprintf("'id' is required for action '%s'.", action))
    }

    # For 'patch', overlay the supplied fields onto the existing card and then
    # validate the merged result the same way 'add'/'replace' do. Drop unset
    # (NULL) fields first so modifyList() does not delete them. To clear an
    # optional field, use 'replace' instead.
    if (action == "patch") {
      existing <- manage_card("get", id = id)
      if (is.null(existing)) {
        rlang::abort(sprintf("No card found with id '%s'.", id))
      }
      supplied <- Filter(
        Negate(is.null),
        list(
          type = type,
          display = display,
          title = title,
          value = value,
          footer = footer,
          subtitle = subtitle,
          theme = theme,
          icon = icon
        )
      )
      merged <- utils::modifyList(existing, supplied)
      type <- merged$type
      display <- merged$display
      title <- merged$title
      value <- merged$value
      footer <- merged$footer
      subtitle <- merged$subtitle
      theme <- merged$theme
      icon <- merged$icon
    }

    if (is.null(type)) {
      rlang::abort(
        "'type' is required for actions 'add', 'replace', and 'patch'."
      )
    }
    if (is.null(title)) {
      rlang::abort(
        "'title' is required for actions 'add', 'replace', and 'patch'."
      )
    }
    if (is.null(value)) {
      rlang::abort(
        "'value' is required for actions 'add', 'replace', and 'patch'."
      )
    }
    if (type == "card" && is.null(display)) {
      rlang::abort("'display' is required when 'type' is 'card'.")
    }

    if (type == "value_box") {
      if (!is.null(icon)) {
        tryCatch(
          bsicons::bs_icon(icon),
          error = function(e) rlang::abort(conditionMessage(e))
        )
      }
      df <- executor$execute_query(value)
      if (!(nrow(df) == 1 && ncol(df) == 1)) {
        rlang::abort(sprintf(
          "Value box query must return exactly 1 row and 1 column. Got %d row(s) and %d column(s).",
          nrow(df),
          ncol(df)
        ))
      }
      card <- list(
        type = "value_box",
        title = title,
        value = value,
        subtitle = subtitle,
        theme = theme,
        icon = icon
      )
    } else if (display == "table") {
      tryCatch(
        executor$test_query(value),
        error = function(e) rlang::abort(conditionMessage(e))
      )
      card <- list(
        type = "card",
        display = "table",
        title = title,
        value = value,
        footer = footer
      )
    } else if (display == "visualization") {
      rlang::check_installed("ggsql", reason = "for visualization support.")
      validated <- ggsql::ggsql_validate(value)
      if (!ggsql::ggsql_has_visual(validated)) {
        rlang::abort("Visualization query must include a VISUALISE clause.")
      }
      if (!isTRUE(validated$valid)) {
        rlang::abort(collapse_validation_errors(validated))
      }
      tryCatch(
        execute_ggsql(executor, validated),
        error = function(e) rlang::abort(conditionMessage(e))
      )
      card <- list(
        type = "card",
        display = "visualization",
        title = title,
        value = value,
        footer = footer
      )
    } else {
      card <- list(
        type = "card",
        display = "markdown",
        title = title,
        value = value,
        footer = footer
      )
    }

    if (action == "add") {
      id <- random_hex()
    }
    card$id <- id

    store_action <- if (action == "add") "add" else "replace"
    summary <- manage_card(store_action, id = id, card = card)
    status <- switch(
      action,
      add = "added",
      replace = "replaced",
      patch = "patched"
    )
    card_tool_result(id, status, summary)
  }
}

card_tool_result <- function(id, status, cards_summary) {
  ellmer::ContentToolResult(
    value = jsonlite::toJSON(
      list(id = id, status = status, cards_summary = cards_summary),
      auto_unbox = TRUE
    )
  )
}

card_icon <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-grid-1x2-fill" viewBox="0 0 16 16"><path d="M0 1a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm9 0a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1zm0 9a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1z"/></svg>'
}
