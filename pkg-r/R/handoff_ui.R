handoff_panel_ui <- function(ns) {
  htmltools::tags$div(
    htmltools::tags$div(class = "querychat-handoff-backdrop"),
    htmltools::tags$div(
      htmltools::tags$div(
        htmltools::tags$div(
          htmltools::tags$h3("Handoff"),
          htmltools::tags$span(
            class = "querychat-handoff-header-spinner"
          ),
          class = "querychat-handoff-title"
        ),
        htmltools::tags$div(
          class = "querychat-handoff-header-spacer"
        ),
        htmltools::tags$button(
          bsicons::bs_icon("pencil-square"),
          class = paste(
            "btn btn-sm querychat-handoff-icon-btn",
            "querychat-handoff-revise-toggle"
          ),
          type = "button",
          title = "Revise with AI",
          `aria-label` = "Revise with AI"
        ),
        shiny::downloadButton(
          ns("handoff_download"),
          label = bsicons::bs_icon("download"),
          class = paste(
            "btn btn-sm querychat-handoff-icon-btn",
            "querychat-handoff-download-btn"
          ),
          icon = NULL,
          title = "Download",
          `aria-label` = "Download"
        ),
        htmltools::tags$span(
          class = "querychat-handoff-header-divider"
        ),
        shiny::actionButton(
          ns("handoff_close"),
          label = NULL,
          icon = bsicons::bs_icon("x-lg"),
          class = "btn btn-sm querychat-handoff-icon-btn",
          title = "Close",
          `aria-label` = "Close"
        ),
        class = "querychat-handoff-panel-header"
      ),
      htmltools::tags$div(
        bslib::input_submit_textarea(
          ns("handoff_revise_text"),
          placeholder = "Ask AI to revise this handoff.",
          rows = 1,
          width = "100%",
          submit_key = "enter"
        ),
        class = "querychat-handoff-revise-drawer"
      ),
      htmltools::tags$div(
        class = "querychat-handoff-panel-error",
        style = "display:none"
      ),
      htmltools::tags$div(
        bslib::input_code_editor(
          ns("handoff_source_editor"),
          value = "",
          language = "plain",
          read_only = TRUE
        ),
        class = "querychat-handoff-panel-body"
      ),
      class = "querychat-handoff-panel"
    ),
    id = ns("handoff_root"),
    class = "querychat-handoff-root"
  )
}

handoff_modal_ui <- function(ns, items) {
  has_items <- length(items) > 0L
  loading_class <- if (has_items) " loading" else ""

  shiny::modalDialog(
    htmltools::tags$p(
      paste(
        "Preserve important findings in a standalone report,",
        "dashboard, or script."
      ),
      class = "querychat-handoff-modal-intro"
    ),
    handoff_section_label(
      "Results to include",
      "Select which queries and visualizations to include in the handoff."
    ),
    htmltools::tags$div(
      htmltools::tags$div(class = "spinner"),
      "Analyzing your results...",
      class = paste0(
        "querychat-handoff-loading-status",
        if (has_items) "" else " hidden"
      )
    ),
    htmltools::tags$div(
      handoff_gallery_ui(items),
      class = "querychat-handoff-gallery-scroll"
    ),
    handoff_section_label(
      "Output format",
      "Choose the file type for the generated handoff.",
      class = "mt-2"
    ),
    handoff_type_selector_ui(),
    handoff_section_label(
      "Language",
      paste(
        "Preferred programming language. Quarto, Shiny, and Jupyter",
        "support either R or Python; Marimo is Python only."
      ),
      class = "mt-2"
    ),
    handoff_language_selector_ui(ns),
    htmltools::tags$div(
      handoff_section_label(
        "Generation notes",
        paste(
          "Optional instructions for the AI on how to structure or",
          "style the handoff."
        )
      ),
      htmltools::tags$span(
        bsicons::bs_icon("stars"),
        "Pre-filled by AI",
        class = paste(
          "querychat-handoff-directions-subtitle",
          "hidden"
        )
      ),
      class = "querychat-handoff-section-label-row mt-2"
    ),
    htmltools::tags$div(
      handoff_directions_ui(ns, disabled = has_items),
      class = paste0(
        "querychat-handoff-directions-wrapper",
        loading_class
      )
    ),
    htmltools::tags$div(
      htmltools::tags$button(
        bsicons::bs_icon("stars"),
        " Generate",
        id = ns("handoff_generate"),
        class = "btn btn-primary querychat-handoff-generate",
        disabled = "disabled"
      ),
      class = "d-flex justify-content-end mt-2"
    ),
    title = "Prepare Handoff",
    footer = NULL,
    size = "l",
    easyClose = TRUE,
    id = ns("handoff_modal_root"),
    class = "querychat-handoff-modal"
  )
}

