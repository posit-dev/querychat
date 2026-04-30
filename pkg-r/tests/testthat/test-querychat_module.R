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

test_that("mod_server() passes visualize callback and tools to client factory", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  captured <- NULL

  client_factory <- function(...) {
    captured <<- list(...)
    structure(list(), class = "MockChat")
  }

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_source = ds,
      greeting = "Hello",
      client = client_factory,
      tools = c("query", "visualize"),
      enable_bookmarking = FALSE
    ),
    {
      expect_type(captured, "list")
      expect_equal(captured$tools, c("query", "visualize"))
      expect_true(is.function(captured$visualize))
      expect_true(is.function(captured$update_dashboard))
      expect_true(is.function(captured$reset_dashboard))
    }
  )
})

test_that("restored viz widgets survive a second bookmark cycle", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  callbacks <- NULL
  bookmark_fn <- NULL
  restore_fn <- NULL
  restored_args <- NULL

  client_factory <- function(...) {
    callbacks <<- list(...)
    structure(list(), class = "MockChat")
  }

  local_mocked_bindings(
    chat_restore = function(id, chat, session) {},
    .package = "shinychat"
  )
  local_mocked_bindings(
    onBookmark = function(fun) {
      bookmark_fn <<- fun
    },
    onRestore = function(fun) {
      restore_fn <<- fun
    },
    .package = "shiny"
  )
  local_mocked_bindings(
    restore_viz_widgets = function(data_source, saved_widgets, session) {
      restored_args <<- list(
        data_source = data_source,
        saved_widgets = saved_widgets,
        session = session
      )
      saved_widgets
    },
    .package = "querychat"
  )

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_source = ds,
      greeting = "Hello",
      client = client_factory,
      tools = c("query", "visualize"),
      enable_bookmarking = TRUE
    ),
    {
      expect_true(is.function(bookmark_fn))
      expect_true(is.function(restore_fn))
      expect_true(is.function(callbacks$visualize))

      saved <- list(
        list(
          widget_id = "querychat_viz_1",
          ggsql = "SELECT 1 VISUALISE 1 AS x DRAW point"
        )
      )

      shiny::isolate(callbacks$visualize(saved[[1]]))

      first_state <- new.env(parent = emptyenv())
      first_state$values <- list()
      shiny::isolate(bookmark_fn(first_state))
      expect_equal(first_state$values$querychat_viz_widgets, saved)

      restore_state <- new.env(parent = emptyenv())
      restore_state$values <- first_state$values
      shiny::isolate(restore_fn(restore_state))
      expect_identical(restored_args$data_source, ds)
      expect_equal(restored_args$saved_widgets, saved)

      second_state <- new.env(parent = emptyenv())
      second_state$values <- list()
      shiny::isolate(bookmark_fn(second_state))
      expect_equal(second_state$values$querychat_viz_widgets, saved)
    }
  )
})
