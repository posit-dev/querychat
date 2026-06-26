tool_card <- function(executor, manage_card) {
  check_query_executor(executor)
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
          "- 'add': create a new card. Requires display, title, and query (or text for markdown).",
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
      query = ellmer::type_string(
        ellmer::interpolate(
          paste(
            "The data query; required for table, visualization, and value_box displays; optional for markdown (interpolation). Its meaning depends on display:",
            "- table: a {{db_type}} SQL SELECT query.",
            "- visualization: a full ggsql query including a VISUALISE clause. Do NOT include `LABEL title => ...`; use the title parameter instead.",
            "- value_box: a {{db_type}} SQL SELECT query returning exactly 1 row. The displayed number comes from the `value` column (or the first column). Additional columns named title, text, theme, or icon override the static card fields. Format the displayed value as a human-readable string in SQL (thousands separators, currency, rounding, a % suffix, etc.).",
            "- markdown (optional): a {{db_type}} SQL SELECT query returning exactly 1 row. Its columns become {{{{var}}}} placeholders in the text body.",
            sep = "\n"
          ),
          db_type = db_type
        ),
        required = FALSE
      ),
      text = ellmer::type_string(
        paste(
          "Supplementary text; its role depends on display:",
          "- markdown (required): the body content, rendered as HTML via markdown. If a query is also supplied, its single-row columns are interpolated as {{var}} placeholders.",
          "- table / visualization: a brief footer shown below the content.",
          "- value_box: the subtitle shown under the main value.",
          sep = "\n"
        ),
        required = FALSE
      ),
      theme = ellmer::type_string(
        "Optional Bootstrap theme name for a value_box background (e.g. primary, secondary, success, danger, warning, info). Applies to value_box only; ignored for other displays.",
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
    query = NULL,
    text = NULL,
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
          query = query,
          text = text,
          theme = theme,
          icon = icon
        )
      )
      merged <- utils::modifyList(existing, supplied)
      display <- merged$display
      title <- merged$title
      query <- merged$query
      text <- merged$text
      theme <- merged$theme
      icon <- merged$icon
    }

    card <- validate_and_build_card(
      executor,
      fields = list(
        display = display,
        title = title,
        query = query,
        text = text,
        theme = theme,
        icon = icon
      )
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

# Validate fields and return the canonical card list (without id).
validate_and_build_card <- function(executor, fields) {
  # Migrate legacy field names from persisted state (bookmarks, URL seeds)
  if (!is.null(fields$caption) && is.null(fields$text)) {
    fields$text <- fields$caption
  }
  fields$caption <- NULL
  if (!is.null(fields$value) && is.null(fields$query)) {
    fields$query <- fields$value
  }
  fields$value <- NULL

  display <- fields$display
  title <- fields$title
  query <- fields$query
  text <- fields$text
  theme <- fields$theme
  icon <- fields$icon

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
  if (display == "markdown") {
    if (is.null(text)) {
      rlang::abort("'text' is required for display 'markdown'.")
    }
  } else {
    if (is.null(query)) {
      rlang::abort(sprintf("'query' is required for display '%s'.", display))
    }
  }

  # Validate icon (bsicons) for any display that supplies one
  if (!is.null(icon)) {
    tryCatch(
      bsicons::bs_icon(icon),
      error = function(e) rlang::abort(conditionMessage(e))
    )
  }

  if (display == "value_box") {
    df <- executor$execute_query(query)
    if (nrow(df) != 1) {
      rlang::abort(sprintf(
        "Value box query must return exactly 1 row. Got %d row(s).",
        nrow(df)
      ))
    }
    row <- as.list(df[1, , drop = FALSE])
    vb_cols <- c("value", "title", "text", "theme", "icon")
    for (col in intersect(names(row), vb_cols)) {
      val <- as.character(row[[col]])
      if (!is.na(val) && nzchar(val)) {
        if (col %in% c("value", "text", "theme")) {
          next
        }
        if (col == "icon") {
          tryCatch(
            bsicons::bs_icon(val),
            error = function(e) {
              rlang::abort(sprintf(
                "Value box query returned invalid icon '%s': %s",
                val,
                conditionMessage(e)
              ))
            }
          )
        }
      }
    }
  } else if (display == "table") {
    tryCatch(
      executor$validate_query(query),
      error = function(e) rlang::abort(conditionMessage(e))
    )
  } else if (display == "visualization") {
    rlang::check_installed("ggsql", reason = "for visualization support.")
    validated <- ggsql::ggsql_validate(query)
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
  } else if (display == "markdown" && !is.null(query)) {
    df <- executor$execute_query(query)
    if (nrow(df) != 1) {
      rlang::abort(sprintf(
        "Markdown interpolation query must return exactly 1 row. Got %d row(s).",
        nrow(df)
      ))
    }
  }

  list(
    display = display,
    title = title,
    query = query,
    text = text,
    theme = theme,
    icon = icon
  )
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
  ordered <- c(
    "id",
    "display",
    "title",
    "query",
    "text",
    "theme",
    "icon"
  )
  card[intersect(ordered, names(card))]
}

# Encode a list of cards to a URL-safe payload string.
# Each card is passed through card_public(), serialized to JSON, compressed
# with gzip, base64-encoded, then made URL-safe (RFC 4648 §5 alphabet).
cards_to_payload <- function(cards) {
  public_cards <- lapply(cards, card_public)
  json <- jsonlite::toJSON(public_cards, auto_unbox = TRUE)
  compressed <- memCompress(charToRaw(json), "gzip")
  b64 <- jsonlite::base64_enc(compressed)
  # base64_enc may insert newlines; strip all whitespace before conversion
  b64 <- gsub("[[:space:]]", "", b64)
  # Convert standard base64 to URL-safe base64: + -> -, / -> _, strip = padding
  b64 <- gsub("+", "-", b64, fixed = TRUE)
  b64 <- gsub("/", "_", b64, fixed = TRUE)
  b64 <- gsub("=", "", b64, fixed = TRUE)
  b64
}

# Decode a URL-safe payload string back to a list of card field-lists.
# Structural decode only — does not run query validation.
payload_to_cards <- function(payload) {
  # Restore URL-safe base64 to standard base64 and re-add = padding
  b64 <- gsub("-", "+", payload, fixed = TRUE)
  b64 <- gsub("_", "/", b64, fixed = TRUE)
  pad <- (4L - nchar(b64) %% 4L) %% 4L
  b64 <- paste0(b64, strrep("=", pad))
  raw_bytes <- jsonlite::base64_dec(b64)
  json <- rawToChar(memDecompress(raw_bytes, "gzip"))
  jsonlite::fromJSON(json, simplifyVector = FALSE)
}

card_icon <- function() {
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-grid-1x2-fill" viewBox="0 0 16 16"><path d="M0 1a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm9 0a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1zm0 9a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1z"/></svg>'
}

# Normalize the `cards` constructor argument into a list of field-lists.
# Accepts NULL (returns NULL), a list (used as-is), or a character scalar
# (parsed as JSON or read from a file path). Performs light structural checks
# only — authoritative field/query validation happens later in mod_server()
# where the executor is available.
normalize_seed_cards <- function(cards) {
  if (is.null(cards)) {
    return(NULL)
  }

  if (is.character(cards) && length(cards) == 1) {
    json <- if (file.exists(cards)) read_utf8(cards) else cards
    cards <- tryCatch(
      jsonlite::fromJSON(json, simplifyVector = FALSE),
      error = function(e) {
        cli::cli_abort(
          c(
            "{.arg cards} could not be parsed as JSON.",
            "x" = "{conditionMessage(e)}"
          ),
          call = NULL
        )
      }
    )
  }

  if (!is.list(cards)) {
    cli::cli_abort(
      "{.arg cards} must be a list, a JSON string, or a path to a JSON file.",
      call = NULL
    )
  }

  # Each element must be a named list (field-list for one card).
  for (i in seq_along(cards)) {
    if (!is.list(cards[[i]])) {
      cli::cli_abort(
        "Element {i} of {.arg cards} must be a named list of card fields, not {.obj_type_friendly cards[[i]]}.",
        call = NULL
      )
    }
  }

  cards
}
