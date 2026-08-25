new_test_handoff_target <- function(...) {
  values <- list(
    file_extension = ".qmd",
    editor_language = "markdown",
    structure = "text"
  )
  overrides <- list(...)
  values[names(overrides)] <- overrides
  do.call(HandoffTarget, values)
}

new_test_handoff_format <- function(...) {
  values <- list(
    id = "quarto-dashboard",
    label = "Quarto",
    description = "A Quarto dashboard",
    icon = "grid-1x2-fill",
    targets = list(python = new_test_handoff_target())
  )
  overrides <- list(...)
  values[names(overrides)] <- overrides
  do.call(HandoffFormat, values)
}

new_test_handoff_type <- function(...) {
  values <- list(
    id = "shiny-app",
    label = "Shiny",
    icon = "lightning-fill",
    language = "r",
    file_extension = ".R",
    editor_language = "r",
    structure = "text"
  )
  overrides <- list(...)
  values[names(overrides)] <- overrides
  do.call(HandoffType, values)
}

new_test_handoff_state <- function(...) {
  values <- list(
    handoff_id = "handoff-one",
    handoff_type = new_test_handoff_type(),
    system_prompt = "prompt",
    source = "source"
  )
  overrides <- list(...)
  values[names(overrides)] <- overrides
  do.call(HandoffState, values)
}

new_test_turn <- function(text = "hello") {
  ellmer::UserTurn(list(ellmer::ContentText(text)))
}

count_raw_values <- function(value) {
  if (is.raw(value)) {
    return(1L)
  }
  if (!is.list(value)) {
    return(0L)
  }
  sum(vapply(value, count_raw_values, integer(1)))
}

local_handoff_replay_probe <- function(env = parent.frame()) {
  counter <- new.env(parent = emptyenv())
  counter$calls <- 0L
  probe_class <- NULL
  probe_class <- S7::new_class(
    "HandoffReplayProbe",
    parent = ellmer::Content,
    constructor = function() {
      counter$calls <- counter$calls + 1L
      S7::new_object(probe_class)
    }
  )
  assign("HandoffReplayProbe", probe_class, envir = globalenv())
  withr::defer(
    rm("HandoffReplayProbe", envir = globalenv()),
    envir = env
  )
  counter
}

new_test_handoff_state_with_argument <- function(value) {
  request <- ellmer::ContentToolRequest(
    id = "call-one",
    name = "echo",
    arguments = list(value = value)
  )
  new_test_handoff_state(
    turns = list(ellmer::AssistantTurn(list(request)))
  )
}

valid_registry_fixture <- function() {
  list(
    version = 1L,
    formats = list(
      custom = list(
        label = "Custom",
        description = "A custom format",
        icon = "file-earmark-code",
        targets = list(
          python = list(
            file_extension = ".txt",
            editor_language = "text",
            structure = "text"
          )
        )
      )
    )
  )
}

local_registry_fixture <- function(
  value = valid_registry_fixture(),
  env = parent.frame()
) {
  path <- withr::local_tempfile(.local_envir = env)
  yaml::write_yaml(value, path)
  path
}

expect_invalid_cases <- function(cases, env = parent.frame()) {
  for (case_name in names(cases)) {
    case <- cases[[case_name]]
    expect_error(
      eval(case$call, envir = env),
      regexp = case$pattern,
      info = case_name
    )
  }
}

describe("HandoffTarget", {
  it("constructs valid target metadata", {
    target <- new_test_handoff_target()

    expect_identical(target@file_extension, ".qmd")
    expect_identical(target@editor_language, "markdown")
    expect_identical(target@structure, "text")
  })

  it("validates every property", {
    expect_invalid_cases(list(
      extension_shape = list(
        call = quote(HandoffTarget(character(), "markdown", "text")),
        pattern = "file_extension"
      ),
      extension_safety = list(
        call = quote(new_test_handoff_target(file_extension = "../qmd")),
        pattern = "safe extension"
      ),
      editor_language = list(
        call = quote(new_test_handoff_target(editor_language = "")),
        pattern = "editor_language"
      ),
      structure = list(
        call = quote(new_test_handoff_target(structure = "binary")),
        pattern = "structure"
      )
    ))
  })
})

describe("HandoffFormat", {
  it("constructs a format with named targets", {
    format <- new_test_handoff_format(
      targets = list(
        python = new_test_handoff_target(),
        r = new_test_handoff_target()
      )
    )

    expect_identical(format@id, "quarto-dashboard")
    expect_named(format@targets, c("python", "r"))
    expect_s7_class(format@targets$python, HandoffTarget)
  })

  it("validates all format metadata", {
    expect_invalid_cases(list(
      id = list(
        call = quote(new_test_handoff_format(id = "Bad ID")),
        pattern = "@id"
      ),
      label = list(
        call = quote(new_test_handoff_format(label = " ")),
        pattern = "@label"
      ),
      description = list(
        call = quote(new_test_handoff_format(description = "")),
        pattern = "@description"
      ),
      icon = list(
        call = quote(new_test_handoff_format(icon = "not-an-icon")),
        pattern = "@icon"
      ),
      empty_targets = list(
        call = quote(new_test_handoff_format(targets = list())),
        pattern = "@targets must not be empty"
      ),
      unnamed_targets = list(
        call = quote(
          new_test_handoff_format(targets = list(new_test_handoff_target()))
        ),
        pattern = "uniquely named"
      ),
      target_language = list(
        call = quote(
          new_test_handoff_format(
            targets = list(javascript = new_test_handoff_target())
          )
        ),
        pattern = "python.*r"
      ),
      target_value = list(
        call = quote(
          new_test_handoff_format(targets = list(python = "not a target"))
        ),
        pattern = "HandoffTarget"
      )
    ))
  })
})

describe("HandoffType", {
  it("constructs complete resolved metadata", {
    type <- new_test_handoff_type()

    expect_identical(type@id, "shiny-app")
    expect_identical(type@label, "Shiny")
    expect_identical(type@icon, "lightning-fill")
    expect_identical(type@language, "r")
    expect_identical(type@file_extension, ".R")
    expect_identical(type@editor_language, "r")
    expect_identical(type@structure, "text")
  })

  it("validates every property", {
    expect_invalid_cases(list(
      id = list(
        call = quote(new_test_handoff_type(id = "")),
        pattern = "@id"
      ),
      label = list(
        call = quote(new_test_handoff_type(label = "")),
        pattern = "@label"
      ),
      icon = list(
        call = quote(new_test_handoff_type(icon = "invalid")),
        pattern = "@icon"
      ),
      language = list(
        call = quote(new_test_handoff_type(language = "julia")),
        pattern = "@language"
      ),
      extension = list(
        call = quote(new_test_handoff_type(file_extension = "R")),
        pattern = "@file_extension"
      ),
      editor_language = list(
        call = quote(new_test_handoff_type(editor_language = "")),
        pattern = "@editor_language"
      ),
      structure = list(
        call = quote(new_test_handoff_type(structure = "binary")),
        pattern = "@structure"
      )
    ))
  })
})

describe("HandoffGalleryItem", {
  it("is abstract", {
    expect_snapshot(
      error = TRUE,
      HandoffGalleryItem(id = "query-1", title = "Query")
    )
  })
})

