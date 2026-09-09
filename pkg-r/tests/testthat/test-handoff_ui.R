describe("handoff_html_dependency()", {
  it("declares both handoff browser assets", {
    dependency <- handoff_html_dependency()

    expect_identical(dependency$name, "querychat-handoff")
    expect_identical(dependency$script, "handoff.js")
    expect_identical(dependency$stylesheet, "handoff.css")
    expect_identical(dependency$src$file, "htmldep")
    expect_identical(dependency$package, "querychat")
  })
})

describe("handoff_panel_ui()", {
  ns <- shiny::NS("module")

  it("renders the closed namespaced panel controls and editor", {
    panel <- handoff_panel_ui(ns)
    markup <- as.character(panel)

    expect_snapshot(cat(markup))
    expect_match(markup, 'id="module-handoff_root"', fixed = TRUE)
    expect_match(
      markup,
      'id="module-handoff_source_editor"',
      fixed = TRUE
    )
    expect_match(markup, 'readonly="true"', fixed = TRUE)
    expect_match(markup, 'title="Revise with AI"', fixed = TRUE)
    expect_match(markup, 'aria-label="Revise with AI"', fixed = TRUE)
    expect_match(markup, 'title="Download"', fixed = TRUE)
    expect_match(markup, 'aria-label="Download"', fixed = TRUE)
    expect_match(markup, 'title="Close"', fixed = TRUE)
    expect_match(markup, 'aria-label="Close"', fixed = TRUE)
    expect_no_match(
      markup,
      "querychat-handoff-panel open",
      fixed = TRUE
    )
  })
})

describe("handoff_modal_ui()", {
  ns <- shiny::NS("module")

  it("renders the empty gallery and namespaced language group", {
    modal <- handoff_modal_ui(ns, list())
    markup <- as.character(modal)

    expect_snapshot(cat(markup))
    expect_match(
      markup,
      'id="module-handoff_modal_root"',
      fixed = TRUE
    )
    expect_match(
      markup,
      'name="module-handoff_language"',
      fixed = TRUE
    )
    expect_match(
      markup,
      "querychat-handoff-language-radio",
      fixed = TRUE
    )
    expect_match(
      markup,
      "querychat-handoff-language-icon-python",
      fixed = TRUE
    )
    expect_match(
      markup,
      "querychat-handoff-language-icon-r",
      fixed = TRUE
    )
    expect_match(
      markup,
      'data-handoff-type="marimo-notebook"',
      fixed = TRUE
    )
    expect_match(markup, 'data-languages="python"', fixed = TRUE)
    expect_match(
      markup,
      'data-handoff-type="shiny-app"',
      fixed = TRUE
    )
    expect_match(markup, 'data-languages="python,r"', fixed = TRUE)
  })

  it("renders gallery item attributes and escapes their titles", {
    unsafe_title <- '<script>alert("x")</script> & report'
    items <- list(
      HandoffQueryItem(
        id = "query-0",
        title = unsafe_title,
        sql = "SELECT 1",
        preview_html = NULL
      ),
      HandoffVizItem(
        id = "viz-1",
        title = unsafe_title,
        thumbnail = "data:image/png;base64,abc",
        ggsql = "SELECT 1 VISUALISE x DRAW bar"
      )
    )

    markup <- as.character(handoff_modal_ui(ns, items))

    expect_snapshot(cat(markup))
    expect_match(markup, 'data-item-id="query-0"', fixed = TRUE)
    expect_match(markup, 'data-item-id="viz-1"', fixed = TRUE)
    expect_match(markup, 'draggable="false"', fixed = TRUE)
    expect_no_match(markup, unsafe_title, fixed = TRUE)
    expect_match(
      markup,
      "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; report",
      fixed = TRUE
    )
  })
})

describe("render_handoff_pill()", {
  it("renders Python-compatible data attributes and escapes the label", {
    handoff_type <- HandoffType(
      id = "other",
      label = "<b>R</b> & Co",
      icon = "file-earmark-code",
      language = "r",
      file_extension = ".R",
      editor_language = "r",
      structure = "text"
    )

    markup <- as.character(
      render_handoff_pill(
        "handoff-123",
        handoff_type,
        "module-handoff_open"
      )
    )

    expect_snapshot(cat(markup))
    expect_match(
      markup,
      'data-handoff-id="handoff-123"',
      fixed = TRUE
    )
    expect_match(
      markup,
      'data-input-id="module-handoff_open"',
      fixed = TRUE
    )
    expect_match(markup, "querychat-handoff-pill-open", fixed = TRUE)
    expect_no_match(markup, "<b>R</b>", fixed = TRUE)
    expect_match(markup, "&lt;b&gt;R&lt;/b&gt; &amp; Co", fixed = TRUE)
  })
})
