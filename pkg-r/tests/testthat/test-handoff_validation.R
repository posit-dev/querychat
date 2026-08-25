describe("validate_handoff_source()", {
  it("accepts nonempty source for text and notebook targets", {
    text_type <- resolve_handoff_type("shiny-app", "python")
    notebook_type <- resolve_handoff_type("jupyter-notebook", "r")

    expect_invisible(validate_handoff_source("print('ok')", text_type))
    expect_invisible(
      validate_handoff_source("not notebook JSON", notebook_type)
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
