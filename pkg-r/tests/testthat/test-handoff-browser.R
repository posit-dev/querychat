# Deterministic shinytest2 coverage for the /handoff browser workflow, driven
# against `apps/handoff/app.R` (two QueryChat modules, each backed by a
# HandoffTestChat that returns queued, deterministic responses instead of
# calling a real model).
#
# NOTE: restore-after-reload is intentionally not covered here. The pinned
# `shinychat@dev/querychat-pr311-history-save` branch's history object
# exposes only `on_save`/`on_restore` -- no `save()` method (confirmed via
# `is.function(chat_module$history$save)` returning FALSE at runtime) -- so
# `handoff_server()` skips the post-commit history save on this build. The
# underlying generation/revision still commits correctly, but the
# chat-history round trip that restore relies on cannot be exercised
# reliably right now. See the PR description for this as a concrete release
# blocker.

local_handoff_app <- function(env = parent.frame()) {
  app <- shinytest2::AppDriver$new(
    test_path("apps", "handoff"),
    name = "handoff",
    height = 1000,
    width = 1400,
    load_timeout = 15000
  )
  withr::defer(app$stop(), envir = env)
  app
}

send_chat_message <- function(app, module_id, text, wait = TRUE) {
  app$run_js(sprintf(
    "
    const editor = document.querySelector('#%s-chat_user_input [contenteditable]');
    editor.focus();
    document.execCommand('insertText', false, %s);
    ",
    module_id,
    jsonlite::toJSON(text)
  ))
  app$click(selector = sprintf("#%s-chat .shiny-chat-btn-send", module_id))
  if (wait) {
    app$wait_for_idle(timeout = 8000)
  }
}

populate_gallery <- function(app, module_id) {
  send_chat_message(app, module_id, "Show me the sales data")
}

open_handoff_modal <- function(app, module_id, wait = TRUE) {
  send_chat_message(app, module_id, "/handoff", wait = wait)
}

select_language <- function(app, module_id, language) {
  app$run_js(sprintf(
    "document.querySelector('#%s-handoff_modal_root .querychat-handoff-language-radio[data-language=\"%s\"]').click()",
    module_id,
    language
  ))
}

select_gallery_item <- function(app, module_id) {
  app$click(
    selector = sprintf(
      "#%s-handoff_modal_root .querychat-handoff-gallery-item",
      module_id
    )
  )
}

click_generate <- function(app, module_id) {
  app$click(selector = sprintf("#%s-handoff_generate", module_id))
  app$wait_for_idle(timeout = 8000)
}

generate_handoff <- function(app, module_id, language = "r") {
  populate_gallery(app, module_id)
  open_handoff_modal(app, module_id)
  Sys.sleep(1)
  select_language(app, module_id, language)
  click_generate(app, module_id)
  Sys.sleep(0.5)
}

panel_open <- function(app, module_id) {
  isTRUE(app$get_js(sprintf(
    "document.querySelector('#%s-handoff_root .querychat-handoff-panel')?.classList.contains('open')",
    module_id
  )))
}

source_editor_value <- function(app, module_id) {
  app$get_js(sprintf(
    "document.getElementById('%s-handoff_source_editor')?.value",
    module_id
  ))
}

download_disabled <- function(app, module_id) {
  isTRUE(app$get_js(sprintf(
    "document.querySelector(\"#%s-handoff_root [id$='handoff_download']\")?.classList.contains('disabled')",
    module_id
  )))
}

