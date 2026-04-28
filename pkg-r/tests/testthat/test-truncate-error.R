describe("truncate_error()", {
  it("returns short messages unchanged", {
    expect_equal(truncate_error("short error"), "short error")
  })

  it("handles empty string", {
    expect_equal(truncate_error(""), "")
  })

  it("truncates at blank line", {
    msg <- "Something went wrong\n\nHere is a very long schema dump that goes on and on"
    result <- truncate_error(msg)
    expect_equal(result, "Something went wrong\n\n(error truncated)")
  })

  it("truncates at schema dump markers", {
    msg <- "Validation failed\n{'additionalProperties': false}"
    result <- truncate_error(msg)
    expect_equal(result, "Validation failed\n\n(error truncated)")
  })

  it("applies hard cap on long single-line messages", {
    long_msg <- paste(rep("word", 200), collapse = " ")
    result <- truncate_error(long_msg, max_chars = 100)
    expect_true(nchar(result) <= 120)
    expect_match(result, "\\(error truncated\\)$")
  })

  it("cuts on word boundary for hard cap", {
    long_msg <- paste(rep("abcdefghij", 20), collapse = " ")
    result <- truncate_error(long_msg, max_chars = 50)
    expect_false(
      grepl("abcdefgh$", sub("\n\n\\(error truncated\\)$", "", result))
    )
  })

  it("respects custom max_chars", {
    msg <- paste(rep("word", 100), collapse = " ")
    result <- truncate_error(msg, max_chars = 20)
    body <- sub("\n\n\\(error truncated\\)$", "", result)
    expect_true(nchar(body) <= 20)
  })
})
