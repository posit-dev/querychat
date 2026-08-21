# Test fixture constructors for data source tests

# Access the internal data source for a named table (test helper only)
qc_data_source <- function(qc, table_name) {
  qc$.__enclos_env__$private$.data_sources[[table_name]]
}

# Simple data frame with id, name, and value columns
new_test_df <- function(rows = 5) {
  data.frame(
    id = seq_len(rows),
    name = c("A", "B", "C", "D", "E")[seq_len(rows)],
    value = c(10, 20, 30, 40, 50)[seq_len(rows)],
    stringsAsFactors = FALSE
  )
}

# Data frame with multiple numeric columns for testing min/max ranges
new_metrics_df <- function() {
  data.frame(
    id = 1:5,
    score = c(10.5, 20.3, 15.7, 30.1, 25.9),
    count = c(100, 200, 150, 50, 75),
    stringsAsFactors = FALSE
  )
}

# Data frame with mixed types including boolean
new_mixed_types_df <- function() {
  data.frame(
    id = 1:5,
    name = c("A", "B", "C", "D", "E"),
    active = c(TRUE, FALSE, TRUE, TRUE, FALSE),
    stringsAsFactors = FALSE
  )
}

# Data frame for testing user data
new_users_df <- function() {
  data.frame(
    id = 1:5,
    name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
    age = c(25, 30, 35, 28, 32),
    stringsAsFactors = FALSE
  )
}

# Data frame with all data types for type testing
new_types_df <- function() {
  data.frame(
    id = 1:3,
    text_col = c("text1", "text2", "text3"),
    num_col = c(1.1, 2.2, 3.3),
    int_col = c(10L, 20L, 30L),
    bool_col = c(TRUE, FALSE, TRUE),
    stringsAsFactors = FALSE
  )
}

# Create a temporary SQLite connection with a test table
local_sqlite_connection <- function(
  data = new_test_df(),
  table_name = "test_table",
  env = parent.frame()
) {
  if (testthat::is_testing()) {
    skip_if_not_installed("RSQLite")
  }

  temp_db <- withr::local_tempfile(fileext = ".db", .local_envir = env)
  conn <- DBI::dbConnect(RSQLite::SQLite(), temp_db)
  withr::defer(DBI::dbDisconnect(conn), envir = env)

  DBI::dbWriteTable(conn, table_name, data, overwrite = TRUE)

  list(conn = conn, path = temp_db)
}

# Skip test if no DataFrameSource engine is available
skip_if_no_dataframe_engine <- function() {
  if (!rlang::is_installed("duckdb") && !rlang::is_installed("RSQLite")) {
    skip("Neither duckdb nor RSQLite is installed")
  }
}

# Create a DataFrameSource with automatic cleanup
local_data_frame_source <- function(
  data,
  table_name = "test_table",
  engine = "duckdb",
  env = parent.frame()
) {
  df_source <- DataFrameSource$new(data, table_name, engine = engine)
  withr::defer(df_source$cleanup(), envir = env)
  df_source
}

local_recording_data_frame_source <- function(
  data = new_test_df(),
  table_name = "test_table",
  engine = "duckdb",
  env = parent.frame()
) {
  state <- new.env(parent = emptyenv())
  state$get_data_calls <- 0L
  state$get_data_error <- NULL

  RecordingDataFrameSource <- R6::R6Class(
    "RecordingDataFrameSource",
    inherit = DataFrameSource,
    public = list(
      get_data = function() {
        state$get_data_calls <- state$get_data_calls + 1L
        if (!is.null(state$get_data_error)) {
          stop(state$get_data_error)
        }
        super$get_data()
      }
    )
  )
  source <- RecordingDataFrameSource$new(data, table_name, engine = engine)
  withr::defer(source$cleanup(), envir = env)
  list(source = source, state = state)
}

new_fake_handoff_data_source <- function(
  table_name = "orders",
  db_type = "PostgreSQL"
) {
  source <- new.env(parent = emptyenv())
  source$table_name <- table_name
  source$get_db_type <- function() db_type
  class(source) <- c("FakeHandoffDataSource", "R6")
  source
}