describe("HandoffQueryItem", {
  it("inherits gallery metadata and defaults preview HTML", {
    item <- HandoffQueryItem(
      id = "query-1",
      title = "Top sales",
      sql = "SELECT * FROM sales"
    )

    expect_s7_class(item, HandoffGalleryItem)
    expect_null(item@preview_html)
  })

  it("validates inherited and query properties", {
    expect_invalid_cases(list(
      id = list(
        call = quote(HandoffQueryItem("", "Top sales", "SELECT 1")),
        pattern = "@id"
      ),
      title = list(
        call = quote(HandoffQueryItem("query-1", "", "SELECT 1")),
        pattern = "@title"
      ),
      sql = list(
        call = quote(HandoffQueryItem("query-1", "Top sales", "")),
        pattern = "@sql"
      ),
      preview = list(
        call = quote(
          HandoffQueryItem(
            "query-1",
            "Top sales",
            "SELECT 1",
            preview_html = character()
          )
        ),
        pattern = "@preview_html"
      )
    ))
  })
})

describe("HandoffVizItem", {
  it("inherits gallery metadata and defaults thumbnail", {
    item <- HandoffVizItem(
      id = "viz-1",
      title = "Sales",
      ggsql = "SELECT * FROM sales VISUALISE x DRAW bar"
    )

    expect_s7_class(item, HandoffGalleryItem)
    expect_null(item@thumbnail)
  })

  it("validates inherited and visualization properties", {
    expect_invalid_cases(list(
      id = list(
        call = quote(HandoffVizItem("", "Sales", ggsql = "SELECT 1")),
        pattern = "@id"
      ),
      title = list(
        call = quote(HandoffVizItem("viz-1", "", ggsql = "SELECT 1")),
        pattern = "@title"
      ),
      ggsql = list(
        call = quote(HandoffVizItem("viz-1", "Sales", ggsql = "")),
        pattern = "@ggsql"
      ),
      thumbnail = list(
        call = quote(
          HandoffVizItem(
            "viz-1",
            "Sales",
            thumbnail = character(),
            ggsql = "SELECT 1"
          )
        ),
        pattern = "@thumbnail"
      )
    ))
  })
})

describe("HandoffGenerateRequest", {
  it("has independent empty defaults", {
    first <- HandoffGenerateRequest()
    second <- HandoffGenerateRequest()
    first@selected_ids <- "query-1"

    expect_identical(second@selected_ids, character())
    expect_identical(second@type_id, "")
    expect_identical(second@language, "")
    expect_identical(second@freeform, "")
  })

  it("validates all request fields", {
    expect_invalid_cases(list(
      selected_type = list(
        call = quote(HandoffGenerateRequest(selected_ids = list("query-1"))),
        pattern = "@selected_ids"
      ),
      selected_missing = list(
        call = quote(HandoffGenerateRequest(selected_ids = NA_character_)),
        pattern = "@selected_ids"
      ),
      type_id = list(
        call = quote(HandoffGenerateRequest(type_id = "Bad ID")),
        pattern = "@type_id"
      ),
      language = list(
        call = quote(HandoffGenerateRequest(language = "julia")),
        pattern = "@language"
      ),
      freeform = list(
        call = quote(HandoffGenerateRequest(freeform = character())),
        pattern = "@freeform"
      )
    ))
  })
})

describe("HandoffRecommendation", {
  it("defaults directions", {
    recommendation <- HandoffRecommendation(
      selected_ids = c("viz-1", "query-1"),
      format_id = "quarto-dashboard"
    )

    expect_identical(recommendation@directions, "")
  })

  it("validates all recommendation fields", {
    expect_invalid_cases(list(
      selected_type = list(
        call = quote(
          HandoffRecommendation(
            selected_ids = list("viz-1"),
            format_id = "quarto-dashboard"
          )
        ),
        pattern = "@selected_ids"
      ),
      selected_missing = list(
        call = quote(
          HandoffRecommendation(
            selected_ids = NA_character_,
            format_id = "quarto-dashboard"
          )
        ),
        pattern = "@selected_ids"
      ),
      format = list(
        call = quote(
          HandoffRecommendation("viz-1", format_id = "Bad ID")
        ),
        pattern = "@format_id"
      ),
      directions = list(
        call = quote(
          HandoffRecommendation(
            "viz-1",
            "quarto-dashboard",
            directions = character()
          )
        ),
        pattern = "@directions"
      )
    ))
  })
})

describe("HandoffResult", {
  it("has independent metadata defaults", {
    first <- HandoffResult(source = "x", language = "python")
    second <- HandoffResult(source = "x", language = "python")
    first@referenced_tables <- "sales"

    expect_identical(second@summary, "")
    expect_identical(second@install_instructions, "")
    expect_identical(second@run_instructions, "")
    expect_identical(second@referenced_tables, character())
  })

  it("validates every result field", {
    expect_invalid_cases(list(
      source = list(
        call = quote(HandoffResult(character(), "python")),
        pattern = "@source"
      ),
      language = list(
        call = quote(HandoffResult("x", "julia")),
        pattern = "@language"
      ),
      summary = list(
        call = quote(HandoffResult("x", "python", summary = character())),
        pattern = "@summary"
      ),
      install = list(
        call = quote(
          HandoffResult("x", "python", install_instructions = character())
        ),
        pattern = "@install_instructions"
      ),
      run = list(
        call = quote(
          HandoffResult("x", "python", run_instructions = character())
        ),
        pattern = "@run_instructions"
      ),
      tables_type = list(
        call = quote(
          HandoffResult("x", "python", referenced_tables = list("sales"))
        ),
        pattern = "@referenced_tables"
      ),
      tables_missing = list(
        call = quote(
          HandoffResult("x", "python", referenced_tables = NA_character_)
        ),
        pattern = "@referenced_tables"
      )
    ))
  })
})

describe("HandoffState", {
  it("validates real turns and has independent defaults", {
    turn <- new_test_turn()
    first <- new_test_handoff_state(turns = list(turn))
    second <- new_test_handoff_state(handoff_id = "handoff-two")

    expect_s7_class(first@turns[[1]], ellmer::Turn)
    expect_identical(second@turns, list())
    expect_identical(second@summary, "")
    expect_identical(second@install_instructions, "")
    expect_identical(second@run_instructions, "")
    expect_identical(second@referenced_tables, character())
    expect_identical(second@bundled_tables, character())
    expect_null(second@bundle_id)
    expect_identical(second@data_instructions, "")
  })

  it("requires ellmer turns on construction and assignment", {
    state <- new_test_handoff_state()

    expect_error(
      new_test_handoff_state(turns = list("turn")),
      "@turns values must be <ellmer::Turn>"
    )
    expect_error(
      state@turns <- list("turn"),
      "@turns values must be <ellmer::Turn>"
    )
    expect_identical(state@turns, list())
  })

  it("validates every other state property", {
    expect_invalid_cases(list(
      id = list(
        call = quote(new_test_handoff_state(handoff_id = "")),
        pattern = "@handoff_id"
      ),
      type = list(
        call = quote(new_test_handoff_state(handoff_type = "not a type")),
        pattern = "@handoff_type"
      ),
      prompt = list(
        call = quote(new_test_handoff_state(system_prompt = character())),
        pattern = "@system_prompt"
      ),
      source = list(
        call = quote(new_test_handoff_state(source = character())),
        pattern = "@source"
      ),
      turns_type = list(
        call = quote(new_test_handoff_state(turns = "turn")),
        pattern = "@turns"
      ),
      summary = list(
        call = quote(new_test_handoff_state(summary = character())),
        pattern = "@summary"
      ),
      install = list(
        call = quote(
          new_test_handoff_state(install_instructions = character())
        ),
        pattern = "@install_instructions"
      ),
      run = list(
        call = quote(new_test_handoff_state(run_instructions = character())),
        pattern = "@run_instructions"
      ),
      referenced = list(
        call = quote(
          new_test_handoff_state(referenced_tables = NA_character_)
        ),
        pattern = "@referenced_tables"
      ),
      bundled = list(
        call = quote(new_test_handoff_state(bundled_tables = list("sales"))),
        pattern = "@bundled_tables"
      ),
      bundle = list(
        call = quote(new_test_handoff_state(bundle_id = "")),
        pattern = "@bundle_id"
      ),
      data = list(
        call = quote(new_test_handoff_state(data_instructions = character())),
        pattern = "@data_instructions"
      )
    ))
  })
})

