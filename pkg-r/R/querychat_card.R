tool_card <- function(executor, manage_card) {
  check_function(manage_card)

  db_type <- executor$get_db_type()

  ellmer::tool(
    tool_card_impl(executor, manage_card),
    name = "querychat_card",
    description = interpolate_package("tool-card.md", db_type = db_type),
    arguments = list(
      action = ellmer::type_enum(
        c("add", "replace", "patch", "remove", "get"),
        paste(
          "The operation to perform.",
          "- 'add': create a new card. Requires display, title, and value.",
          "- 'patch': the preferred way to edit a card. Send the id and only the fields you are changing; omitted fields keep their current values. Cannot clear an optional field; use 'replace' for that.",
          "- 'replace': fully overwrite a card. Send the id and every field for the new version (same requirements as 'add'; changing display is allowed). Omitted optional fields are cleared.",
          "- 'remove': delete a card. Requires only id.",
          "- 'get': read existing cards. Omit id for all cards, or pass an id for one. Use it to discover card ids and their current contents before a patch, replace, or remove.",
          sep = "\n"
        )
      ),
      id = ellmer::type_string(
        "The short card identifier. Required for replace, patch, and remove; optional for get (omit to return all cards); omit for add.",
        required = FALSE
      ),
      display = ellmer::type_enum(
        c("table", "visualization", "markdown", "value_box"),
        "Which renderer to use; required for add and replace. 'table' renders SQL query results as a table, 'visualization' renders a ggsql chart, 'markdown' renders static markdown text, 'value_box' renders a single highlighted metric (SQL query returning exactly 1 row and 1 column).",
        required = FALSE
      ),
      title = ellmer::type_string(
        "A brief card heading shown in the card header. Required for add and replace.",
        required = FALSE
      ),
      value = ellmer::type_string(
        ellmer::interpolate(
          paste(
            "The card content; required for add and replace. Its meaning depends on display:",
            "- table: a {{db_type}} SQL SELECT query.",
            "- visualization: a full ggsql query including a VISUALISE clause. Do NOT include `LABEL title => ...`; use the title parameter instead.",
            "- markdown: markdown text to render.",
            "- value_box: a {{db_type}} SQL SELECT query returning exactly 1 row and 1 column. Format the value into a human-readable string in SQL (thousands separators, currency, rounding, a % suffix, etc.) so it displays cleanly; don't return a raw float.",
            sep = "\n"
          ),
          db_type = db_type
        ),
        required = FALSE
      ),
      caption = ellmer::type_string(
        "Optional brief secondary text. Rendered as a footer for table/visualization/markdown cards, and as the subtitle for value_box. Keep it to a few words.",
        required = FALSE
      ),
      theme = ellmer::type_string(
        "Optional Bootstrap theme name for a value_box background: one of primary, secondary, success, danger, warning, info. Applies to value_box only; ignored for other displays.",
        required = FALSE
      ),
      icon = ellmer::type_string(
        "Optional Bootstrap icon name (e.g., 'bar-chart', 'currency-dollar', 'people-fill'). Honored by every display: the showcase icon for value_box, and shown beside the title for table/visualization/markdown.",
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
    display = NULL,
    title = NULL,
    value = NULL,
    caption = NULL,
    theme = NULL,
    icon = NULL
  ) {
    if (action == "get") {
      if (is.null(id)) {
        cards <- manage_card("get")
        return(card_tool_result(lapply(cards, card_public), "View Cards"))
      }
      card <- manage_card("get", id = id)
      if (is.null(card)) {
        rlang::abort(sprintf("No card found with id '%s'.", id))
      }
      return(card_tool_result(card_public(card), "View Card"))
    }

    if (action == "remove") {
      if (is.null(id)) {
        rlang::abort("'id' is required for action 'remove'.")
      }
      manage_card("remove", id = id)
      return(card_tool_result(list(id = id, status = "removed"), "Remove Card"))
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
          display = display,
          title = title,
          value = value,
          caption = caption,
          theme = theme,
          icon = icon
        )
      )
      merged <- utils::modifyList(existing, supplied)
      display <- merged$display
      title <- merged$title
      value <- merged$value
      caption <- merged$caption
      theme <- merged$theme
      icon <- merged$icon
    }

    if (is.null(display)) {
      rlang::abort(
        "'display' is required for actions 'add', 'replace', and 'patch'."
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

    # Validate icon (bsicons) for any display that supplies one
    if (!is.null(icon)) {
      tryCatch(
        bsicons::bs_icon(icon),
        error = function(e) rlang::abort(conditionMessage(e))
      )
    }

    if (display == "value_box") {
      df <- executor$execute_query(value)
      if (!(nrow(df) == 1 && ncol(df) == 1)) {
        rlang::abort(sprintf(
          "Value box query must return exactly 1 row and 1 column. Got %d row(s) and %d column(s).",
          nrow(df),
          ncol(df)
        ))
      }
    } else if (display == "table") {
      tryCatch(
        executor$validate_query(value),
        error = function(e) rlang::abort(conditionMessage(e))
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
    }
    # markdown: no query validation needed

    card <- list(
      display = display,
      title = title,
      value = value,
      caption = caption,
      theme = theme,
      icon = icon
    )

    if (action == "add") {
      id <- new_card_id(manage_card)
    }
    card$id <- id

    store_action <- if (action == "add") "add" else "replace"
    manage_card(store_action, id = id, card = card)
    status <- switch(
      action,
      add = "added",
      replace = "replaced",
      patch = "patched"
    )
    title <- switch(
      action,
      add = "Add Card",
      replace = "Replace Card",
      patch = "Update Card"
    )
    card_tool_result(list(id = id, status = status), title)
  }
}

card_tool_result <- function(value, title) {
  ellmer::ContentToolResult(
    value = jsonlite::toJSON(value, auto_unbox = TRUE),
    extra = list(
      display = list(title = title)
    )
  )
}

# Generate a short (4 hex char) card id that does not collide with an existing
# card. Cards are few, so collisions are rare; the loop guarantees uniqueness.
new_card_id <- function(manage_card) {
  existing <- map_chr(manage_card("get"), function(cd) cd$id)
  repeat {
    id <- random_hex(2)
    if (!id %in% existing) {
      return(id)
    }
  }
}

# Present a stored card to the model: drop unset optional fields and order
# the remaining fields with `id` first.
card_public <- function(card) {
  card <- compact(card)
  ordered <- c("id", "display", "title", "value", "caption", "theme", "icon")
  card[intersect(ordered, names(card))]
}

card_icon <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-grid-1x2-fill" viewBox="0 0 16 16"><path d="M0 1a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm9 0a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1zm0 9a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1z"/></svg>'
}