new_recording_handoff_chat <- function(
  history = list(),
  ask_results = list(),
  stream_results = list(),
  journal = NULL
) {
  state <- new.env(parent = emptyenv())
  state$history <- history
  state$ask_results <- ask_results
  state$stream_results <- stream_results
  state$events <- list()

  RecordingHandoffChat <- R6::R6Class(
    "RecordingHandoffChat",
    inherit = HandoffChat,
    public = list(
      initialize = function() {},

      history_turns = function() {
        state$history
      },

      ask = function(prompt, type, turns = list()) {
        event <- list(
          action = "ask",
          prompt = prompt,
          type = type,
          turns = turns
        )
        state$events[[length(state$events) + 1L]] <- event
        append_handoff_journal(journal, event)
        result <- state$ask_results[[1]]
        state$ask_results <- state$ask_results[-1]
        if (inherits(result, "condition")) {
          return(promises::promise_reject(result))
        }
        promises::promise_resolve(result)
      },

      stream = function(
        prompt,
        turns = list(),
        system_prompt = NULL,
        type,
        view
      ) {
        event <- list(
          action = "stream",
          prompt = prompt,
          turns = turns,
          system_prompt = system_prompt,
          type = type
        )
        state$events[[length(state$events) + 1L]] <- event
        append_handoff_journal(journal, event)
        result <- state$stream_results[[1]]
        state$stream_results <- state$stream_results[-1]
        if (is.function(result)) {
          result <- result(view)
        }
        if (inherits(result, "condition")) {
          return(promises::promise_reject(result))
        }
        promises::promise_resolve(result)
      }
    )
  )

  list(chat = RecordingHandoffChat$new(), state = state)
}

new_recording_handoff_view <- function(failures = list(), journal = NULL) {
  view <- new.env(parent = emptyenv())
  view$events <- list()
  view$failures <- failures
  view$counts <- new.env(parent = emptyenv())

  record <- function(action, ...) {
    count <- if (exists(action, envir = view$counts, inherits = FALSE)) {
      get(action, envir = view$counts, inherits = FALSE) + 1L
    } else {
      1L
    }
    assign(action, count, envir = view$counts)
    event <- list(action = action, ...)
    view$events[[length(view$events) + 1L]] <- event
    append_handoff_journal(journal, event)
    if (count %in% (view$failures[[action]] %||% integer())) {
      stop(paste(action, "failed"))
    }
    invisible(NULL)
  }

  view$show_modal <- function(items) record("show_modal", items = items)
  view$remove_modal <- function() record("remove_modal")
  view$show_recommendation <- function(value) {
    record("show_recommendation", value = value)
  }
  view$show_recommendation_error <- function(error) {
    record("show_recommendation_error", error = error)
  }
  view$clear_source <- function(language) {
    record("clear_source", language = language)
  }
  view$set_panel_open <- function(open) {
    record("set_panel_open", open = open)
  }
  view$show_handoff <- function(state, download_available) {
    record(
      "show_handoff",
      state = state,
      download_available = download_available
    )
  }
  view$append_pill <- function(handoff_id, handoff_type, summary) {
    record(
      "append_pill",
      handoff_id = handoff_id,
      handoff_type = handoff_type,
      summary = summary
    )
  }
  view
}

new_recording_handoff_store <- function(
  journal = NULL,
  max_items = 25L
) {
  RecordingHandoffStore <- R6::R6Class(
    "RecordingHandoffStore",
    inherit = HandoffStore,
    public = list(
      initialize = function() {
        super$initialize(max_items = max_items)
      },

      remember = function(state) {
        append_handoff_journal(
          journal,
          list(action = "remember", state = state)
        )
        super$remember(state)
      }
    )
  )
  RecordingHandoffStore$new()
}

new_handoff_event_journal <- function() {
  journal <- new.env(parent = emptyenv())
  journal$events <- list()
  journal
}