describe("handoff_state_record()", {
  it("round-trips bounded state metadata and ellmer turns through JSON", {
    turns <- list(
      new_test_turn("Create an app"),
      ellmer::AssistantTurn(list(ellmer::ContentText("Here is the app")))
    )
    state <- new_test_handoff_state(
      turns = turns,
      summary = "An app",
      install_instructions = "pak::pak('shiny')",
      run_instructions = "shiny::runApp()",
      referenced_tables = "sales",
      bundled_tables = "sales",
      bundle_id = "bundle-one",
      data_instructions = "Load sales.csv"
    )

    record <- handoff_state_record(state)
    json <- jsonlite::serializeJSON(
      list(version = 1L, states = list(record))
    )
    decoded <- jsonlite::unserializeJSON(json)
    restored <- handoff_state_from_record(decoded$states[[1]])

    expect_identical(restored@handoff_id, state@handoff_id)
    expect_identical(restored@handoff_type, state@handoff_type)
    expect_identical(restored@system_prompt, state@system_prompt)
    expect_identical(restored@source, state@source)
    expect_equal(restored@turns, state@turns)
    expect_identical(restored@summary, state@summary)
    expect_identical(
      restored@install_instructions,
      state@install_instructions
    )
    expect_identical(restored@run_instructions, state@run_instructions)
    expect_identical(restored@referenced_tables, state@referenced_tables)
    expect_identical(restored@bundled_tables, state@bundled_tables)
    expect_identical(restored@bundle_id, state@bundle_id)
    expect_identical(restored@data_instructions, state@data_instructions)
    expect_identical(count_raw_values(record), 0L)
  })

  it("normalizes failed tool conditions for JSON round trips", {
    tool <- ellmer::tool(
      function(value) value,
      "Echo a value",
      arguments = list(value = ellmer::type_string()),
      name = "echo"
    )
    request <- ellmer::ContentToolRequest(
      id = "call-one",
      name = "echo",
      arguments = list(value = "hello"),
      tool = tool
    )
    state <- new_test_handoff_state(
      turns = list(ellmer::UserTurn(list(ellmer::ContentToolResult(
        error = simpleError("boom"),
        request = request
      ))))
    )

    record <- handoff_state_record(state)
    result_record <- record$turns[[1]]$props$contents[[1]]
    json <- jsonlite::serializeJSON(
      list(version = 1L, states = list(record))
    )
    decoded <- jsonlite::unserializeJSON(json)
    restored <- handoff_state_from_record(
      decoded$states[[1]],
      tools = list(echo = tool)
    )
    result <- restored@turns[[1]]@contents[[1]]

    expect_identical(result_record$props$error, "boom")
    expect_null(attributes(result_record$props$error))
    expect_identical(result@error, "boom")
    expect_null(result@value)
    expect_identical(result@request@tool, tool)
  })

  it("rejects non-inert values preserved by ellmer records", {
    cases <- list(
      closure = function() NULL,
      environment = new.env(parent = emptyenv()),
      external_pointer = methods::new("externalptr"),
      raw = charToRaw("bytes"),
      data_frame = data.frame(value = 1),
      matrix = matrix(1:4, nrow = 2),
      s3 = structure(list(value = 1), class = "handoff_probe"),
      s4 = methods::new("classRepresentation"),
      s7 = ellmer::ContentText("nested"),
      attributed = structure("value", marker = TRUE),
      infinite = Inf,
      nan = NaN
    )

    state <- new_test_handoff_state_with_argument(cases$closure)
    expect_snapshot(
      error = TRUE,
      invisible(handoff_state_record(state))
    )

    cases$closure <- NULL
    for (case_name in names(cases)) {
      state <- new_test_handoff_state_with_argument(cases[[case_name]])
      error <- tryCatch(
        {
          handoff_state_record(state)
          NULL
        },
        error = identity
      )
      expect_s3_class(error, "error")
      expected <- paste(
        "Handoff records may contain only inert JSON values",
        "and plain lists."
      )
      if (identical(case_name, "s7")) {
        expected <- paste(
          "Handoff ellmer record data must not contain nested",
          "recorded objects."
        )
      }
      if (inherits(error, "error")) {
        expect_identical(conditionMessage(error), expected, info = case_name)
      }
    }
  })

  it("requires a HandoffState input", {
    error <- tryCatch(
      handoff_state_record(list()),
      error = identity
    )

    expect_s3_class(error, "error")
    expect_identical(
      conditionMessage(error),
      "`state` must be a <HandoffState> object."
    )
    expect_snapshot(
      error = TRUE,
      handoff_state_record(list())
    )
  })

  it("rejects non-inert state metadata and named turns", {
    attributed_source <- new_test_handoff_state(
      source = structure("source", marker = TRUE)
    )
    expect_snapshot(
      error = TRUE,
      handoff_state_record(attributed_source)
    )

    attributed_type <- new_test_handoff_state(
      handoff_type = new_test_handoff_type(
        label = structure("Shiny", marker = TRUE)
      )
    )
    named_turns <- new_test_handoff_state(
      turns = list(first = new_test_turn())
    )
    cases <- list(
      attributed_type = attributed_type,
      named_turns = named_turns
    )
    expected <- c(
      attributed_type = paste(
        "Handoff records may contain only inert JSON values",
        "and plain lists."
      ),
      named_turns = paste(
        "Handoff state record `turns` must be an unnamed",
        "plain list."
      )
    )

    for (case_name in names(cases)) {
      error <- tryCatch(
        {
          handoff_state_record(cases[[case_name]])
          NULL
        },
        error = identity
      )
      expect_s3_class(error, "error")
      if (inherits(error, "error")) {
        expect_identical(
          conditionMessage(error),
          expected[[case_name]],
          info = case_name
        )
      }
    }
  })
})

