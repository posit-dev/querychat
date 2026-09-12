# Tests for QueryChat$server(data_source = ) surviving a second Shiny
# session without corrupting an earlier, still-running session's resources
# or greeting (posit-dev/querychat#300).

# Any non-NULL value satisfies $server()'s `is.null(session)` guard; the
# value itself is never otherwise used (it isn't threaded into mod_server()).
fake_shiny_session <- function() structure(list(), class = "ShinySession")

# R6 instances lock existing method bindings, so spying on $cleanup()
# requires unlocking it first.
spy_on_cleanup <- function(obj) {
  called <- FALSE
  unlockBinding("cleanup", obj)
  obj$cleanup <- function() called <<- TRUE
  function() called
}

# Mock mod_server() to capture its call kwargs instead of actually building a
# Shiny module, and return a list() so $server() has something to return.
local_captured_mod_server <- function(env = parent.frame()) {
  calls <- new.env(parent = emptyenv())
  calls$args <- list()

  testthat::local_mocked_bindings(
    mod_server = function(...) {
      calls$args[[length(calls$args) + 1L]] <- list(...)
      list()
    },
    .package = "querychat",
    .env = env
  )
  calls
}

describe("QueryChat$server(data_source=) survives a second session", {
  it("a second session's call does not raise", {
    skip_if_no_dataframe_engine()
    calls <- local_captured_mod_server()

    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    withr::defer(qc$cleanup())

    qc$server(data_source = new_users_df(), session = fake_shiny_session())
    expect_no_error(
      qc$server(data_source = new_users_df(), session = fake_shiny_session())
    )

    expect_equal(names(calls$args[[2]]$data_sources), "users")
  })

  it("the public $add_table() guard is still enforced", {
    skip_if_no_dataframe_engine()
    local_captured_mod_server()

    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    withr::defer(qc$cleanup())

    qc$server(data_source = new_users_df(), session = fake_shiny_session())

    expect_error(
      qc$add_table(new_users_df(), "other"),
      "Cannot add tables after server initialization"
    )
  })
})

describe("QueryChat$server(data_source=) cleanup safety", {
  it("a second session's call does not clean up the first session's source", {
    skip_if_no_dataframe_engine()
    local_captured_mod_server()

    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    withr::defer(qc$cleanup())

    qc$server(data_source = new_users_df(), session = fake_shiny_session())
    first_source <- qc_data_source(qc, "users")
    cleaned_up <- spy_on_cleanup(first_source)

    qc$server(data_source = new_users_df(), session = fake_shiny_session())

    expect_false(cleaned_up())
  })

  it("the public add_table(replace=TRUE) still cleans up the old source", {
    skip_if_no_dataframe_engine()

    qc <- QueryChat$new(new_users_df(), "users", greeting = "Test")
    withr::defer(qc$cleanup())

    first_source <- qc_data_source(qc, "users")
    cleaned_up <- spy_on_cleanup(first_source)

    qc$add_table(new_users_df(), "users", replace = TRUE)

    expect_true(cleaned_up())
  })

  it("a second session's call does not clean up the first session's query executor", {
    skip_if_no_dataframe_engine()
    local_captured_mod_server()

    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    withr::defer(qc$cleanup())

    qc$server(data_source = new_users_df(), session = fake_shiny_session())
    first_executor <- qc$.__enclos_env__$private$.query_executor
    cleaned_up <- spy_on_cleanup(first_executor)

    qc$server(data_source = new_users_df(), session = fake_shiny_session())

    expect_false(cleaned_up())
  })

  it("the public add_table(replace=TRUE) still cleans up the old query executor", {
    skip_if_no_dataframe_engine()

    qc <- QueryChat$new(new_users_df(), "users", greeting = "Test")
    withr::defer(qc$cleanup())

    # Force the executor to be built, mirroring a session that's already
    # queried through it before a config-time replace happens.
    qc$.__enclos_env__$private$.query_executor <- build_query_executor(
      qc$.__enclos_env__$private$.data_sources
    )
    first_executor <- qc$.__enclos_env__$private$.query_executor
    cleaned_up <- spy_on_cleanup(first_executor)

    qc$add_table(new_users_df(), "users", replace = TRUE)

    expect_true(cleaned_up())
  })
})

