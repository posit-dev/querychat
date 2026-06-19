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

test_that("mod_server() return includes table() and table_names() for single-table", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  client_factory <- function(...) structure(list(), class = "MockChat")

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      enable_bookmarking = FALSE
    ),
    {
      # table_names_fn() returns the table name vector
      expect_equal(table_names_fn(), "test_table")

      # table_fn() returns a TableAccessor backed by reactive state
      acc <- table_fn("test_table")
      expect_true(inherits(acc, "TableAccessor"))
      expect_equal(acc$table_name, "test_table")

      # TableAccessor$df() works (returns the full data frame when no filter set)
      df_result <- shiny::isolate(acc$df())
      expect_equal(nrow(df_result), 5L)

      # Single-table backward compat: first$df/sql/title are still in the return
      first_state <- tables[[1]]
      expect_true(is.function(first_state$df))
      expect_true(is.function(first_state$sql))
      expect_true(is.function(first_state$title))

      # Verify the returned list exposes table() and table_names()
      expect_true(is.function(session$returned$table))
      expect_true(is.function(session$returned$table_names))
      acc <- session$returned$table("test_table")
      expect_s3_class(acc, "TableAccessor")
      expect_equal(session$returned$table_names(), "test_table")

      # Verify backward-compat reactive accessors on the returned list
      expect_true(is.function(session$returned$df))
      expect_true(is.function(session$returned$sql))
      expect_true(is.function(session$returned$title))
    }
  )
})

test_that("mod_server() return includes table() and table_names() for multi-table", {
  skip_if_no_dataframe_engine()

  ds1 <- local_data_frame_source(new_test_df(), table_name = "tbl_a")
  ds2 <- local_data_frame_source(new_test_df(), table_name = "tbl_b")
  data_sources <- list(tbl_a = ds1, tbl_b = ds2)
  executor <- build_query_executor(data_sources)
  withr::defer(executor$cleanup())

  result <- NULL
  client_factory <- function(...) {
    result <<- "client_called"
    structure(list(), class = "MockChat")
  }

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = data_sources,
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      enable_bookmarking = FALSE
    ),
    {
      # table_names_fn() returns all registered table names
      expect_equal(table_names_fn(), c("tbl_a", "tbl_b"))

      # table_fn() returns a TableAccessor for each table
      acc_a <- table_fn("tbl_a")
      expect_true(inherits(acc_a, "TableAccessor"))
      expect_equal(acc_a$table_name, "tbl_a")

      acc_b <- table_fn("tbl_b")
      expect_true(inherits(acc_b, "TableAccessor"))
      expect_equal(acc_b$table_name, "tbl_b")

      # table_fn() errors for unknown names
      expect_error(table_fn("nonexistent"), class = "rlang_error")

      # Multi-table: single_table_error functions mention qc_vals$table()
      single_err <- single_table_error("sql")
      expect_error(single_err(), regexp = "qc_vals\\$table")

      # Verify the returned list exposes table() and table_names()
      expect_true(is.function(session$returned$table))
      expect_true(is.function(session$returned$table_names))
      acc <- session$returned$table("tbl_a")
      expect_s3_class(acc, "TableAccessor")
      expect_equal(sort(session$returned$table_names()), c("tbl_a", "tbl_b"))

      # Verify error is surfaced through the public API
      expect_error(session$returned$table("nonexistent"), "not found")
    }
  )
})

test_that("mod_server() passes visualize callback and tools to client factory", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())
  captured <- NULL

  client_factory <- function(...) {
    captured <<- list(...)
    structure(list(), class = "MockChat")
  }

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
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

test_that("mod_server() exposes current_table() starting as NULL", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  client_factory <- function(...) structure(list(), class = "MockChat")

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      enable_bookmarking = FALSE
    ),
    {
      expect_true(is.function(session$returned$current_table))
      expect_null(shiny::isolate(session$returned$current_table()))
    }
  )
})

test_that("mod_server() current_table() updates on update_dashboard and reset_query", {
  skip_if_no_dataframe_engine()

  ds1 <- local_data_frame_source(new_test_df(), table_name = "tbl_a")
  ds2 <- local_data_frame_source(new_test_df(), table_name = "tbl_b")
  data_sources <- list(tbl_a = ds1, tbl_b = ds2)
  executor <- build_query_executor(data_sources)
  withr::defer(executor$cleanup())

  captured_callbacks <- NULL
  client_factory <- function(...) {
    captured_callbacks <<- list(...)
    structure(list(), class = "MockChat")
  }

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = data_sources,
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      enable_bookmarking = FALSE
    ),
    {
      # Initially NULL
      expect_null(shiny::isolate(session$returned$current_table()))

      # update_dashboard sets it
      shiny::isolate(
        captured_callbacks$update_dashboard(
          query = "SELECT * FROM tbl_a",
          title = "All of tbl_a",
          table = "tbl_a"
        )
      )
      expect_equal(shiny::isolate(session$returned$current_table()), "tbl_a")

      # reset_dashboard also sets it
      shiny::isolate(captured_callbacks$reset_dashboard("tbl_b"))
      expect_equal(shiny::isolate(session$returned$current_table()), "tbl_b")
    }
  )
})

test_that("mod_ui() passes allow_attachments = TRUE to shinychat by default", {
  captured <- NULL
  local_mocked_bindings(
    chat_ui = function(...) {
      captured <<- list(...)
      htmltools::div()
    },
    .package = "shinychat"
  )
  mod_ui("test")
  expect_true(isTRUE(captured$allow_attachments))
})

test_that("mod_ui() passes allow_attachments = FALSE when requested", {
  captured <- NULL
  local_mocked_bindings(
    chat_ui = function(...) {
      captured <<- list(...)
      htmltools::div()
    },
    .package = "shinychat"
  )
  mod_ui("test", allow_attachments = FALSE)
  expect_false(isTRUE(captured$allow_attachments))
})

test_that("restored viz widgets survive a second bookmark cycle", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())
  callbacks <- NULL
  bookmark_fn <- NULL
  restore_fn <- NULL
  restored_args <- NULL

  client_factory <- function(...) {
    callbacks <<- list(...)
    structure(list(), class = "MockChat")
  }

  local_mocked_bindings(
    chat_restore = function(id, chat, ..., session) {},
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
    restore_viz_widgets = function(executor, saved_widgets, session) {
      restored_args <<- list(
        executor = executor,
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
      data_sources = list(test_table = ds),
      executor = executor,
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
      expect_true(inherits(restored_args$executor, "QueryExecutor"))
      expect_equal(restored_args$saved_widgets, saved)

      second_state <- new.env(parent = emptyenv())
      second_state$values <- list()
      shiny::isolate(bookmark_fn(second_state))
      expect_equal(second_state$values$querychat_viz_widgets, saved)
    }
  )
})
