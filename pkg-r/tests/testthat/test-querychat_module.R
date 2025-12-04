test_that("Shiny app example loads without errors", {
  skip_if_not_installed("DT")
  skip_if_not_installed("RSQLite")
  skip_if_not_installed("shinytest2")

  # Create a simplified test app with mocked ellmer
  test_app_dir <- withr::local_tempdir()
  test_app_file <- file.path(test_app_dir, "app.R")
  dir.create(dirname(test_app_file), showWarnings = FALSE)

  file.copy(test_path("apps/basic/app.R"), test_app_file)

  # Test that the app can be loaded without immediate errors
  expect_no_error({
    # Try to parse and evaluate the app code
    source(test_app_file, local = TRUE)
  })
})
