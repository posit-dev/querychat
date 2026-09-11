new_notebook_json <- function(kernel_language = "R") {
  sprintf(
    paste0(
      '{"cells": [{"cell_type": "code", "source": "1 + 1", "metadata": {}}],',
      ' "metadata": {"kernelspec": {"language": %s}},',
      ' "nbformat": 4, "nbformat_minor": 5}'
    ),
    jsonlite::toJSON(kernel_language, auto_unbox = TRUE)
  )
}

describe("validate_handoff_source()", {
  it("accepts nonempty source for text targets", {
    text_type <- resolve_handoff_type("shiny-app", "python")

    expect_invisible(
      validate_handoff_source(
        long_enough_source("print('ok')"),
        text_type,
        "unrelated system prompt"
      )
    )
  })

  it("accepts valid notebook JSON with a matching kernelspec", {
    r_type <- resolve_handoff_type("jupyter-notebook", "r")
    python_type <- resolve_handoff_type("jupyter-notebook", "python")

    expect_invisible(
      validate_handoff_source(new_notebook_json("R"), r_type, "sys")
    )
    expect_invisible(
      validate_handoff_source(new_notebook_json("python"), python_type, "sys")
    )
    # Kernel language matching is case-insensitive.
    expect_invisible(
      validate_handoff_source(new_notebook_json("r"), r_type, "sys")
    )
  })

  it("rejects notebook targets that are not valid notebook JSON", {
    notebook_type <- resolve_handoff_type("jupyter-notebook", "r")
    invalid_sources <- list(
      "not notebook JSON",
      "[1, 2]",
      '{"cells": []}',
      '{"cells": [], "metadata": {}, "nbformat": "4"}'
    )

    for (source in invalid_sources) {
      expect_error(
        validate_handoff_source(source, notebook_type, "sys"),
        "not valid notebook JSON",
        info = source
      )
    }
  })

  it("rejects notebooks with a missing or mismatched kernelspec", {
    r_type <- resolve_handoff_type("jupyter-notebook", "r")
    python_type <- resolve_handoff_type("jupyter-notebook", "python")
    no_kernelspec <- paste0(
      '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}'
    )

    expect_error(
      validate_handoff_source(no_kernelspec, r_type, "sys"),
      "must declare a R kernelspec"
    )
    expect_error(
      validate_handoff_source(new_notebook_json("R"), python_type, "sys"),
      "must declare a Python kernelspec, not R"
    )
  })

  it("rejects non-scalar, non-character, and blank source consistently", {
    type <- resolve_handoff_type("jupyter-notebook", "python")
    invalid_sources <- list(NULL, 1, c("one", "two"), " \n\t")
    messages <- vapply(
      invalid_sources,
      function(source) {
        tryCatch(
          validate_handoff_source(source, type, "sys"),
          error = conditionMessage
        )
      },
      character(1)
    )

    expect_identical(
      unique(messages),
      "Generated handoff source must be a non-empty string."
    )
    expect_snapshot(
      error = TRUE,
      validate_handoff_source(" \n\t", type, "sys")
    )
  })

  it("requires a resolved handoff type", {
    expect_snapshot(
      error = TRUE,
      validate_handoff_source("source", "not a handoff type", "sys")
    )
  })

  it("rejects a source shorter than the minimum-substance floor", {
    text_type <- resolve_handoff_type("quarto-dashboard", "r")

    expect_error(
      validate_handoff_source("penguins-handoff.qmd", text_type, "sys"),
      "too short"
    )
  })

  it("rejects a source that echoes the system prompt", {
    text_type <- resolve_handoff_type("quarto-dashboard", "r")
    system_prompt <- paste(
      "You are an expert data analyst and developer. Your task is to turn",
      "the work a user did during a data-exploration session into a",
      "standalone, reusable handoff they can run, share, and build on",
      "outside the chat."
    )
    echoed_source <- paste0(system_prompt, "\n\n", strrep("more text ", 30))

    expect_error(
      validate_handoff_source(echoed_source, text_type, system_prompt),
      "echoes the system prompt"
    )
  })

  it("accepts a real, adequately long source that merely shares vocabulary with the prompt", {
    text_type <- resolve_handoff_type("quarto-dashboard", "r")
    system_prompt <- "You are an expert data analyst and developer."

    expect_invisible(
      validate_handoff_source(
        long_enough_source(
          "---\ntitle: Penguins dashboard\n---\n\n```{r}\nlibrary(ggplot2)\n```"
        ),
        text_type,
        system_prompt
      )
    )
  })
})