render_handoff_pill <- function(handoff_id, handoff_type, input_id) {
  check_handoff_protocol_string(handoff_id, "handoff_id")
  check_handoff_protocol_string(input_id, "input_id")
  if (!S7::S7_inherits(handoff_type, HandoffType)) {
    cli::cli_abort(
      "{.arg handoff_type} must be a {.cls HandoffType}."
    )
  }

  htmltools::tags$button(
    htmltools::tags$span(
      bsicons::bs_icon(handoff_type@icon),
      class = "querychat-handoff-pill-icon"
    ),
    htmltools::tags$span(
      htmltools::tags$span(
        "Handoff",
        class = "querychat-handoff-pill-title"
      ),
      htmltools::tags$span(
        handoff_type@label,
        class = "querychat-handoff-pill-subtitle"
      ),
      class = "querychat-handoff-pill-body"
    ),
    htmltools::tags$span(
      bsicons::bs_icon("box-arrow-up-right"),
      class = "querychat-handoff-pill-open"
    ),
    type = "button",
    class = "querychat-handoff-pill",
    `data-handoff-id` = handoff_id,
    `data-input-id` = input_id
  )
}

handoff_html_dependency <- function() {
  htmltools::htmlDependency(
    name = "querychat-handoff",
    version = utils::packageVersion("querychat"),
    package = "querychat",
    src = "htmldep",
    script = "handoff.js",
    stylesheet = "handoff.css"
  )
}

handoff_gallery_ui <- function(items) {
  if (length(items) == 0L) {
    return(
      htmltools::tags$div(
        htmltools::tags$p(
          paste0(
            "No results yet \u2014 ask a question first to populate ",
            "the gallery."
          )
        ),
        class = "querychat-handoff-gallery-empty"
      )
    )
  }

  cards <- lapply(items, function(item) {
    if (S7::S7_inherits(item, HandoffVizItem)) {
      return(handoff_viz_card_ui(item))
    }
    if (S7::S7_inherits(item, HandoffQueryItem)) {
      return(handoff_query_card_ui(item))
    }
    cli::cli_abort(
      "{.arg items} must contain only handoff gallery items."
    )
  })

  htmltools::tags$div(
    htmltools::tagList(cards),
    class = "querychat-handoff-gallery loading"
  )
}

handoff_query_card_ui <- function(item) {
  preview <- if (is.null(item@preview_html)) {
    htmltools::tags$div(
      htmltools::tags$div(
        substr(item@sql, 1L, 80L),
        class = "sql-snippet"
      ),
      class = "preview-container"
    )
  } else {
    htmltools::tags$div(
      htmltools::HTML(item@preview_html),
      class = "preview-container"
    )
  }

  handoff_gallery_card_ui(item, preview)
}

handoff_viz_card_ui <- function(item) {
  visual <- if (is.null(item@thumbnail)) {
    htmltools::tags$div("No preview", class = "placeholder-icon")
  } else {
    htmltools::tags$img(
      src = item@thumbnail,
      alt = item@title,
      draggable = "false"
    )
  }

  handoff_gallery_card_ui(
    item,
    htmltools::tags$div(visual, class = "preview-container")
  )
}