describe("handoff modal", {
  it("starts with the panel closed and the gallery empty", {
    app <- local_handoff_app()

    expect_false(panel_open(app, "mod1"))

    open_handoff_modal(app, "mod1")

    expect_true(app$get_js(
      "!!document.querySelector('#mod1-handoff_modal_root .querychat-handoff-gallery-empty')"
    ))
    expect_identical(
      app$get_js(
        "document.getElementById('mod1-handoff_modal_root').closest('.modal').querySelector('.modal-title').textContent"
      ),
      "Prepare Handoff"
    )
  })

  it("shows the query result gallery once a query has run", {
    app <- local_handoff_app()

    populate_gallery(app, "mod1")
    open_handoff_modal(app, "mod1")

    expect_true(app$get_js(
      "!!document.querySelector('#mod1-handoff_modal_root .querychat-handoff-gallery-item')"
    ))
    expect_false(app$get_js(
      "!!document.querySelector('#mod1-handoff_modal_root .querychat-handoff-gallery-empty')"
    ))
  })

  it("transitions the gallery and directions from loading to ready", {
    app <- local_handoff_app()

    populate_gallery(app, "mod1")
    open_handoff_modal(app, "mod1", wait = FALSE)
    Sys.sleep(0.15)

    expect_true(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-gallery')?.classList.contains('loading')"
    ))
    expect_true(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-directions-wrapper')?.classList.contains('loading')"
    ))

    app$wait_for_idle(timeout = 8000)
    Sys.sleep(0.3)

    expect_false(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-gallery')?.classList.contains('loading')"
    ))
    expect_false(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-directions-wrapper')?.classList.contains('loading')"
    ))
    expect_true(app$get_js(
      "!!document.querySelector('#mod1-handoff_modal_root .querychat-handoff-gallery-item.selected')"
    ))
  })

  it("keeps exclusive R/Python selection and disables Marimo's R option", {
    app <- local_handoff_app()

    populate_gallery(app, "mod1")
    open_handoff_modal(app, "mod1")

    select_language(app, "mod1", "r")
    expect_true(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-language-radio[data-language=\"r\"]').checked"
    ))
    expect_false(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-language-radio[data-language=\"python\"]').checked"
    ))

    app$run_js(
      "document.querySelector('#mod1-handoff_modal_root [data-handoff-type=\"marimo-notebook\"]').click()"
    )

    expect_true(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-language-radio[data-language=\"r\"]').disabled"
    ))
    expect_true(app$get_js(
      "document.querySelector('#mod1-handoff_modal_root .querychat-handoff-language-radio[data-language=\"python\"]').checked"
    ))
  })

  it("requires a non-empty format name before Other can generate", {
    app <- local_handoff_app()

    populate_gallery(app, "mod1")
    open_handoff_modal(app, "mod1")
    Sys.sleep(1)
    app$run_js(
      "document.querySelector('#mod1-handoff_modal_root [data-handoff-type=\"other\"]').click()"
    )

    expect_true(app$get_js(
      "document.getElementById('mod1-handoff_generate').disabled"
    ))

    app$run_js(
      "
      const input = document.querySelector('#mod1-handoff_modal_root .querychat-handoff-freeform-input input');
      input.value = 'SQL script';
      input.dispatchEvent(new Event('input', {bubbles: true}));
      "
    )

    expect_false(app$get_js(
      "document.getElementById('mod1-handoff_generate').disabled"
    ))
  })

  it("leaves manual controls usable after a recommendation failure", {
    app <- local_handoff_app()

    populate_gallery(app, "mod2")
    open_handoff_modal(app, "mod2")
    Sys.sleep(1)

    status <- app$get_js(
      "document.querySelector('#mod2-handoff_modal_root .querychat-handoff-loading-status')?.textContent"
    )
    expect_match(status, "Couldn't auto-suggest results", fixed = TRUE)
    expect_true(app$get_js(
      "document.querySelector('#mod2-handoff_modal_root .querychat-handoff-loading-status')?.classList.contains('error')"
    ))

    select_gallery_item(app, "mod2")
    select_language(app, "mod2", "r")

    expect_false(app$get_js(
      "document.getElementById('mod2-handoff_generate').disabled"
    ))
  })
})

