test_that("packaged handoff-formats.yml matches the canonical shared copy", {
  canonical <- test_path("..", "..", "..", "shared", "handoff-formats.yml")
  skip_if_not(
    file.exists(canonical),
    "shared/handoff-formats.yml only exists in the source repo"
  )

  # Resolve via system.file() so this works under R CMD check too, where
  # tests run from <pkg>.Rcheck/tests/ and inst/ has been installed away
  packaged <- system.file("handoff-formats.yml", package = "querychat")

  expect_identical(
    readBin(packaged, "raw", file.size(packaged)),
    readBin(canonical, "raw", file.size(canonical))
  )
})