describe("handoff_state_from_record()", {
  it("passes tools to ellmer turn replay without recording executables", {
    tool <- ellmer::tool(
      function(value) value,
      "Echo a value",
      arguments = list(value = ellmer::type_string()),
      name = "echo"
    )
    request <- ellmer::ContentToolRequest(
      id = "call-one",
      name = "echo",
      arguments = list(value = "hello"),
      tool = tool
    )
    state <- new_test_handoff_state(
      turns = list(ellmer::AssistantTurn(list(request)))
    )

    record <- handoff_state_record(state)
    restored <- handoff_state_from_record(
      record,
      tools = list(echo = tool)
    )

    request_record <- record$turns[[1]]$props$contents[[1]]
    expect_setequal(
      names(request_record$props),
      c("id", "name", "arguments", "extra")
    )
    expect_identical(restored@turns[[1]]@contents[[1]]@tool, tool)
  })

  it("round-trips supported structured and tool result records", {
    tool <- ellmer::tool(
      function(value) value,
      "Echo a value",
      arguments = list(value = ellmer::type_string()),
      name = "echo"
    )
    request <- ellmer::ContentToolRequest(
      id = "call-one",
      name = "echo",
      arguments = list(value = "hello"),
      tool = tool,
      extra = list(provider = "test")
    )
    content_json <- asNamespace("ellmer")[["ContentJson"]]
    state <- new_test_handoff_state(
      turns = list(
        ellmer::AssistantTurn(list(
          content_json(data = list(source = "app", language = "r"))
        )),
        ellmer::AssistantTurn(list(request)),
        ellmer::UserTurn(list(ellmer::ContentToolResult(
          value = list(ok = TRUE),
          extra = list(provider = "test"),
          request = request
        )))
      )
    )

    record <- handoff_state_record(state)
    restored <- handoff_state_from_record(
      record,
      tools = list(echo = tool)
    )

    expect_identical(
      restored@turns[[1]]@contents[[1]]@parsed,
      list(source = "app", language = "r")
    )
    expect_identical(
      restored@turns[[2]]@contents[[1]]@tool,
      tool
    )
    expect_identical(
      restored@turns[[3]]@contents[[1]]@request@tool,
      tool
    )
  })

  it("round-trips ContentThinking with exact inert props", {
    content_thinking <- asNamespace("ellmer")[["ContentThinking"]]
    content_json <- asNamespace("ellmer")[["ContentJson"]]
    thinking <- content_thinking(
      thinking = "private reasoning",
      extra = list(signature = "sig")
    )
    state <- new_test_handoff_state(
      turns = list(ellmer::AssistantTurn(list(
        thinking,
        content_json(data = list(answer = 42L))
      )))
    )

    record <- handoff_state_record(state)
    json <- jsonlite::serializeJSON(
      list(version = 1L, states = list(record))
    )
    decoded <- jsonlite::unserializeJSON(json)
    restored <- handoff_state_from_record(decoded$states[[1]])

    thinking_record <- record$turns[[1]]$props$contents[[1]]
    expect_identical(
      names(thinking_record$props),
      c("thinking", "extra")
    )
    expect_identical(
      restored@turns[[1]]@contents[[1]]@thinking,
      thinking@thinking
    )
    expect_identical(
      restored@turns[[1]]@contents[[1]]@extra,
      thinking@extra
    )
    expect_identical(
      restored@turns[[1]]@contents[[2]]@parsed,
      list(answer = 42L)
    )
  })

  it("rejects malformed ContentThinking before replay", {
    content_thinking <- asNamespace("ellmer")[["ContentThinking"]]
    thinking <- content_thinking(
      thinking = "private reasoning",
      extra = list(signature = "sig")
    )
    record <- handoff_state_record(new_test_handoff_state())
    record$turns <- list(ellmer::contents_record(
      ellmer::AssistantTurn(list(thinking))
    ))

    malformed_thinking <- record
    malformed_thinking$turns[[1]]$props$contents[[1]]$props$thinking <- 1
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(malformed_thinking)
    )

    unexpected_prop <- record
    unexpected_prop$turns[[1]]$props$contents[[1]]$props$trace <- "trace"
    error <- tryCatch(
      handoff_state_from_record(unexpected_prop),
      error = identity
    )
    expect_s3_class(error, "error")
    expect_identical(
      conditionMessage(error),
      'Ellmer ContentThinking props has unexpected field: "trace".'
    )

    counter <- local_handoff_replay_probe()
    nested_record <- record
    nested_record$turns[[1]]$props$contents[[1]]$props$extra$payload <- list(
      version = 1,
      class = "HandoffReplayProbe",
      props = list()
    )
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(nested_record)
    )
    expect_identical(counter$calls, 0L)
  })

  it("rejects unapproved classes before constructor resolution", {
    counter <- local_handoff_replay_probe()
    record <- handoff_state_record(new_test_handoff_state())
    record$turns <- list(list(
      version = 1,
      class = "ellmer::UserTurn",
      props = list(
        contents = list(list(
          version = 1,
          class = "HandoffReplayProbe",
          props = list()
        ))
      )
    ))

    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )
    expect_identical(counter$calls, 0L)
  })

  it("rejects record-shaped tool arguments before constructor resolution", {
    counter <- local_handoff_replay_probe()
    request <- ellmer::ContentToolRequest(
      id = "call-one",
      name = "echo",
      arguments = list(value = "hello")
    )
    state <- new_test_handoff_state(
      turns = list(ellmer::AssistantTurn(list(request)))
    )
    record <- handoff_state_record(state)
    record$turns[[1]]$props$contents[[1]]$props$arguments <- list(
      payload = list(
        version = 1,
        class = "HandoffReplayProbe",
        props = list()
      )
    )

    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )
    expect_identical(counter$calls, 0L)
  })

  it("rejects non-inert incoming tool values", {
    state <- new_test_handoff_state_with_argument("value")
    record <- handoff_state_record(state)
    record$turns[[1]]$props$contents[[1]]$props$arguments$value <-
      function() NULL

    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )

    request <- ellmer::ContentToolRequest(
      id = "call-one",
      name = "echo"
    )
    failed_state <- new_test_handoff_state(
      turns = list(ellmer::UserTurn(list(ellmer::ContentToolResult(
        error = "boom",
        request = request
      ))))
    )
    failed_record <- handoff_state_record(failed_state)
    failed_record$turns[[1]]$props$contents[[1]]$props$error <-
      simpleError("boom")
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(failed_record)
    )
  })

  it("rejects non-plain state and turn containers", {
    record <- handoff_state_record(new_test_handoff_state())
    class(record) <- "handoff_record"
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )

    null_turns <- handoff_state_record(new_test_handoff_state())
    null_turns["turns"] <- list(NULL)
    named_turns <- handoff_state_record(new_test_handoff_state(
      turns = list(new_test_turn())
    ))
    names(named_turns$turns) <- "first"
    classed_turn <- handoff_state_record(new_test_handoff_state(
      turns = list(new_test_turn())
    ))
    class(classed_turn$turns[[1]]) <- "handoff_turn_record"
    cases <- list(
      null_turns = null_turns,
      named_turns = named_turns,
      classed_turn = classed_turn
    )
    expected <- c(
      null_turns = paste(
        "Handoff state record `turns` must be an unnamed",
        "plain list."
      ),
      named_turns = paste(
        "Handoff state record `turns` must be an unnamed",
        "plain list."
      ),
      classed_turn = "Ellmer turn record must be a plain list."
    )

    for (case_name in names(cases)) {
      error <- tryCatch(
        {
          handoff_state_from_record(cases[[case_name]])
          NULL
        },
        error = identity
      )
      expect_s3_class(error, "error")
      if (inherits(error, "error")) {
        expect_identical(
          conditionMessage(error),
          expected[[case_name]],
          info = case_name
        )
      }
    }
  })

  it("rejects unexpected ellmer record fields and props", {
    state <- new_test_handoff_state(turns = list(new_test_turn()))

    extra_turn_field <- handoff_state_record(state)
    extra_turn_field$turns[[1]]$extra <- TRUE
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(extra_turn_field)
    )

    unnamed_turn_props <- handoff_state_record(state)
    unnamed_turn_props$turns[[1]]$props <- unname(
      unnamed_turn_props$turns[[1]]$props
    )
    extra_turn_prop <- handoff_state_record(state)
    extra_turn_prop$turns[[1]]$props$extra <- TRUE
    extra_content_field <- handoff_state_record(state)
    extra_content_field$turns[[1]]$props$contents[[1]]$extra <- TRUE
    unnamed_content_props <- handoff_state_record(state)
    unnamed_content_props$turns[[1]]$props$contents[[1]]$props <- unname(
      unnamed_content_props$turns[[1]]$props$contents[[1]]$props
    )
    extra_content_prop <- handoff_state_record(state)
    extra_content_prop$turns[[1]]$props$contents[[1]]$props$extra <- TRUE
    cases <- list(
      unnamed_turn_props = unnamed_turn_props,
      extra_turn_prop = extra_turn_prop,
      extra_content_field = extra_content_field,
      unnamed_content_props = unnamed_content_props,
      extra_content_prop = extra_content_prop
    )
    expected <- c(
      unnamed_turn_props = "Ellmer UserTurn props must be a mapping.",
      extra_turn_prop = paste(
        "Ellmer UserTurn props has unexpected field:",
        '"extra".'
      ),
      extra_content_field = paste(
        "Ellmer content record has unexpected field:",
        '"extra".'
      ),
      unnamed_content_props = "Ellmer ContentText props must be a mapping.",
      extra_content_prop = paste(
        "Ellmer ContentText props has unexpected field:",
        '"extra".'
      )
    )

    for (case_name in names(cases)) {
      error <- tryCatch(
        {
          handoff_state_from_record(cases[[case_name]])
          NULL
        },
        error = identity
      )
      expect_s3_class(error, "error")
      if (inherits(error, "error")) {
        expect_identical(
          conditionMessage(error),
          expected[[case_name]],
          info = case_name
        )
      }
    }
  })

  it("rejects attributed ellmer class metadata", {
    record <- handoff_state_record(new_test_handoff_state(
      turns = list(new_test_turn())
    ))
    record$turns[[1]]$class <- structure(
      "ellmer::UserTurn",
      marker = TRUE
    )
    error <- tryCatch(
      handoff_state_from_record(record),
      error = identity
    )

    expect_s3_class(error, "error")
    if (inherits(error, "error")) {
      expect_identical(
        conditionMessage(error),
        paste(
          "Handoff ellmer record class must be a single",
          "un-attributed string."
        )
      )
    }
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )
  })

  it("rejects malformed ellmer prop values before replay", {
    text <- handoff_state_record(new_test_handoff_state(
      turns = list(new_test_turn())
    ))
    text$turns[[1]]$props$contents[[1]]$props$text <- 1
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(text)
    )

    assistant_json <- handoff_state_record(new_test_handoff_state(
      turns = list(ellmer::AssistantTurn())
    ))
    assistant_json$turns[[1]]$props$json <- "not a list"
    assistant_tokens <- handoff_state_record(new_test_handoff_state(
      turns = list(ellmer::AssistantTurn())
    ))
    assistant_tokens$turns[[1]]$props$tokens <- c(1, 2)
    request_arguments <- handoff_state_record(
      new_test_handoff_state_with_argument("value")
    )
    request_arguments$turns[[1]]$props$contents[[1]]$props$arguments <-
      "not a list"
    result_request <- handoff_state_record(new_test_handoff_state(
      turns = list(ellmer::UserTurn(list(ellmer::ContentToolResult(
        request = ellmer::ContentToolRequest("call-one", "echo")
      ))))
    ))
    result_request$turns[[1]]$props$contents[[1]]$props$request$class <-
      "ellmer::ContentText"
    result_request$turns[[1]]$props$contents[[1]]$props$request$props <-
      list(text = "not a request")
    cases <- list(
      assistant_json = assistant_json,
      assistant_tokens = assistant_tokens,
      request_arguments = request_arguments,
      result_request = result_request
    )
    expected <- c(
      assistant_json = paste(
        "Ellmer AssistantTurn prop `json` must be a plain list."
      ),
      assistant_tokens = paste(
        "Ellmer AssistantTurn prop `tokens` must be a",
        "length-three numeric vector."
      ),
      request_arguments = paste(
        "Ellmer ContentToolRequest prop `arguments` must be a plain list."
      ),
      result_request = paste(
        "Ellmer ContentToolResult `request` must be",
        "an ellmer::ContentToolRequest record."
      )
    )

    for (case_name in names(cases)) {
      error <- tryCatch(
        {
          handoff_state_from_record(cases[[case_name]])
          NULL
        },
        error = identity
      )
      expect_s3_class(error, "error")
      if (inherits(error, "error")) {
        expect_identical(
          conditionMessage(error),
          expected[[case_name]],
          info = case_name
        )
      }
    }
  })

  it("rejects missing tool result requests before replay", {
    request <- ellmer::ContentToolRequest(
      id = "call-one",
      name = "echo"
    )
    state <- new_test_handoff_state(
      turns = list(ellmer::UserTurn(list(ellmer::ContentToolResult(
        value = "ok",
        request = request
      ))))
    )
    record <- handoff_state_record(state)

    missing_request <- record
    missing_request$turns[[1]]$props$contents[[1]]$props$request <- NULL
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(missing_request)
    )

    null_request <- record
    null_request$turns[[1]]$props$contents[[1]]$props["request"] <- list(NULL)
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(null_request)
    )
  })

  it("validates state and type metadata before turn replay", {
    counter <- local_handoff_replay_probe()
    malformed_source <- handoff_state_record(new_test_handoff_state())
    malformed_source$source <- 1
    malformed_source$turns <- list(list(
      version = 1,
      class = "ellmer::UserTurn",
      props = list(
        contents = list(list(
          version = 1,
          class = "HandoffReplayProbe",
          props = list()
        ))
      )
    ))
    error <- tryCatch(
      handoff_state_from_record(malformed_source),
      error = identity
    )

    expect_s3_class(error, "error")
    expect_identical(
      conditionMessage(error),
      "`source` must be a single non-missing string"
    )
    expect_identical(counter$calls, 0L)
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(malformed_source)
    )

    attributed_source <- handoff_state_record(new_test_handoff_state())
    attributed_source$source <- structure("source", marker = TRUE)
    attributed_type <- handoff_state_record(new_test_handoff_state())
    attributed_type$handoff_type$label <- structure(
      "Shiny",
      marker = TRUE
    )
    for (record in list(attributed_source, attributed_type)) {
      error <- tryCatch(
        handoff_state_from_record(record),
        error = identity
      )
      expect_s3_class(error, "error")
      if (inherits(error, "error")) {
        expect_identical(
          conditionMessage(error),
          paste(
            "Handoff records may contain only inert JSON values",
            "and plain lists."
          )
        )
      }
    }
  })

  it("rejects unsupported record versions", {
    record <- handoff_state_record(new_test_handoff_state())
    record$version <- 2L

    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )
  })

  it("rejects malformed records", {
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record("not a record")
    )

    record <- handoff_state_record(new_test_handoff_state())
    record$source <- NULL
    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )
  })

  it("rejects unknown type metadata", {
    record <- handoff_state_record(new_test_handoff_state())
    record$handoff_type$renderer <- "html"

    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )
  })

  it("rejects ellmer record versions before replay", {
    state <- new_test_handoff_state(turns = list(new_test_turn()))
    record <- handoff_state_record(state)
    record$turns[[1]]$version <- 2

    expect_snapshot(
      error = TRUE,
      handoff_state_from_record(record)
    )
  })
})