append_handoff_journal <- function(journal, event) {
  if (is.null(journal)) {
    return(invisible(NULL))
  }
  journal$events[[length(journal$events) + 1L]] <- event
  invisible(NULL)
}

new_recording_handoff_executor <- function(schemas) {
  executor <- new.env(parent = emptyenv())
  executor$calls <- list()
  executor$get_schema <- function(
    table_name,
    categorical_threshold,
    table_spec = NULL
  ) {
    executor$calls[[length(executor$calls) + 1L]] <- list(
      table_name = table_name,
      categorical_threshold = categorical_threshold,
      table_spec = table_spec
    )
    schemas[[table_name]]
  }
  executor
}

local_querychat <- function(
  data_source = new_test_df(),
  table_name = "test_table",
  ...,
  env = parent.frame()
) {
  qc <- QueryChat$new(data_source, table_name, ...)
  withr::defer(qc$cleanup(), envir = env)
  qc
}

# Create a TblSqlSource with DuckDB and automatic cleanup
local_tbl_sql_source <- function(
  data = new_test_df(),
  table_name = "test_table",
  tbl_transform = identity,
  env = parent.frame()
) {
  skip_if_not_installed("duckdb")
  skip_if_not_installed("dbplyr")
  skip_if_not_installed("dplyr")

  conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
  withr::defer(DBI::dbDisconnect(conn, shutdown = TRUE), envir = env)

  DBI::dbWriteTable(conn, table_name, data, overwrite = TRUE)
  tbl <- dplyr::tbl(conn, table_name)
  tbl <- tbl_transform(tbl)

  TblSqlSource$new(tbl, table_name)
}

# Create a DuckDB connection with multiple tables for JOIN tests
local_duckdb_multi_table <- function(
  env = parent.frame()
) {
  skip_if_not_installed("duckdb")

  conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
  withr::defer(DBI::dbDisconnect(conn, shutdown = TRUE), envir = env)

  # Table A with id and name
  DBI::dbWriteTable(
    conn,
    "table_a",
    data.frame(
      id = 1:3,
      name = c("Alice", "Bob", "Carol"),
      stringsAsFactors = FALSE
    )
  )

  # Table B with id and value
  DBI::dbWriteTable(
    conn,
    "table_b",
    data.frame(
      id = 1:3,
      value = c(100, 200, 300),
      stringsAsFactors = FALSE
    )
  )

  conn
}

mock_ellmer_chat_client <- function(
  public = list(),
  private = list(),
  env = parent.frame()
) {
  MockChat <- R6::R6Class(
    "MockChat",
    inherit = asNamespace("ellmer")[["Chat"]],
    public = public,
    private = private
  )

  MockChat$new(
    ellmer::Provider("test", "test", "test"),
    model = "test"
  )
}

mock_handoff_stream <- coro::async_generator(function(
  chat,
  prompt,
  chunks,
  completed_content,
  stream_error,
  cancellation,
  partial_turn_reason
) {
  for (chunk in chunks) {
    coro::yield(chunk)
  }

  if (!is.null(stream_error)) {
    stop(stream_error)
  }
  if (!is.null(cancellation)) {
    stop(cancellation)
  }
  if (!is.null(partial_turn_reason)) {
    chat$set_turns(
      c(
        chat$get_turns(),
        list(
          ellmer::UserTurn(prompt),
          ellmer::AssistantPartialTurn(
            "partial structured output",
            reason = partial_turn_reason
          )
        )
      )
    )
  } else if (!is.null(completed_content)) {
    chat$set_turns(
      c(
        chat$get_turns(),
        list(
          ellmer::UserTurn(prompt),
          ellmer::AssistantTurn(list(completed_content))
        )
      )
    )
  }
  coro::exhausted()
})

