test_that("packaged handoff-formats.yml matches the canonical shared copy", {
  canonical <- test_path("..", "..", "..", "shared", "handoff-formats.yml")
  skip_if_not(
    file.exists(canonical),
    "shared/handoff-formats.yml only exists in the source repo"
  )

  packaged <- test_path("..", "..", "inst", "handoff-formats.yml")

  expect_identical(
    readBin(packaged, "raw", file.size(packaged)),
    readBin(canonical, "raw", file.size(canonical))
  )
})