describe("HandoffBundle", {
  it("constructs named raw file contents", {
    bundle <- HandoffBundle(
      bundle_id = "bundle-1",
      bundled_files = list("sales.csv" = charToRaw("x\n1"))
    )

    expect_identical(bundle@bundle_id, "bundle-1")
    expect_named(bundle@bundled_files, "sales.csv")
  })

  it("validates the bundle ID and file mapping", {
    expect_invalid_cases(list(
      id = list(
        call = quote(
          HandoffBundle("", list("sales.csv" = charToRaw("x")))
        ),
        pattern = "@bundle_id"
      ),
      names = list(
        call = quote(HandoffBundle("bundle-1", list(charToRaw("x")))),
        pattern = "uniquely named"
      ),
      contents = list(
        call = quote(HandoffBundle("bundle-1", list("sales.csv" = "x"))),
        pattern = "raw vectors"
      )
    ))
  })
})

describe("failed S7 property assignment", {
  it("leaves scalar, list, nullable, and raw properties unchanged", {
    target <- new_test_handoff_target()
    format <- new_test_handoff_format()
    query <- HandoffQueryItem("query-1", "Query", "SELECT 1")
    bundle <- HandoffBundle(
      "bundle-1",
      list("sales.csv" = charToRaw("x"))
    )

    expect_error(target@structure <- "binary", "@structure")
    expect_identical(target@structure, "text")

    expect_error(
      format@targets <- list(python = "not a target"),
      "HandoffTarget"
    )
    expect_s7_class(format@targets$python, HandoffTarget)

    expect_error(query@preview_html <- character(), "@preview_html")
    expect_null(query@preview_html)

    expect_error(
      bundle@bundled_files <- list("sales.csv" = "x"),
      "raw vectors"
    )
    expect_identical(bundle@bundled_files, list("sales.csv" = charToRaw("x")))
  })
})