MockHandoffChat <- R6::R6Class(
  "MockHandoffChat",
  inherit = asNamespace("ellmer")[["Chat"]],
  public = list(
    initialize = function(
      structured_result = NULL,
      stream_chunks = character(),
      completed_content = NULL,
      stream_error = NULL,
      stream_start_error = NULL,
      cancellation = NULL,
      partial_turn_reason = NULL,
      turns = list(),
      system_prompt = NULL
    ) {
      super$initialize(
        ellmer::Provider("test", "test", "test"),
        model = "test",
        system_prompt = system_prompt
      )
      self$set_turns(turns)

      private$state <- new.env(parent = emptyenv())
      private$state$structured_result <- structured_result
      private$state$stream_chunks <- stream_chunks
      private$state$completed_content <- completed_content
      private$state$stream_error <- stream_error
      private$state$stream_start_error <- stream_start_error
      private$state$cancellation <- cancellation
      private$state$partial_turn_reason <- partial_turn_reason
      private$state$requests <- list()
    },

    requests = function() {
      private$state$requests
    },

    chat_structured_async = function(prompt, type) {
      private$record_request(prompt, type)
      promises::promise_resolve(private$state$structured_result)
    },

    stream_async = function(prompt, type) {
      private$record_request(prompt, type)
      if (!is.null(private$state$stream_start_error)) {
        stop(private$state$stream_start_error)
      }
      mock_handoff_stream(
        self,
        prompt,
        private$state$stream_chunks,
        private$state$completed_content,
        private$state$stream_error,
        private$state$cancellation,
        private$state$partial_turn_reason
      )
    }
  ),
  private = list(
    state = NULL,

    record_request = function(prompt, type) {
      private$state$requests[[length(private$state$requests) + 1L]] <-
        list(
          turns = self$get_turns(),
          system_prompt = self$get_system_prompt(),
          prompt = prompt,
          type = type
        )
    }
  )
)

sync_promise <- function(promise, timeout = 5) {
  done <- FALSE
  value <- NULL
  error <- NULL
  deadline <- proc.time()[["elapsed"]] + timeout

  promises::then(
    promise,
    function(result) {
      value <<- result
      done <<- TRUE
    },
    function(condition) {
      error <<- condition
      done <<- TRUE
    }
  )

  while (!done) {
    remaining <- deadline - proc.time()[["elapsed"]]
    if (remaining <= 0) {
      cli::cli_abort(
        "Promise did not settle within {timeout} seconds."
      )
    }
    later::run_now(min(0.05, remaining))
  }
  if (!is.null(error)) {
    stop(error)
  }
  value
}

# shinychat::chat_restore() validates that `client` is an ellmer::Chat() R6
# object; the lightweight `structure(list(), class = c("MockChat", "Chat"))`
# fakes used throughout this file don't satisfy that. mod_server() calls
# chat_restore() whenever `history` isn't in bookmark mode, so tests that
# don't care about its behavior need a no-op stand-in.
local_mock_chat_restore <- function(env = parent.frame()) {
  testthat::local_mocked_bindings(
    chat_restore = function(...) invisible(NULL),
    .package = "shinychat",
    .env = env
  )
}

# Minimal mock matching the shape shinychat::chat_server() always returns,
# including a $history interface that's present regardless of the `history`
# argument's value (registrations are just inert if history isn't active).
mock_chat_server_result <- function(client) {
  chat <- new.env(parent = emptyenv())
  chat$client <- client
  chat$commands <- list()
  chat$appended <- list()
  chat$status_value <- "idle"
  chat$slash_command <- function(
    name,
    description,
    handler,
    ...,
    echo = NULL,
    force = FALSE
  ) {
    chat$commands[[name]] <- list(
      name = name,
      description = description,
      handler = handler,
      echo = echo,
      force = force
    )
    invisible(function() NULL)
  }
  chat$status <- function() chat$status_value
  chat$append <- function(response, role = "assistant", icon = NULL) {
    chat$appended[[length(chat$appended) + 1L]] <- list(
      response = response,
      role = role,
      icon = icon
    )
    invisible(NULL)
  }
  chat$history <- list(
    save = function() FALSE,
    on_save = function(fn) invisible(fn),
    on_restore = function(fn) invisible(fn)
  )
  chat
}
