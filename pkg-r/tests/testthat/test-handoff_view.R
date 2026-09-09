new_handoff_fake_session <- function() {
  session <- new.env(parent = emptyenv())
  session$messages <- list()
  session$ns <- function(id) paste0("module-", id)
  session$sendCustomMessage <- function(type, message) {
    session$messages[[length(session$messages) + 1L]] <- list(
      type = type,
      payload = message
    )
  }
  session
}

new_handoff_fake_chat <- function() {
  chat <- new.env(parent = emptyenv())
  chat$appended <- list()
  chat$append <- function(response, role = "assistant", icon = NULL) {
    chat$appended[[length(chat$appended) + 1L]] <- list(
      response = response,
      role = role,
      icon = icon
    )
  }
  chat
}

new_handoff_view <- function() {
  session <- new_handoff_fake_session()
  chat_module <- new_handoff_fake_chat()
  list(
    view = HandoffView$new(
      session = session,
      chat_module = chat_module
    ),
    session = session,
    chat_module = chat_module
  )
}

describe("HandoffView$new()", {
  it("keeps dependencies and derived IDs private", {
    fixture <- new_handoff_view()
    private_names <- c(
      "session",
      "chat_module",
      "panel_root_id",
      "modal_root_id",
      "editor_id",
      "directions_id",
      "open_input_id"
    )

    expect_length(intersect(names(fixture$view), private_names), 0L)
  })
})

describe("HandoffView$set_panel_open()", {
  it("sends panel toggle messages", {
    fixture <- new_handoff_view()
    view <- fixture$view

    view$set_panel_open(TRUE)
    view$set_panel_open(FALSE)

    expect_identical(
      fixture$session$messages,
      list(
        list(
          type = "querychat-handoff-panel-toggle",
          payload = list(
            root_id = "module-handoff_root",
            open = TRUE
          )
        ),
        list(
          type = "querychat-handoff-panel-toggle",
          payload = list(
            root_id = "module-handoff_root",
            open = FALSE
          )
        )
      )
    )
  })
})

describe("HandoffView$clear_source()", {
  it("clears the editor and disables downloads", {
    fixture <- new_handoff_view()
    view <- fixture$view

    view$clear_source("r")

    expect_identical(
      fixture$session$messages,
      list(
        list(
          type = "querychat-handoff-source-update",
          payload = list(
            root_id = "module-handoff_root",
            id = "module-handoff_source_editor",
            value = "",
            language = "r",
            download_available = FALSE
          )
        )
      )
    )
  })
})

describe("HandoffView$replace_source()", {
  it("replaces the editor source", {
    fixture <- new_handoff_view()
    view <- fixture$view

    view$replace_source("print(1)")

    expect_identical(
      fixture$session$messages[[1]],
      list(
        type = "querychat-handoff-source-update",
        payload = list(
          root_id = "module-handoff_root",
          id = "module-handoff_source_editor",
          value = "print(1)"
        )
      )
    )
  })
})

describe("HandoffView$append_source()", {
  it("appends an editor source delta", {
    fixture <- new_handoff_view()
    view <- fixture$view

    view$append_source("\nprint(2)")

    expect_identical(
      fixture$session$messages[[1]],
      list(
        type = "querychat-handoff-source-update",
        payload = list(
          root_id = "module-handoff_root",
          id = "module-handoff_source_editor",
          value = "\nprint(2)",
          append = TRUE
        )
      )
    )
  })
})

describe("HandoffView$set_streaming()", {
  it("sends streaming state changes", {
    fixture <- new_handoff_view()
    view <- fixture$view

    view$set_streaming(TRUE)
    view$set_streaming(FALSE)

    expect_identical(
      fixture$session$messages,
      list(
        list(
          type = "querychat-handoff-streaming",
          payload = list(
            root_id = "module-handoff_root",
            active = TRUE
          )
        ),
        list(
          type = "querychat-handoff-streaming",
          payload = list(
            root_id = "module-handoff_root",
            active = FALSE
          )
        )
      )
    )
  })
})

describe("HandoffView$show_handoff()", {
  it("shows the current source, language, and download state", {
    fixture <- new_handoff_view()
    view <- fixture$view
    state <- HandoffState(
      handoff_id = "handoff-123",
      handoff_type = resolve_handoff_type("quarto-dashboard", "r"),
      system_prompt = "System prompt",
      source = "library(shiny)"
    )

    view$show_handoff(state, download_available = FALSE)

    expect_identical(
      fixture$session$messages[[1]],
      list(
        type = "querychat-handoff-source-update",
        payload = list(
          root_id = "module-handoff_root",
          id = "module-handoff_source_editor",
          value = "library(shiny)",
          language = "markdown",
          download_available = FALSE
        )
      )
    )
  })
})