describe("handoff generation", {
  it("streams source before completion and clears the spinner afterward", {
    app <- local_handoff_app()

    populate_gallery(app, "mod1")
    open_handoff_modal(app, "mod1")
    Sys.sleep(1)
    select_language(app, "mod1", "r")

    app$click(selector = "#mod1-handoff_generate")
    lengths_seen <- integer()
    for (i in seq_len(40)) {
      Sys.sleep(0.05)
      lengths_seen <- c(lengths_seen, nchar(source_editor_value(app, "mod1")))
    }
    app$wait_for_idle(timeout = 8000)

    distinct_growing_values <- length(unique(lengths_seen[lengths_seen > 0]))
    expect_gte(distinct_growing_values, 3L)
    expect_false(app$get_js(
      "document.querySelector('#mod1-handoff_root .querychat-handoff-panel')?.classList.contains('streaming')"
    ))
    expect_match(
      source_editor_value(app, "mod1"),
      "sales-by-region",
      fixed = TRUE
    )
  })

  it("opens the panel, closes it, and reopens it from its chat pill", {
    app <- local_handoff_app()

    generate_handoff(app, "mod1")

    expect_true(panel_open(app, "mod1"))
    expect_true(app$get_js(
      "!!document.querySelector('.querychat-handoff-pill')"
    ))

    app$click(selector = "#mod1-handoff_close")
    Sys.sleep(0.3)
    expect_false(panel_open(app, "mod1"))

    app$click(selector = ".querychat-handoff-pill")
    Sys.sleep(0.3)
    expect_true(panel_open(app, "mod1"))
  })

  it("revises the handoff and reflects the new source", {
    app <- local_handoff_app()

    generate_handoff(app, "mod1")
    expect_no_match(
      source_editor_value(app, "mod1"),
      "BROWSER_HISTORY",
      fixed = TRUE
    )

    app$click(selector = "#mod1-handoff_root .querychat-handoff-revise-toggle")
    Sys.sleep(0.3)
    app$run_js(
      "
      const ta = document.querySelector('#mod1-handoff_revise_text');
      ta.focus();
      ta.value = 'Make it smaller.';
      ta.dispatchEvent(new Event('input', {bubbles: true}));
    "
    )
    app$click(selector = "#mod1-handoff_revise_text_submit")
    app$wait_for_idle(timeout = 8000)
    Sys.sleep(1)

    expect_match(
      source_editor_value(app, "mod1"),
      "BROWSER_HISTORY",
      fixed = TRUE
    )
  })

  it("downloads a ZIP containing the source, README, and bundled CSV", {
    app <- local_handoff_app()

    generate_handoff(app, "mod1")
    expect_false(download_disabled(app, "mod1"))

    zip_path <- app$get_download("mod1-handoff_download")

    expect_setequal(
      zip::zip_list(zip_path)$filename,
      c("handoff.qmd", "README.md", "sales.csv")
    )
  })
})

describe("handoff module isolation", {
  it("keeps the two QueryChat modules independent", {
    app <- local_handoff_app()

    generate_handoff(app, "mod1")
    mod1_source_before <- source_editor_value(app, "mod1")
    mod1_pill_before <- app$get_js(
      "!!document.querySelector('#mod1-chat .querychat-handoff-pill')"
    )

    populate_gallery(app, "mod2")
    open_handoff_modal(app, "mod2")
    Sys.sleep(1)
    select_gallery_item(app, "mod2")
    select_language(app, "mod2", "r")
    click_generate(app, "mod2")
    Sys.sleep(0.5)

    app$click(selector = "#mod2-handoff_root .querychat-handoff-revise-toggle")
    Sys.sleep(0.2)
    mod2_drawer_open <- app$get_js(
      "document.querySelector('#mod2-handoff_root .querychat-handoff-revise-drawer')?.classList.contains('open')"
    )
    app$click(selector = "#mod2-handoff_close")
    Sys.sleep(0.2)

    expect_true(mod2_drawer_open)
    expect_false(panel_open(app, "mod2"))
    expect_true(panel_open(app, "mod1"))
    expect_identical(source_editor_value(app, "mod1"), mod1_source_before)
    expect_identical(
      app$get_js(
        "!!document.querySelector('#mod1-chat .querychat-handoff-pill')"
      ),
      mod1_pill_before
    )
    expect_false(app$get_js(
      "document.querySelector('#mod1-handoff_root .querychat-handoff-revise-drawer')?.classList.contains('open')"
    ))
  })
})
