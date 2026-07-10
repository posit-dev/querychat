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

  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
    ),
    {
      # Verify the returned list exposes table() and table_names()
      expect_true(is.function(session$returned$table))
      expect_true(is.function(session$returned$table_names))
      expect_equal(session$returned$table_names(), "test_table")

      # table() returns a TableAccessor backed by reactive state
      acc <- session$returned$table("test_table")
      expect_s3_class(acc, "TableAccessor")
      expect_equal(acc$table_name, "test_table")

      # TableAccessor$df() works (returns the full data frame when no filter set)
      df_result <- shiny::isolate(acc$df())
      expect_equal(nrow(df_result), 5L)

      # Single-table backward compat: first$df/sql/title are still in the return
      first_state <- session$returned$.tables[[1]]
      expect_true(is.function(first_state$df))
      expect_true(is.function(first_state$sql))
      expect_true(is.function(first_state$title))

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
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = data_sources,
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
    ),
    {
      # Verify the returned list exposes table() and table_names()
      expect_true(is.function(session$returned$table))
      expect_true(is.function(session$returned$table_names))
      expect_equal(sort(session$returned$table_names()), c("tbl_a", "tbl_b"))

      # table() returns a TableAccessor for each table
      acc_a <- session$returned$table("tbl_a")
      expect_s3_class(acc_a, "TableAccessor")
      expect_equal(acc_a$table_name, "tbl_a")

      acc_b <- session$returned$table("tbl_b")
      expect_s3_class(acc_b, "TableAccessor")
      expect_equal(acc_b$table_name, "tbl_b")

      # table() errors for unknown names
      expect_error(session$returned$table("nonexistent"), "not found")

      # Multi-table: single_table_error functions mention qc_vals$table()
      expect_error(session$returned$sql(), regexp = "qc_vals\\$table")
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
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = c("query", "visualize"),
      history = TRUE
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

  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
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
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = data_sources,
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
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

test_that("mod_ui() does not force allow_attachments, deferring to chat_ui default", {
  captured <- NULL
  local_mocked_bindings(
    chat_ui = function(id, ...) {
      captured <<- list(...)
      htmltools::div()
    },
    .package = "shinychat"
  )
  mod_ui("test")
  expect_false("allow_attachments" %in% names(captured))
})

test_that("mod_ui() passes allow_attachments = FALSE when requested", {
  captured <- NULL
  local_mocked_bindings(
    chat_ui = function(id, ...) {
      captured <<- list(...)
      htmltools::div()
    },
    .package = "shinychat"
  )
  mod_ui("test", allow_attachments = FALSE)
  expect_false(isTRUE(captured$allow_attachments))
})

test_that("mod_ui() calls chat_ui with NS(id, 'chat')", {
  captured <- NULL
  local_mocked_bindings(
    chat_ui = function(id, ...) {
      captured <<- list(id = id, ...)
      htmltools::div()
    },
    .package = "shinychat"
  )
  mod_ui("mymod")
  expect_equal(captured$id, shiny::NS("mymod", "chat"))
})

test_that("mod_ui() passes enable_cancel through to chat_ui without warning", {
  captured <- NULL
  local_mocked_bindings(
    chat_ui = function(id, ...) {
      captured <<- list(...)
      htmltools::div()
    },
    .package = "shinychat"
  )
  expect_no_warning(mod_ui("test", enable_cancel = FALSE))
  expect_false(isTRUE(captured$enable_cancel))
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
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    .package = "shinychat"
  )
  local_mock_chat_restore()
  local_mocked_bindings(
    onBookmark = function(fun, session = NULL) {
      bookmark_fn <<- fun
    },
    onRestore = function(fun, session = NULL) {
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
      history = TRUE
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

test_that("mod_server() calls chat_server('chat', ...) with the pre-built client", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  captured_chat_args <- NULL
  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) {
      captured_chat_args <<- list(id = id, client = client)
      mock_chat_server_result(client)
    },
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
    ),
    {
      expect_equal(captured_chat_args$id, "chat")
      expect_true(inherits(captured_chat_args$client, "Chat"))
    }
  )
})

test_that("mod_server() calls chat_restore() with the auto-bookmark trigger disabled when history isn't bookmark mode", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  captured_restore_args <- NULL
  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    chat_restore = function(id, client, ...) {
      captured_restore_args <<- list(id = id, client = client, ...)
      invisible(NULL)
    },
    .package = "shinychat"
  )

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
    ),
    {
      expect_equal(captured_restore_args$id, "chat")
      expect_true(inherits(captured_restore_args$client, "Chat"))
      expect_false(captured_restore_args$restore_ui)
      # The hooks are registered, but querychat never triggers a bookmark
      # itself -- that's left to `history` or the host app.
      expect_false(captured_restore_args$bookmark_on_input)
      expect_false(captured_restore_args$bookmark_on_response)
    }
  )
})

test_that("mod_server() skips chat_restore() when history is bookmark mode", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  chat_restore_called <- FALSE
  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    chat_restore = function(id, client, ...) {
      chat_restore_called <<- TRUE
      invisible(NULL)
    },
    .package = "shinychat"
  )

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = shinychat::history_options(restore_mode = "bookmark")
    ),
    {
      expect_false(chat_restore_called)
    }
  )
})

