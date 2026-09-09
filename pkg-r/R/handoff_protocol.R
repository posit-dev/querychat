HANDOFF_MESSAGE_ACTIONS <- c(
  "recommend",
  "recommend-error",
  "source-update",
  "streaming",
  "panel-toggle"
)

handoff_message_type <- function(action) {
  check_handoff_protocol_string(action, "action")
  if (!action %in% HANDOFF_MESSAGE_ACTIONS) {
    cli::cli_abort(
      "{.arg action} must be one of {.val {HANDOFF_MESSAGE_ACTIONS}}."
    )
  }
  paste0("querychat-handoff-", action)
}

handoff_recommend_message <- function(
  root_id,
  recommendation,
  directions_id
) {
  check_handoff_protocol_string(root_id, "root_id")
  check_handoff_protocol_string(directions_id, "directions_id")
  if (!S7::S7_inherits(recommendation, HandoffRecommendation)) {
    cli::cli_abort(
      "{.arg recommendation} must be a {.cls HandoffRecommendation}."
    )
  }
  check_handoff_protocol_vector(
    recommendation@selected_ids,
    "recommendation@selected_ids"
  )

  new_handoff_message(
    "recommend",
    list(
      root_id = root_id,
      selected_ids = unname(as.list(recommendation@selected_ids)),
      format_id = recommendation@format_id,
      directions = recommendation@directions,
      directions_id = directions_id
    )
  )
}

handoff_recommend_error_message <- function(root_id, error) {
  check_handoff_protocol_string(root_id, "root_id")
  check_handoff_protocol_string(error, "error", allow_empty = TRUE)

  new_handoff_message(
    "recommend-error",
    list(root_id = root_id, error = error)
  )
}

handoff_source_update_message <- function(
  root_id,
  id,
  value,
  append = NULL,
  language = NULL,
  download_available = NULL
) {
  check_handoff_protocol_string(root_id, "root_id")
  check_handoff_protocol_string(id, "id")
  check_handoff_protocol_string(value, "value", allow_empty = TRUE)
  check_handoff_protocol_logical(append, "append")
  check_handoff_protocol_optional_string(language, "language")
  check_handoff_protocol_logical(
    download_available,
    "download_available"
  )

  new_handoff_message(
    "source-update",
    list(
      root_id = root_id,
      id = id,
      value = value,
      append = append,
      language = language,
      download_available = download_available
    )
  )
}

handoff_streaming_message <- function(root_id, active) {
  check_handoff_protocol_string(root_id, "root_id")
  check_handoff_protocol_logical(active, "active", optional = FALSE)

  new_handoff_message(
    "streaming",
    list(root_id = root_id, active = active)
  )
}

handoff_panel_toggle_message <- function(root_id, open) {
  check_handoff_protocol_string(root_id, "root_id")
  check_handoff_protocol_logical(open, "open", optional = FALSE)

  new_handoff_message(
    "panel-toggle",
    list(root_id = root_id, open = open)
  )
}

new_handoff_message <- function(action, payload) {
  payload <- Filter(Negate(is.null), payload)
  payload <- lapply(payload, unname)
  list(type = handoff_message_type(action), payload = payload)
}

check_handoff_protocol_string <- function(
  value,
  name,
  allow_empty = FALSE
) {
  valid <- is.character(value) &&
    length(value) == 1L &&
    !is.na(value) &&
    (allow_empty || nzchar(value))
  if (!valid) {
    qualifier <- if (allow_empty) "a single string" else "a nonempty string"
    cli::cli_abort("{.arg {name}} must be {qualifier}.")
  }
}

check_handoff_protocol_optional_string <- function(value, name) {
  if (!is.null(value)) {
    check_handoff_protocol_string(value, name)
  }
}

check_handoff_protocol_logical <- function(
  value,
  name,
  optional = TRUE
) {
  if (optional && is.null(value)) {
    return(invisible(NULL))
  }
  if (!is.logical(value) || length(value) != 1L || is.na(value)) {
    cli::cli_abort("{.arg {name}} must be a single logical value.")
  }
  invisible(NULL)
}

check_handoff_protocol_vector <- function(value, name) {
  if (
    !is.character(value) ||
      anyNA(value) ||
      any(!nzchar(value))
  ) {
    cli::cli_abort(
      "{.arg {name}} must contain only nonempty strings."
    )
  }
}