describe("QueryChat$server(data_source=) greeting snapshot", {
  it("passes a greeting_tables snapshot to mod_server", {
    skip_if_no_dataframe_engine()
    calls <- local_captured_mod_server()

    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    withr::defer(qc$cleanup())

    qc$server(data_source = new_users_df(), session = fake_shiny_session())

    expect_equal(calls$args[[1]]$greeting_tables, "users")
  })

  it("per-session registration does not duplicate greeter$tables", {
    skip_if_no_dataframe_engine()
    calls <- local_captured_mod_server()

    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    withr::defer(qc$cleanup())

    qc$server(data_source = new_users_df(), session = fake_shiny_session())
    qc$server(data_source = new_users_df(), session = fake_shiny_session())

    expect_equal(qc$greeter$tables, "users")
    expect_equal(calls$args[[2]]$greeting_tables, "users")
  })
})

describe("Mixing config-time $add_table() with $server(data_source=)", {
  it("server(data_source=) without a name replaces the config-time table", {
    skip_if_no_dataframe_engine()
    calls <- local_captured_mod_server()

    qc <- QueryChat$new(NULL, greeting = "Test")
    withr::defer(qc$cleanup())

    config_df <- data.frame(id = 1:3)
    session_df <- data.frame(id = 4:6)
    qc$add_table(config_df, "orders")

    qc$server(data_source = session_df, session = fake_shiny_session())

    # Same table name, but the session's data replaces the config-time data
    expect_equal(names(calls$args[[1]]$data_sources), "orders")
    expect_equal(calls$args[[1]]$data_sources$orders$get_data()$id, 4:6)
  })

  it("replacing a config-time table does not clean it up", {
    skip_if_no_dataframe_engine()
    local_captured_mod_server()

    qc <- QueryChat$new(NULL, greeting = "Test")
    withr::defer(qc$cleanup())

    qc$add_table(new_users_df(), "orders")
    config_source <- qc_data_source(qc, "orders")
    cleaned_up <- spy_on_cleanup(config_source)

    qc$server(data_source = new_users_df(), session = fake_shiny_session())

    # Consistent with per-session replacement: the replaced source's cleanup
    # is left to whoever created it
    expect_false(cleaned_up())
  })

  it("server(data_source=, table_name=) adds a second table alongside the config-time one", {
    skip_if_no_dataframe_engine()
    calls <- local_captured_mod_server()

    qc <- QueryChat$new(NULL, greeting = "Test")
    withr::defer(qc$cleanup())

    config_df <- data.frame(id = 1:3)
    session_df <- data.frame(id = 4:6)
    qc$add_table(config_df, "orders")

    qc$server(
      data_source = session_df,
      table_name = "returns",
      session = fake_shiny_session()
    )

    expect_equal(names(calls$args[[1]]$data_sources), c("orders", "returns"))
    # The config-time table's own data is untouched
    expect_equal(calls$args[[1]]$data_sources$orders$get_data()$id, 1:3)
    expect_equal(calls$args[[1]]$data_sources$returns$get_data()$id, 4:6)
  })

  it("registration state is shared: a later session's snapshot includes an earlier session's differently-named table", {
    skip_if_no_dataframe_engine()
    calls <- local_captured_mod_server()

    qc <- QueryChat$new(NULL, greeting = "Test")
    withr::defer(qc$cleanup())

    qc$add_table(data.frame(id = 1:3), "orders")

    # Session 1 adds its own table alongside the config-time one
    qc$server(
      data_source = data.frame(id = 4:6),
      table_name = "returns",
      session = fake_shiny_session()
    )
    # Session 2 replaces "orders" only -- but still sees session 1's table,
    # since the registry is shared and cumulative across sessions
    qc$server(
      data_source = data.frame(id = 7:9),
      table_name = "orders",
      session = fake_shiny_session()
    )

    expect_equal(names(calls$args[[2]]$data_sources), c("orders", "returns"))
    expect_equal(calls$args[[2]]$data_sources$orders$get_data()$id, 7:9)
    expect_equal(calls$args[[2]]$data_sources$returns$get_data()$id, 4:6)
  })
})