handoff_gallery_card_ui <- function(item, preview) {
  htmltools::tags$div(
    handoff_checkbox_ui(),
    preview,
    htmltools::tags$div(item@title, class = "title"),
    class = "querychat-handoff-gallery-item",
    `data-item-id` = item@id
  )
}

handoff_checkbox_ui <- function() {
  htmltools::tags$div(
    htmltools::tags$svg(
      htmltools::tag(
        "polyline",
        list(points = "3 6.5 5.5 9 9 3.5")
      ),
      viewBox = "0 0 12 12",
      xmlns = "http://www.w3.org/2000/svg"
    ),
    class = "gallery-checkbox"
  )
}

handoff_type_selector_ui <- function() {
  registry <- handoff_registry()
  pills <- Map(
    function(format, index) {
      htmltools::tags$button(
        bsicons::bs_icon(format@icon),
        paste0(" ", format@label),
        class = paste0(
          "querychat-handoff-type-pill",
          if (index == 1L) " active" else ""
        ),
        type = "button",
        `data-handoff-type` = format@id,
        `data-languages` = paste(names(format@targets), collapse = ",")
      )
    },
    registry,
    seq_along(registry)
  )
  pills[[length(pills) + 1L]] <- htmltools::tags$button(
    bsicons::bs_icon("three-dots"),
    " Other",
    class = "querychat-handoff-type-pill",
    type = "button",
    `data-handoff-type` = "other",
    `data-languages` = "python,r"
  )

  htmltools::tagList(
    htmltools::tags$div(
      htmltools::tagList(pills),
      class = "querychat-handoff-type-selector"
    ),
    htmltools::tags$div(
      htmltools::tags$input(
        type = "text",
        class = "form-control mt-2",
        placeholder = paste(
          "e.g., R Markdown report, Streamlit app, SQL script..."
        )
      ),
      class = "querychat-handoff-freeform-input hidden"
    )
  )
}

handoff_language_selector_ui <- function(ns) {
  languages <- c(python = "Python", r = "R")
  radios <- Map(
    function(language, label) {
      htmltools::tags$label(
        htmltools::tags$input(
          type = "radio",
          name = ns("handoff_language"),
          class = "querychat-handoff-language-radio",
          `data-language` = language,
          checked = if (language == "python") "" else NULL
        ),
        htmltools::tags$span(
          class = paste(
            "querychat-handoff-language-icon",
            paste0(
              "querychat-handoff-language-icon-",
              language
            )
          )
        ),
        label,
        class = paste(
          "querychat-handoff-language-option",
          "querychat-handoff-language-pill"
        ),
        `data-language` = language
      )
    },
    names(languages),
    unname(languages)
  )

  htmltools::tags$div(
    htmltools::tagList(radios),
    class = "querychat-handoff-language-selector",
    role = "radiogroup",
    `aria-label` = "Programming language"
  )
}

handoff_directions_ui <- function(ns, disabled) {
  input <- shiny::textAreaInput(
    ns("handoff_directions"),
    label = NULL,
    placeholder = paste(
      "e.g., Use a dark theme, put the revenue chart prominently..."
    ),
    width = "100%",
    autoresize = TRUE
  )
  if (!disabled) {
    return(input)
  }

  htmltools::tagQuery(input) |>
    (\(query) query$find("textarea"))() |>
    (\(query) query$addAttrs(disabled = "disabled"))() |>
    (\(query) query$allTags())()
}

handoff_section_label <- function(text, tooltip, class = "") {
  label_class <- "querychat-handoff-section-label"
  if (nzchar(class)) {
    label_class <- paste(label_class, class)
  }

  htmltools::tags$div(
    text,
    bslib::tooltip(
      htmltools::tags$span(
        bsicons::bs_icon("info-circle"),
        class = "querychat-handoff-info-icon",
        tabindex = "0",
        `aria-label` = "More information"
      ),
      tooltip,
      placement = "top"
    ),
    class = label_class
  )
}
