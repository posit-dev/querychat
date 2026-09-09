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

    expect_invisible(validate_handoff_source("print('ok')", text_type))
  })

  it("accepts valid notebook JSON with a matching kernelspec", {
    r_type <- resolve_handoff_type("jupyter-notebook", "r")
    python_type <- resolve_handoff_type("jupyter-notebook", "python")

    expect_invisible(validate_handoff_source(new_notebook_json("R"), r_type))
    expect_invisible(
      validate_handoff_source(new_notebook_json("python"), python_type)
    )
    # Kernel language matching is case-insensitive.
    expect_invisible(validate_handoff_source(new_notebook_json("r"), r_type))
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
        validate_handoff_source(source, notebook_type),
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
      validate_handoff_source(no_kernelspec, r_type),
      "must declare a R kernelspec"
    )
    expect_error(
      validate_handoff_source(new_notebook_json("R"), python_type),
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
          validate_handoff_source(source, type),
          error = conditionMessage
        )
      },
      character(1)
    )

    expect_identical(
      unique(messages),
      "Generated handoff source must be a non-empty string."
    )
    expect_snapshot(error = TRUE, validate_handoff_source(" \n\t", type))
  })

  it("requires a resolved handoff type", {
    expect_snapshot(
      error = TRUE,
      validate_handoff_source("source", "not a handoff type")
    )
  })
})