test_that("mod_server() builds the auto-generated greeting from the greeter, not the main client", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  main_client_calls <- list()
  client_factory <- function(...) {
    main_client_calls[[length(main_client_calls) + 1L]] <<- list(...)
    structure(list(), class = c("MockChat", "Chat"))
  }

  greeting_stream_prompt <- NULL
  fake_greeting_client <- list(
    stream_async = function(prompt) {
      greeting_stream_prompt <<- prompt
      "fake-stream"
    }
  )

  build_client_calls <- list()
  fake_greeter <- list(
    build_client = function(base = NULL) {
      build_client_calls[[length(build_client_calls) + 1L]] <<- base
      fake_greeting_client
    }
  )

  captured_greeting_arg <- NULL
  local_mocked_bindings(
    chat_server = function(id, client, greeting = NULL, ...) {
      captured_greeting_arg <<- greeting
      mock_chat_server_result(client)
    },
    chat_greeting = function(content, ...) content,
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = NULL,
      client = client_factory,
      tools = "query",
      greeter = fake_greeter,
      greeting_base = "base-client",
      history = TRUE
    ),
    {
      expect_true(is.function(captured_greeting_arg))
      suppressWarnings(captured_greeting_arg())

      # The greeting client must come from the greeter (configured with the
      # dedicated greeting prompt), not from a second call to the main client
      # factory with tools = NULL (which would use the query system prompt).
      expect_equal(length(build_client_calls), 1L)
      expect_equal(build_client_calls[[1]], "base-client")
      expect_equal(length(main_client_calls), 1L)
      expect_false(is.null(greeting_stream_prompt))
    }
  )
})

test_that("mod_server() chat_update input updates table state", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  local_mocked_bindings(
    chat_server = function(id, client, ...) mock_chat_server_result(client),
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
    ),
    {
      session$setInputs(
        chat_update = list(
          table = "test_table",
          query = "SELECT * FROM test_table WHERE cyl = 4",
          title = "4-cylinder cars"
        )
      )
      expect_equal(
        shiny::isolate(session$returned$sql()),
        "SELECT * FROM test_table WHERE cyl = 4"
      )
      expect_equal(
        shiny::isolate(session$returned$current_table()),
        "test_table"
      )
    }
  )
})

test_that("mod_server() registers table/viz state with both bookmark and history hooks, unconditionally", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  bookmark_save_count <- 0
  bookmark_restore_count <- 0
  history_save_fn <- NULL
  history_restore_fn <- NULL

  local_mocked_bindings(
    chat_server = function(id, client, ...) {
      list(
        client = client,
        history = list(
          on_save = function(fn) {
            history_save_fn <<- fn
            invisible(fn)
          },
          on_restore = function(fn) {
            history_restore_fn <<- fn
            invisible(fn)
          }
        )
      )
    },
    .package = "shinychat"
  )
  local_mock_chat_restore()
  local_mocked_bindings(
    onBookmark = function(fun, session = NULL) {
      bookmark_save_count <<- bookmark_save_count + 1
    },
    onRestore = function(fun, session = NULL) {
      bookmark_restore_count <<- bookmark_restore_count + 1
    },
    .package = "shiny"
  )

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = FALSE # even with history disabled, registration must still happen
    ),
    {
      expect_equal(bookmark_save_count, 1L)
      expect_equal(bookmark_restore_count, 1L)
      expect_true(is.function(history_save_fn))
      expect_true(is.function(history_restore_fn))
    }
  )
})

test_that("history on_save callback returns merged values (R history contract)", {
  skip_if_no_dataframe_engine()

  ds <- local_data_frame_source(new_test_df())
  executor <- build_query_executor(list(test_table = ds))
  withr::defer(executor$cleanup())

  client_factory <- function(...) {
    structure(list(), class = c("MockChat", "Chat"))
  }

  history_save_fn <- NULL
  local_mocked_bindings(
    chat_server = function(id, client, ...) {
      list(
        client = client,
        history = list(
          on_save = function(fn) {
            history_save_fn <<- fn
            invisible(fn)
          },
          on_restore = function(fn) invisible(fn)
        )
      )
    },
    .package = "shinychat"
  )
  local_mock_chat_restore()

  shiny::testServer(
    mod_server,
    args = list(
      id = "test",
      data_sources = list(test_table = ds),
      executor = executor,
      greeting = "Hello",
      client = client_factory,
      tools = "query",
      history = TRUE
    ),
    {
      session$setInputs(
        chat_update = list(
          table = "test_table",
          query = "SELECT * FROM test_table WHERE id = 1",
          title = "One row"
        )
      )
      result <- shiny::isolate(history_save_fn(list(unrelated_key = "kept")))
      expect_equal(result$unrelated_key, "kept")
      expect_equal(
        result$querychat_tables$test_table$sql,
        "SELECT * FROM test_table WHERE id = 1"
      )
    }
  )
})
