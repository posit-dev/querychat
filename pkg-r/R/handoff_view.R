HandoffView <- R6::R6Class(
  "HandoffView",
  public = list(
    initialize = function(session, chat_module) {
      private$session <- session
      private$chat_module <- chat_module
      private$panel_root_id <- session$ns("handoff_root")
      private$modal_root_id <- session$ns("handoff_modal_root")
      private$editor_id <- session$ns("handoff_source_editor")
      private$directions_id <- session$ns("handoff_directions")
      private$open_input_id <- session$ns("handoff_open")
    },

    set_panel_open = function(open) {
      private$send(
        handoff_panel_toggle_message(private$panel_root_id, open)
      )
    },

    clear_source = function(language) {
      private$send(
        handoff_source_update_message(
          private$panel_root_id,
          private$editor_id,
          "",
          language = language,
          download_available = FALSE
        )
      )
    },

    replace_source = function(value) {
      private$send(
        handoff_source_update_message(
          private$panel_root_id,
          private$editor_id,
          value
        )
      )
    },

    append_source = function(value) {
      private$send(
        handoff_source_update_message(
          private$panel_root_id,
          private$editor_id,
          value,
          append = TRUE
        )
      )
    },

    set_streaming = function(active) {
      private$send(
        handoff_streaming_message(private$panel_root_id, active)
      )
    },

    show_handoff = function(state, download_available) {
      if (!S7::S7_inherits(state, HandoffState)) {
        cli::cli_abort("{.arg state} must be a {.cls HandoffState}.")
      }
      private$send(
        handoff_source_update_message(
          private$panel_root_id,
          private$editor_id,
          state@source,
          language = state@handoff_type@editor_language,
          download_available = download_available
        )
      )
    },

    show_recommendation = function(recommendation) {
      if (!S7::S7_inherits(recommendation, HandoffRecommendation)) {
        cli::cli_abort(
          "{.arg recommendation} must be a {.cls HandoffRecommendation}."
        )
      }
      recommendation <- HandoffRecommendation(
        selected_ids = unique(recommendation@selected_ids),
        format_id = recommendation@format_id,
        directions = recommendation@directions
      )
      private$send(
        handoff_recommend_message(
          private$modal_root_id,
          recommendation,
          private$directions_id
        )
      )
    },

    show_recommendation_error = function(error) {
      private$send(
        handoff_recommend_error_message(private$modal_root_id, error)
      )
    },

    show_modal = function(items) {
      shiny::showModal(
        handoff_modal_ui(private$session$ns, items),
        session = private$session
      )
    },

    remove_modal = function() {
      shiny::removeModal(session = private$session)
    },

    append_pill = function(handoff_id, handoff_type, summary) {
      check_handoff_protocol_string(summary, "summary", allow_empty = TRUE)
      message <- htmltools::tagList(
        render_handoff_pill(
          handoff_id,
          handoff_type,
          private$open_input_id
        )
      )
      if (nzchar(summary)) {
        message <- htmltools::tagList(message, htmltools::tags$p(summary))
      }
      private$chat_module$append(message)
    }
  ),
  private = list(
    session = NULL,
    chat_module = NULL,
    panel_root_id = NULL,
    modal_root_id = NULL,
    editor_id = NULL,
    directions_id = NULL,
    open_input_id = NULL,

    send = function(message) {
      private$session$sendCustomMessage(
        message$type,
        message$payload
      )
    }
  )
)