describe("load_handoff_registry()", {
  it("loads all built-in formats and target languages", {
    registry <- load_handoff_registry()

    expect_named(
      registry,
      c(
        "quarto-dashboard",
        "marimo-notebook",
        "shiny-app",
        "jupyter-notebook"
      )
    )
    expect_named(registry[["quarto-dashboard"]]@targets, c("python", "r"))
    expect_named(registry[["marimo-notebook"]]@targets, "python")
    expect_named(registry[["shiny-app"]]@targets, c("python", "r"))
    expect_named(registry[["jupyter-notebook"]]@targets, c("python", "r"))
  })

  it("normalizes mapping keys into format IDs", {
    registry <- load_handoff_registry(local_registry_fixture())

    expect_identical(registry$custom@id, "custom")
  })

  it("rejects invalid registry shapes", {
    root_sequence <- list("version")
    bad_version <- valid_registry_fixture()
    bad_version$version <- 2L
    missing_formats <- valid_registry_fixture()
    missing_formats$formats <- NULL
    formats_sequence <- valid_registry_fixture()
    formats_sequence$formats <- list("custom")
    empty_formats <- valid_registry_fixture()
    empty_formats$formats <- structure(list(), names = character())
    scalar_entry <- valid_registry_fixture()
    scalar_entry$formats$custom <- "nope"
    missing_format_field <- valid_registry_fixture()
    missing_format_field$formats$custom$targets <- NULL
    extra_format_field <- valid_registry_fixture()
    extra_format_field$formats$custom$extra <- "value"
    empty_targets <- valid_registry_fixture()
    empty_targets$formats$custom$targets <- structure(
      list(),
      names = character()
    )
    scalar_target <- valid_registry_fixture()
    scalar_target$formats$custom$targets$python <- "nope"
    missing_target_field <- valid_registry_fixture()
    missing_target_field$formats$custom$targets$python$structure <- NULL
    extra_target_field <- valid_registry_fixture()
    extra_target_field$formats$custom$targets$python$extra <- "value"

    cases <- list(
      root = list(root_sequence, "registry must be a mapping"),
      version = list(bad_version, "version must be exactly 1"),
      missing_formats = list(
        missing_formats,
        "missing required field.*formats"
      ),
      formats_sequence = list(formats_sequence, "formats must be a mapping"),
      empty_formats = list(empty_formats, "formats must not be empty"),
      scalar_entry = list(scalar_entry, "format entry must be a mapping"),
      missing_format_field = list(
        missing_format_field,
        "missing required field.*targets"
      ),
      extra_format_field = list(
        extra_format_field,
        "unexpected field.*extra"
      ),
      empty_targets = list(empty_targets, "targets must not be empty"),
      scalar_target = list(scalar_target, "target must be a mapping"),
      missing_target_field = list(
        missing_target_field,
        "missing required field.*structure"
      ),
      extra_target_field = list(
        extra_target_field,
        "unexpected field.*extra"
      )
    )

    for (case_name in names(cases)) {
      case <- cases[[case_name]]
      expect_error(
        load_handoff_registry(local_registry_fixture(case[[1]])),
        case[[2]],
        info = case_name
      )
    }
  })

  it("rejects invalid registry values", {
    invalid_id <- valid_registry_fixture()
    names(invalid_id$formats) <- "Bad ID"
    blank_label <- valid_registry_fixture()
    blank_label$formats$custom$label <- ""
    blank_description <- valid_registry_fixture()
    blank_description$formats$custom$description <- ""
    bad_icon <- valid_registry_fixture()
    bad_icon$formats$custom$icon <- "not-an-icon"
    bad_language <- valid_registry_fixture()
    names(bad_language$formats$custom$targets) <- "javascript"
    bad_extension <- valid_registry_fixture()
    bad_extension$formats$custom$targets$python$file_extension <- "txt"
    unsafe_extension <- valid_registry_fixture()
    unsafe_extension$formats$custom$targets$python$file_extension <- "../txt"
    blank_editor <- valid_registry_fixture()
    blank_editor$formats$custom$targets$python$editor_language <- ""
    bad_structure <- valid_registry_fixture()
    bad_structure$formats$custom$targets$python$structure <- "binary"

    cases <- list(
      id = list(invalid_id, "format ID"),
      label = list(blank_label, "@label"),
      description = list(blank_description, "@description"),
      icon = list(bad_icon, "@icon"),
      language = list(bad_language, "target language"),
      extension = list(bad_extension, "@file_extension"),
      unsafe_extension = list(unsafe_extension, "@file_extension"),
      editor = list(blank_editor, "@editor_language"),
      structure = list(bad_structure, "@structure")
    )

    for (case_name in names(cases)) {
      case <- cases[[case_name]]
      expect_error(
        load_handoff_registry(local_registry_fixture(case[[1]])),
        case[[2]],
        info = case_name
      )
    }
  })

  it("shows a representative root diagnostic", {
    expect_snapshot(
      error = TRUE,
      load_handoff_registry(local_registry_fixture(list("version")))
    )
  })
})

