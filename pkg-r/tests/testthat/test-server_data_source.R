# QueryChat$server(data_source = ) registers a table for one session only.
# mod_server() is mocked so each test can inspect what a session received.

local_captured_mod_server <- function(env = parent.frame()) {
  calls <- new.env(parent = emptyenv())
  calls$args <- list()
  testthat::local_mocked_bindings(
    mod_server = function(id, ...) {
      calls$args[[length(calls$args) + 1L]] <- list(...)
      list()
    },
    .package = "querychat",
    .env = env
  )
  calls
}

# Runs qc$server(...) under an explicit MockShinySession and returns that
# session still open, so a test can hold several sessions at once and end
# each with session$close() (which fires onSessionEnded callbacks).
# shiny::testServer() is not used here because it closes its session on exit.
start_server_session <- function(qc, ..., env = parent.frame()) {
  args <- list(...)
  session <- shiny::MockShinySession$new()
  withr::defer(if (!session$isClosed()) session$close(), envir = env)
  shiny::withReactiveDomain(session, do.call(qc$server, args))
  session
}

source_conn_valid <- function(source) {
  DBI::dbIsValid(source$.__enclos_env__$private$conn)
}

describe("QueryChat$server(data_source = ) session isolation", {
  it("does not change the instance's tables", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(NULL, table_name = "users", greeting = "hi")
    withr::defer(qc$cleanup())

    start_server_session(qc, data_source = new_users_df())

    expect_equal(qc$table_names(), character())
    expect_equal(calls$args[[1]]$table_set$table_names(), "users")
  })

  it("gives each session its own source", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(NULL, table_name = "users", greeting = "hi")
    withr::defer(qc$cleanup())

    start_server_session(qc, data_source = new_users_df())
    start_server_session(qc, data_source = new_test_df())

    first <- calls$args[[1]]$table_set$data_sources$users
    second <- calls$args[[2]]$table_set$data_sources$users
    expect_false(identical(first, second))
    expect_equal(names(first$get_data()), c("id", "name", "age"))
    expect_equal(names(second$get_data()), c("id", "name", "value"))
  })

  it("shadows a same-named instance table for that session only", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(new_users_df(), "users", greeting = "hi")
    withr::defer(qc$cleanup())
    config_source <- qc_data_source(qc, "users")

    start_server_session(qc, data_source = new_test_df())

    expect_identical(qc_data_source(qc, "users"), config_source)
    session_source <- calls$args[[1]]$table_set$data_sources$users
    expect_false(identical(session_source, config_source))
    expect_equal(names(session_source$get_data()), c("id", "name", "value"))
  })

  it("keeps sessions from seeing each other's tables", {
    skip_if_not_installed("duckdb")
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(NULL, greeting = "hi")
    qc$add_table(new_users_df(), "orders")
    withr::defer(qc$cleanup())

    start_server_session(
      qc,
      data_source = new_test_df(),
      table_name = "returns"
    )
    start_server_session(
      qc,
      data_source = new_metrics_df(),
      table_name = "orders"
    )

    expect_equal(
      calls$args[[1]]$table_set$table_names(),
      c("orders", "returns")
    )
    expect_equal(calls$args[[2]]$table_set$table_names(), "orders")
  })

  it("snapshots greeting tables per session without touching the greeter", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(NULL, table_name = "users", greeting = "hi")
    withr::defer(qc$cleanup())

    start_server_session(qc, data_source = new_users_df())

    expect_equal(calls$args[[1]]$greeting_tables, "users")
    expect_equal(qc$greeter$tables, character())
  })

  it("passes the session's table set and description to the greeter factory", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(NULL, table_name = "users", greeting = "hi")
    withr::defer(qc$cleanup())
    start_server_session(qc, data_source = new_users_df())
    session_set <- calls$args[[1]]$table_set

    seen <- NULL
    qc$greeter$.__enclos_env__$private$.client_factory <- function(
      tables,
      prompt,
      base = NULL,
      table_set = NULL
    ) {
      seen <<- list(tables = tables, table_set = table_set)
      structure(list(), class = c("MockChat", "Chat"))
    }
    qc$greeter$build_client(tables = "users", table_set = session_set)

    expect_equal(seen$tables, "users")
    expect_identical(seen$table_set, session_set)
  })
})

describe("QueryChat$server(data_source = ) session cleanup", {
  it("closes the session's own source and executor when the session ends", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(NULL, table_name = "users", greeting = "hi")
    withr::defer(qc$cleanup())

    session <- start_server_session(qc, data_source = new_users_df())
    session_set <- calls$args[[1]]$table_set
    session_source <- session_set$data_sources$users
    session_set$executor()
    expect_true(source_conn_valid(session_source))

    session$close()

    expect_false(source_conn_valid(session_source))
  })

  it("does not close another session's source", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    qc <- QueryChat$new(NULL, table_name = "users", greeting = "hi")
    withr::defer(qc$cleanup())

    session_a <- start_server_session(qc, data_source = new_users_df())
    session_b <- start_server_session(qc, data_source = new_test_df())
    source_a <- calls$args[[1]]$table_set$data_sources$users
    source_b <- calls$args[[2]]$table_set$data_sources$users

    session_b$close()
    expect_false(source_conn_valid(source_b))
    expect_true(source_conn_valid(source_a))

    session_a$close()
    expect_false(source_conn_valid(source_a))
  })

  it("leaves the instance's config-time source open until $cleanup()", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    local_captured_mod_server()
    qc <- QueryChat$new(new_users_df(), "users", greeting = "hi")
    config_source <- qc_data_source(qc, "users")

    session <- start_server_session(qc, data_source = new_test_df())
    session$close()
    expect_true(source_conn_valid(config_source))

    qc$cleanup()
    expect_false(source_conn_valid(config_source))
  })

  it("owns nothing when no data_source is passed", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    local_captured_mod_server()
    qc <- QueryChat$new(new_users_df(), "users", greeting = "hi")
    withr::defer(qc$cleanup())
    config_source <- qc_data_source(qc, "users")

    session <- start_server_session(qc)
    session$close()

    expect_true(source_conn_valid(config_source))
  })

  it("does not close a caller-supplied DataSource when the session ends", {
    skip_if_no_dataframe_engine()
    withr::local_envvar(OPENAI_API_KEY = "boop")
    local_captured_mod_server()
    qc <- QueryChat$new(NULL, table_name = "users", greeting = "hi")
    withr::defer(qc$cleanup())
    caller_source <- local_data_frame_source(new_users_df(), "users")

    session <- start_server_session(qc, data_source = caller_source)
    session$close()

    expect_true(source_conn_valid(caller_source))
  })

  it("leaves the instance untouched when registration fails", {
    skip_if_no_dataframe_engine()
    skip_if_not_installed("RSQLite")
    withr::local_envvar(OPENAI_API_KEY = "boop")
    calls <- local_captured_mod_server()
    db <- local_sqlite_connection(table_name = "other")
    qc <- QueryChat$new(new_users_df(), "users", greeting = "hi")
    withr::defer(qc$cleanup())

    expect_error(
      start_server_session(qc, data_source = db$conn, table_name = "other"),
      "same type"
    )

    expect_equal(qc$table_names(), "users")
    start_server_session(qc)
    expect_equal(
      calls$args[[length(calls$args)]]$table_set$table_names(),
      "users"
    )
  })
})