describe("HandoffView$show_recommendation()", {
  it("shows a deduplicated recommendation in the modal", {
    fixture <- new_handoff_view()
    view <- fixture$view
    recommendation <- HandoffRecommendation(
      selected_ids = c("query-0", "viz-1", "query-0"),
      format_id = "shiny-app",
      directions = "Use a sidebar."
    )

    view$show_recommendation(recommendation)

    expect_identical(
      fixture$session$messages[[1]],
      list(
        type = "querychat-handoff-recommend",
        payload = list(
          root_id = "module-handoff_modal_root",
          selected_ids = list("query-0", "viz-1"),
          format_id = "shiny-app",
          directions = "Use a sidebar.",
          directions_id = "module-handoff_directions"
        )
      )
    )
  })
})

describe("HandoffView$show_recommendation_error()", {
  it("shows the recommendation error in the modal", {
    fixture <- new_handoff_view()
    view <- fixture$view

    view$show_recommendation_error("Service unavailable")

    expect_identical(
      fixture$session$messages[[1]],
      list(
        type = "querychat-handoff-recommend-error",
        payload = list(
          root_id = "module-handoff_modal_root",
          error = "Service unavailable"
        )
      )
    )
  })
})

describe("HandoffView$show_modal()", {
  it("shows the namespaced modal in its session", {
    shown <- NULL
    local_mocked_bindings(
      showModal = function(ui, session) {
        shown <<- list(ui = ui, session = session)
      },
      .package = "shiny"
    )
    fixture <- new_handoff_view()
    view <- fixture$view

    view$show_modal(list())

    expect_identical(shown$session, fixture$session)
    expect_match(
      as.character(shown$ui),
      'id="module-handoff_modal_root"',
      fixed = TRUE
    )
  })
})

describe("HandoffView$remove_modal()", {
  it("removes the modal from its session", {
    removed_from <- NULL
    local_mocked_bindings(
      removeModal = function(session) {
        removed_from <<- session
      },
      .package = "shiny"
    )
    fixture <- new_handoff_view()
    view <- fixture$view

    view$remove_modal()

    expect_identical(removed_from, fixture$session)
  })
})

describe("HandoffView$append_pill()", {
  it("appends the pill and rendered summary as one assistant message", {
    fixture <- new_handoff_view()
    view <- fixture$view
    handoff_type <- resolve_handoff_type("quarto-dashboard", "python")

    view$append_pill("handoff-123", handoff_type, "A **dashboard**")

    expect_length(fixture$chat_module$appended, 1L)
    appended <- fixture$chat_module$appended[[1]]
    markup <- as.character(appended$response)
    expect_identical(appended$role, "assistant")
    expect_null(appended$icon)
    expect_match(
      markup,
      'data-handoff-id="handoff-123"',
      fixed = TRUE
    )
    expect_match(markup, "<p>A **dashboard**</p>", fixed = TRUE)
    expect_no_match(markup, "<strong>", fixed = TRUE)
  })

  it("escapes untrusted summary markup before appending it", {
    fixture <- new_handoff_view()
    view <- fixture$view
    handoff_type <- resolve_handoff_type("quarto-dashboard", "python")
    summary <- paste0(
      '<img src=x onerror="alert(1)"> ',
      "[click](javascript:alert(2)) ",
      "<script>alert(3)</script>"
    )

    view$append_pill("handoff-123", handoff_type, summary)

    markup <- as.character(fixture$chat_module$appended[[1]]$response)
    expect_no_match(markup, "<img", fixed = TRUE)
    expect_no_match(markup, "<a href=", fixed = TRUE)
    expect_no_match(markup, "<script", fixed = TRUE)
    expect_match(
      markup,
      '&lt;img src=x onerror="alert(1)"&gt;',
      fixed = TRUE
    )
    expect_match(
      markup,
      "[click](javascript:alert(2))",
      fixed = TRUE
    )
    expect_match(
      markup,
      "&lt;script&gt;alert(3)&lt;/script&gt;",
      fixed = TRUE
    )
  })

  it("omits an empty summary", {
    fixture <- new_handoff_view()
    view <- fixture$view
    handoff_type <- resolve_handoff_type("quarto-dashboard", "python")

    view$append_pill("handoff-123", handoff_type, "")

    markup <- as.character(fixture$chat_module$appended[[1]]$response)
    expect_match(
      markup,
      'data-handoff-id="handoff-123"',
      fixed = TRUE
    )
    expect_no_match(markup, "<p>", fixed = TRUE)
  })
})