describe("handoff_registry()", {
  it("returns a fresh valid default registry", {
    first <- handoff_registry()
    second <- handoff_registry()
    first[["shiny-app"]]@label <- "Changed"

    expect_identical(second[["shiny-app"]]@label, "Shiny")
  })
})

describe("resolve_handoff_target()", {
  it("resolves complete built-in target metadata", {
    python <- resolve_handoff_target("shiny-app", "python")
    r <- resolve_handoff_target("shiny-app", "r")

    expect_identical(python@file_extension, ".py")
    expect_identical(python@editor_language, "python")
    expect_identical(python@structure, "text")
    expect_identical(r@file_extension, ".R")
    expect_identical(r@editor_language, "r")
    expect_identical(r@structure, "text")
  })

  it("rejects unknown formats and unsupported languages without fallback", {
    expect_snapshot(
      error = TRUE,
      resolve_handoff_target("missing", "python")
    )
    expect_snapshot(
      error = TRUE,
      resolve_handoff_target("marimo-notebook", "r")
    )
    expect_error(
      resolve_handoff_target("shiny-app", "javascript"),
      "language.*python.*r"
    )
  })
})

describe("resolve_handoff_type()", {
  it("combines format and target metadata", {
    type <- resolve_handoff_type("jupyter-notebook", "r")

    expect_identical(type@id, "jupyter-notebook")
    expect_identical(type@label, "Jupyter")
    expect_identical(type@icon, "file-earmark-code")
    expect_identical(type@language, "r")
    expect_identical(type@file_extension, ".ipynb")
    expect_identical(type@editor_language, "json")
    expect_identical(type@structure, "notebook-json")
  })

  it("uses explicit registries", {
    registry <- list(custom = new_test_handoff_format(id = "custom"))

    type <- resolve_handoff_type("custom", "python", registry)

    expect_identical(type@label, "Quarto")
    expect_identical(type@file_extension, ".qmd")
  })
})

describe("parse_handoff_generate_request()", {
  it("uses defaults only for absent and non-list payloads", {
    absent <- parse_handoff_generate_request(NULL, "quarto-dashboard")
    scalar <- parse_handoff_generate_request("bad payload", "shiny-app")
    number <- parse_handoff_generate_request(1, "marimo-notebook")

    expect_identical(absent@type_id, "quarto-dashboard")
    expect_identical(absent@selected_ids, character())
    expect_identical(scalar@type_id, "shiny-app")
    expect_identical(number@type_id, "marimo-notebook")
  })

  it("normalizes valid and missing fields", {
    request <- parse_handoff_generate_request(
      list(
        selected_ids = c("viz-1", "query-2"),
        type = "shiny-app",
        language = "r",
        freeform = "  R Markdown report  "
      ),
      "quarto-dashboard"
    )
    missing <- parse_handoff_generate_request(
      list(
        selected_ids = NULL,
        type = NULL,
        language = NULL,
        freeform = NULL
      ),
      "jupyter-notebook"
    )

    expect_identical(request@selected_ids, c("viz-1", "query-2"))
    expect_identical(request@type_id, "shiny-app")
    expect_identical(request@language, "r")
    expect_identical(request@freeform, "R Markdown report")
    expect_identical(missing@selected_ids, character())
    expect_identical(missing@type_id, "jupyter-notebook")
    expect_identical(missing@language, "")
    expect_identical(missing@freeform, "")
  })

  it("flattens browser JSON's list-shaped selected_ids", {
    # Shiny's browser JSON deserialization keeps array-valued custom-message
    # fields as plain lists of scalars, never atomic vectors, regardless of
    # array length.
    single <- parse_handoff_generate_request(
      list(
        selected_ids = list("query-0"),
        type = "quarto-dashboard",
        language = "r",
        freeform = ""
      ),
      "quarto-dashboard"
    )
    multiple <- parse_handoff_generate_request(
      list(
        selected_ids = list("viz-1", "query-2"),
        type = "quarto-dashboard",
        language = "r",
        freeform = ""
      ),
      "quarto-dashboard"
    )
    empty <- parse_handoff_generate_request(
      list(
        selected_ids = list(),
        type = "quarto-dashboard",
        language = "r",
        freeform = ""
      ),
      "quarto-dashboard"
    )

    expect_identical(single@selected_ids, "query-0")
    expect_identical(multiple@selected_ids, c("viz-1", "query-2"))
    expect_identical(empty@selected_ids, character())
  })

  it("rejects data frames with a representative diagnostic", {
    expect_snapshot(
      error = TRUE,
      parse_handoff_generate_request(
        data.frame(type = "shiny-app"),
        "quarto-dashboard"
      )
    )
  })

  it("rejects malformed named-list payloads", {
    cases <- list(
      extra = list(
        list(type = "shiny-app", extra = TRUE),
        "unexpected field"
      ),
      unnamed = list(list("shiny-app"), "field names"),
      selected_type = list(
        list(selected_ids = list(1, 2)),
        "selected_ids"
      ),
      selected_missing = list(
        list(selected_ids = c("viz-1", NA_character_)),
        "selected_ids"
      ),
      type = list(
        list(type = c("shiny-app", "quarto-dashboard")),
        "type"
      ),
      language = list(list(language = 1), "language"),
      freeform = list(list(freeform = character()), "freeform")
    )

    for (case_name in names(cases)) {
      case <- cases[[case_name]]
      expect_error(
        parse_handoff_generate_request(case[[1]], "quarto-dashboard"),
        case[[2]],
        info = case_name
      )
    }
  })
})

describe("parse_handoff_recommendation()", {
  it("enforces runtime enums and deduplicates IDs in first order", {
    recommendation <- parse_handoff_recommendation(
      list(
        selected_ids = c("viz-2", "query-1", "viz-2"),
        format_id = "quarto-dashboard",
        directions = "Use a compact layout"
      ),
      allowed_item_ids = c("query-1", "viz-2"),
      allowed_format_ids = c("quarto-dashboard", "shiny-app")
    )

    expect_identical(recommendation@selected_ids, c("viz-2", "query-1"))
    expect_identical(recommendation@format_id, "quarto-dashboard")
    expect_identical(recommendation@directions, "Use a compact layout")
  })

  it("rejects data-frame payloads", {
    expect_error(
      parse_handoff_recommendation(
        data.frame(
          selected_ids = "viz-1",
          format_id = "quarto-dashboard"
        ),
        allowed_item_ids = "viz-1",
        allowed_format_ids = "quarto-dashboard"
      ),
      "must not be a data frame"
    )
  })

  it("defaults directions", {
    recommendation <- parse_handoff_recommendation(
      list(selected_ids = "viz-1", format_id = "shiny-app"),
      allowed_item_ids = "viz-1",
      allowed_format_ids = "shiny-app"
    )

    expect_identical(recommendation@directions, "")
  })

  it("rejects unsupported IDs with a representative diagnostic", {
    expect_snapshot(error = TRUE, {
      parse_handoff_recommendation(
        list(selected_ids = "missing", format_id = "quarto-dashboard"),
        allowed_item_ids = "viz-1",
        allowed_format_ids = "quarto-dashboard"
      )
    })
  })

  it("rejects malformed fields and formats", {
    cases <- list(
      missing = list(
        list(selected_ids = "viz-1"),
        "missing required field"
      ),
      selected_type = list(
        list(
          selected_ids = list("viz-1"),
          format_id = "quarto-dashboard"
        ),
        "selected_ids"
      ),
      format_shape = list(
        list(
          selected_ids = "viz-1",
          format_id = c("quarto-dashboard", "shiny-app")
        ),
        "format_id"
      ),
      format_enum = list(
        list(selected_ids = "viz-1", format_id = "missing"),
        "unsupported format ID"
      ),
      null_directions = list(
        list(
          selected_ids = "viz-1",
          format_id = "quarto-dashboard",
          directions = NULL
        ),
        "directions"
      ),
      extra = list(
        list(
          selected_ids = "viz-1",
          format_id = "quarto-dashboard",
          extra = "value"
        ),
        "unexpected field"
      )
    )

    for (case_name in names(cases)) {
      case <- cases[[case_name]]
      expect_error(
        parse_handoff_recommendation(
          case[[1]],
          allowed_item_ids = "viz-1",
          allowed_format_ids = c("quarto-dashboard", "shiny-app")
        ),
        case[[2]],
        info = case_name
      )
    }
  })
})

describe("parse_handoff_result()", {
  it("defaults metadata and preserves referenced-table order", {
    result <- parse_handoff_result(
      list(
        source = "print('ok')",
        language = "python",
        referenced_tables = c("orders", "customers", "orders")
      ),
      allowed_table_names = c("customers", "orders"),
      allowed_languages = c("python", "r")
    )

    expect_identical(result@summary, "")
    expect_identical(result@install_instructions, "")
    expect_identical(result@run_instructions, "")
    expect_identical(
      result@referenced_tables,
      c("orders", "customers", "orders")
    )
  })

  it("rejects data-frame payloads", {
    expect_error(
      parse_handoff_result(
        data.frame(
          source = "print('ok')",
          language = "python",
          referenced_tables = "orders"
        ),
        allowed_table_names = "orders",
        allowed_languages = "python"
      ),
      "must not be a data frame"
    )
  })

  it("preserves complete valid metadata", {
    result <- parse_handoff_result(
      list(
        source = "library(shiny)",
        language = "r",
        summary = "A dashboard",
        install_instructions = "Install shiny.",
        run_instructions = "Run the app.",
        referenced_tables = "sales"
      ),
      allowed_table_names = "sales",
      allowed_languages = "r"
    )

    expect_identical(result@language, "r")
    expect_identical(result@summary, "A dashboard")
    expect_identical(result@install_instructions, "Install shiny.")
    expect_identical(result@run_instructions, "Run the app.")
  })

  it("rejects unsupported tables with a representative diagnostic", {
    expect_snapshot(error = TRUE, {
      parse_handoff_result(
        list(
          source = "x",
          language = "python",
          referenced_tables = "payments"
        ),
        allowed_table_names = "orders",
        allowed_languages = "python"
      )
    })
  })

  it("rejects malformed metadata and runtime languages", {
    cases <- list(
      missing = list(
        list(language = "python", referenced_tables = character()),
        "missing required field"
      ),
      extra = list(
        list(
          source = "x",
          language = "python",
          referenced_tables = character(),
          extra = TRUE
        ),
        "unexpected field"
      ),
      source = list(
        list(
          source = c("x", "y"),
          language = "python",
          referenced_tables = character()
        ),
        "source"
      ),
      language_shape = list(
        list(
          source = "x",
          language = character(),
          referenced_tables = character()
        ),
        "language"
      ),
      language_enum = list(
        list(source = "x", language = "r", referenced_tables = character()),
        "unsupported language"
      ),
      summary = list(
        list(
          source = "x",
          language = "python",
          summary = NULL,
          referenced_tables = character()
        ),
        "summary"
      ),
      install = list(
        list(
          source = "x",
          language = "python",
          install_instructions = character(),
          referenced_tables = character()
        ),
        "install_instructions"
      ),
      run = list(
        list(
          source = "x",
          language = "python",
          run_instructions = NA_character_,
          referenced_tables = character()
        ),
        "run_instructions"
      ),
      tables = list(
        list(
          source = "x",
          language = "python",
          referenced_tables = list("orders")
        ),
        "referenced_tables"
      )
    )

    for (case_name in names(cases)) {
      case <- cases[[case_name]]
      expect_error(
        parse_handoff_result(
          case[[1]],
          allowed_table_names = "orders",
          allowed_languages = "python"
        ),
        case[[2]],
        info = case_name
      )
    }
  })
})

describe("parse_handoff_freeform_metadata()", {
  it("normalizes safe extensions and preserves editor metadata", {
    missing_dot <- parse_handoff_freeform_metadata(
      list(file_extension = "py", editor_language = "python")
    )
    existing_dot <- parse_handoff_freeform_metadata(
      list(file_extension = ".Rmd", editor_language = "markdown")
    )

    expect_identical(
      missing_dot,
      list(file_extension = ".py", editor_language = "python")
    )
    expect_identical(
      existing_dot,
      list(file_extension = ".Rmd", editor_language = "markdown")
    )
  })

  it("rejects data-frame payloads", {
    expect_error(
      parse_handoff_freeform_metadata(
        data.frame(
          file_extension = ".py",
          editor_language = "python"
        )
      ),
      "must not be a data frame"
    )
  })

  it("rejects an unsafe extension with a representative diagnostic", {
    expect_snapshot(
      error = TRUE,
      parse_handoff_freeform_metadata(
        list(
          file_extension = "../handoff.py",
          editor_language = "python"
        )
      )
    )
  })

  it("rejects missing, unexpected, and malformed fields", {
    cases <- list(
      slash = list(
        list(
          file_extension = "unsafe/handoff.py",
          editor_language = "python"
        ),
        "safe file extension"
      ),
      backslash = list(
        list(
          file_extension = "..\\handoff.py",
          editor_language = "python"
        ),
        "safe file extension"
      ),
      control = list(
        list(file_extension = ".py\n", editor_language = "python"),
        "safe file extension"
      ),
      missing = list(
        list(file_extension = ".py"),
        "missing required field"
      ),
      extra = list(
        list(
          file_extension = ".py",
          editor_language = "python",
          extra = TRUE
        ),
        "unexpected field"
      ),
      extension_shape = list(
        list(
          file_extension = c(".py", ".R"),
          editor_language = "python"
        ),
        "file_extension"
      )
    )

    for (case_name in names(cases)) {
      case <- cases[[case_name]]
      expect_error(
        parse_handoff_freeform_metadata(case[[1]]),
        case[[2]],
        info = case_name
      )
    }

    expect_snapshot(error = TRUE, {
      parse_handoff_freeform_metadata(
        list(
          file_extension = ".py",
          editor_language = ""
        )
      )
    })
  })
})
