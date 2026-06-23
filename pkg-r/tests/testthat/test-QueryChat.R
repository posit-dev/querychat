describe("QueryChat$new()", {
  skip_if_no_dataframe_engine()

  it("automatically converts data.frame to DataFrameSource", {
    qc <- QueryChat$new(
      data_source = new_test_df(),
      table_name = "test_df",
      greeting = "Test greeting"
    )
    withr::defer(qc$cleanup())

    expect_s3_class(qc_data_source(qc, "test_df"), "DataSource")
    expect_s3_class(qc_data_source(qc, "test_df"), "DataFrameSource")
  })

  it("accepts DataFrameSource directly", {
    df_source <- local_data_frame_source(new_test_df(), "test_source")

    qc <- QueryChat$new(
      data_source = df_source,
      table_name = "test_source",
      greeting = "Test greeting"
    )

    expect_s3_class(qc_data_source(qc, "test_source"), "DataFrameSource")
    expect_equal(qc_data_source(qc, "test_source")$table_name, "test_source")
  })

  it("accepts DBISource", {
    db <- local_sqlite_connection(new_test_df())
    dbi_source <- DBISource$new(db$conn, "test_table")

    qc <- QueryChat$new(
      data_source = dbi_source,
      table_name = "test_table",
      greeting = "Test greeting"
    )

    expect_s3_class(qc_data_source(qc, "test_table"), "DBISource")
    expect_equal(qc_data_source(qc, "test_table")$table_name, "test_table")
  })

  it("infers table_name from data.frame variable name", {
    my_data <- new_test_df()
    qc <- QueryChat$new(my_data, greeting = "Test")
    withr::defer(qc$cleanup())

    expect_equal(qc_data_source(qc, "my_data")$table_name, "my_data")
    expect_equal(qc$id, "querychat_my_data")
  })

  it("loads greeting from file if file exists", {
    withr::local_envvar(OPENAI_API_KEY = "boop")

    greeting_file <- withr::local_tempfile(fileext = ".md")
    greeting_text <- "# Welcome to the data!"
    writeLines(greeting_text, greeting_file)

    qc <- QueryChat$new(
      new_test_df(),
      table_name = "test_df",
      greeting = greeting_file
    )
    withr::defer(qc$cleanup())

    # File content should be loaded (exact format depends on read_utf8 implementation)
    expect_type(qc$greeting, "character")
    expect_match(qc$greeting, greeting_text, fixed = TRUE)
  })

  it("uses greeting string directly if file doesn't exist", {
    qc <- QueryChat$new(
      new_test_df(),
      table_name = "test_df",
      greeting = "Simple greeting"
    )
    withr::defer(qc$cleanup())
    expect_match(qc$greeting, "Simple greeting", fixed = TRUE)
  })

  it("errors with invalid argument types", {
    expect_snapshot(error = TRUE, {
      QueryChat$new(test_df, table_name = "test", id = 123)
    })

    expect_snapshot(error = TRUE, {
      QueryChat$new(test_df, table_name = "test", greeting = 123)
    })

    expect_snapshot(error = TRUE, {
      QueryChat$new(
        test_df,
        table_name = "test",
        categorical_threshold = "not_a_number"
      )
    })

    expect_snapshot(error = TRUE, {
      QueryChat$new(test_df, table_name = "test", cleanup = "not_logical")
    })
  })
})

describe("QueryChat deferred client", {
  it("accepts NULL data_source with table_name", {
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    expect_equal(length(qc$table_names()), 0L)
    expect_equal(qc$id, "querychat_users")
  })

  it("requires table_name when data_source is NULL", {
    expect_error(
      QueryChat$new(NULL),
      "table_name.*required"
    )
  })

  it("stores client spec without resolving it", {
    withr::local_envvar(OPENAI_API_KEY = NA)
    withr::local_options(querychat.client = NULL)
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    expect_equal(length(qc$table_names()), 0L)
  })

  it("stores explicit client string as spec", {
    withr::local_envvar(OPENAI_API_KEY = "boop")
    qc <- QueryChat$new(NULL, "users", greeting = "Test", client = "openai")
    expect_equal(length(qc$table_names()), 0L)
  })

  it("$client() errors when data_source is NULL", {
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    expect_error(
      qc$client(),
      "data_source.*must be set|data_source.*set before"
    )
  })

  it("$console() errors when data_source is NULL", {
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    expect_error(
      qc$console(),
      "data_source.*must be set|data_source.*set before"
    )
  })

  it("$generate_greeting() errors when data_source is NULL", {
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    expect_error(
      qc$generate_greeting(),
      "data_source.*must be set|data_source.*set before"
    )
  })

  it("$system_prompt errors when data_source is NULL", {
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    expect_error(
      qc$system_prompt,
      "data_source.*must be set|data_source.*set before"
    )
  })

  it("works after adding table via add_table()", {
    skip_if_no_dataframe_engine()
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    qc$add_table(new_users_df(), "users")

    expect_s3_class(qc_data_source(qc, "users"), "DataFrameSource")
    prompt <- qc$system_prompt
    expect_match(prompt, "users")
  })
})

describe("QueryChat integration with DBISource", {
  it("works with iris dataset queries", {
    skip_if_not_installed("RSQLite")

    library(DBI)
    library(RSQLite)

    temp_db <- withr::local_tempfile(fileext = ".db")
    conn <- dbConnect(RSQLite::SQLite(), temp_db)
    dbWriteTable(conn, "iris", iris, overwrite = TRUE)
    dbDisconnect(conn)

    db_conn <- dbConnect(RSQLite::SQLite(), temp_db)
    withr::defer(dbDisconnect(db_conn))

    iris_source <- DBISource$new(db_conn, "iris")

    withr::local_envvar(OPENAI_API_KEY = "boop")
    mock_client <- ellmer::chat_openai()

    qc <- QueryChat$new(
      data_source = iris_source,
      table_name = "iris",
      greeting = "Test greeting",
      client = mock_client
    )

    iris_source <- qc_data_source(qc, "iris")
    expect_s3_class(iris_source, "DBISource")
    expect_s3_class(iris_source, "DataSource")

    result_data <- iris_source$execute_query(NULL)
    expect_s3_class(result_data, "data.frame")
    expect_equal(nrow(result_data), 150)
    expect_equal(ncol(result_data), 5)

    query_result <- iris_source$execute_query(
      "SELECT \"Sepal.Length\", \"Sepal.Width\" FROM iris WHERE \"Species\" = 'setosa'"
    )
    expect_s3_class(query_result, "data.frame")
    expect_equal(nrow(query_result), 50)
    expect_equal(ncol(query_result), 2)
    expect_true(all(c("Sepal.Length", "Sepal.Width") %in% names(query_result)))
  })
})

describe("QueryChat$cleanup()", {
  it("cleans up data source resources", {
    test_df <- new_test_df()
    qc <- QueryChat$new(test_df, greeting = "Test")

    # Cleanup should not error
    expect_silent(qc$cleanup())

    # Should be idempotent
    expect_silent(qc$cleanup())
  })
})

describe("QueryChat$system_prompt", {
  it("returns the system prompt from the client", {
    test_df <- new_test_df()
    qc <- QueryChat$new(test_df, greeting = "Test")
    withr::defer(qc$cleanup())

    prompt <- qc$system_prompt

    expect_type(prompt, "character")
    expect_true(nchar(prompt) > 0)
    # Should contain table name
    expect_true(grepl("test_df", prompt, fixed = TRUE))
  })

  it("doesn't include update instructions if not enabled", {
    template <- "{{#has_tool_update}}update tool enabled!{{/has_tool_update}}"

    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = "query",
      prompt_template = template
    )
    withr::defer(qc$cleanup())

    expect_equal(qc$system_prompt, "")
  })

  it("doesn't include query instructions if not enabled", {
    template <- "{{#has_tool_query}}query tool enabled!{{/has_tool_query}}"

    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = "update",
      prompt_template = template
    )
    withr::defer(qc$cleanup())

    expect_equal(qc$system_prompt, "")
  })

  it("doesn't include update instructions if not enabled (full prompt)", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = "query"
    )
    withr::defer(qc$cleanup())

    tool_header <- "Filtering and Sorting Data"

    expect_no_match(qc$system_prompt, tool_header)
    expect_no_match(qc$client()$get_system_prompt(), tool_header)
    expect_match(qc$client(tools = "update")$get_system_prompt(), tool_header)
  })

  it("doesn't include query instructions if not enabled (full prompt)", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = "update"
    )
    withr::defer(qc$cleanup())

    tool_header <- "Answering Questions About Data"

    expect_no_match(qc$system_prompt, tool_header)
    expect_no_match(qc$client()$get_system_prompt(), tool_header)
    expect_match(qc$client(tools = "query")$get_system_prompt(), tool_header)
  })
})

describe("QueryChat$data_source", {
  skip_if_no_dataframe_engine()

  it("errors when accessed (removed)", {
    test_df <- new_test_df()
    qc <- QueryChat$new(test_df, greeting = "Test")
    withr::defer(qc$cleanup())

    expect_error(qc$data_source, "removed")
  })

  it("errors when set (removed)", {
    test_df <- new_test_df()
    qc <- QueryChat$new(test_df, greeting = "Test")
    withr::defer(qc$cleanup())

    expect_error(qc$data_source <- test_df, "removed")
  })
})

describe("QueryChat$client()", {
  it("uses default tools when tools = NA", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = c("update", "query")
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = NA)

    # Should have both update and query tools
    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_update_dashboard")
    expect_contains(tool_names, "querychat_reset_dashboard")
    expect_contains(tool_names, "querychat_query")
  })

  it("overrides default tools when tools parameter is provided", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = c("update", "query")
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = "query")

    # Should only have query tool (plus get_schema)
    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_query")
    expect_false("querychat_update_dashboard" %in% tool_names)
    expect_false("querychat_reset_dashboard" %in% tool_names)
  })

  it("registers only update tools when tools = 'update'", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = "update")

    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_update_dashboard")
    expect_contains(tool_names, "querychat_reset_dashboard")
    expect_false("querychat_query" %in% tool_names)
  })

  it("treats 'filter' as an alias for 'update'", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = "filter")

    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_update_dashboard")
    expect_contains(tool_names, "querychat_reset_dashboard")
    expect_false("querychat_query" %in% tool_names)
  })

  it("normalizes c('filter', 'query') to update + query tools", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = c("filter", "query")
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = NA)

    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_update_dashboard")
    expect_contains(tool_names, "querychat_reset_dashboard")
    expect_contains(tool_names, "querychat_query")
  })

  it("deduplicates when both 'filter' and 'update' are provided", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = c("filter", "update", "query")
    )
    withr::defer(qc$cleanup())

    expect_equal(qc$tools, c("update", "query"))
  })

  it("registers only query tool when tools = 'query'", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = "query")

    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_query")
    expect_false("querychat_update_dashboard" %in% tool_names)
    expect_false("querychat_reset_dashboard" %in% tool_names)
  })

  it("registers visualize tool when tools include 'visualize'", {
    skip_if_not_installed("ggsql")
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )

    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = c("query", "visualize")
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = c("query", "visualize"), session = session)

    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_query")
    expect_contains(tool_names, "querychat_visualize")
    expect_false("querychat_update_dashboard" %in% tool_names)
    expect_false("querychat_reset_dashboard" %in% tool_names)
  })

  it("registers visualize tool without a session", {
    skip_if_not_installed("ggsql")

    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = "visualize")

    tool_names <- sapply(client$get_tools(), function(t) t@name)
    expect_contains(tool_names, "querychat_visualize")
  })

  it("registers only visualize tool when tools = 'visualize'", {
    skip_if_not_installed("ggsql")
    session <- structure(
      list(
        output = list(),
        ns = identity
      ),
      class = "MockShinySession"
    )

    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = "visualize", session = session)

    tool_names <- sapply(client$get_tools(), function(t) t@name)
    # get_schema is always registered when tools != NULL
    expect_contains(tool_names, "querychat_visualize")
    expect_false("querychat_update_dashboard" %in% tool_names)
    expect_false("querychat_reset_dashboard" %in% tool_names)
    expect_false("querychat_query" %in% tool_names)
  })

  it("returns client with no tools when tools = NULL", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client <- qc$client(tools = NULL)

    expect_length(client$get_tools(), 0)
  })

  it("sets system prompt based on tools parameter", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client_query <- qc$client(tools = "query")
    client_update <- qc$client(tools = "update")

    prompt_query <- client_query$get_system_prompt()
    prompt_update <- client_update$get_system_prompt()

    # Query client should have query instructions but not update
    expect_match(prompt_query, "Answering Questions About Data")
    expect_no_match(prompt_query, "Filtering and Sorting Data")

    # Update client should have update instructions but not query
    expect_match(prompt_update, "Filtering and Sorting Data")
    expect_no_match(prompt_update, "Answering Questions About Data")
  })

  it("passes update_dashboard callback to tool", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    update_calls <- list()
    client <- qc$client(
      tools = "update",
      update_dashboard = function(query, title, table) {
        update_calls <<- list(query = query, title = title, table = table)
      }
    )

    # Find and call the update tool
    tools <- client$get_tools()
    update_tool <- tools[[
      which(
        sapply(tools, function(t) {
          t@name == "querychat_update_dashboard"
        })
      )
    ]]

    # Call the tool - it should execute the query and call the callback
    result <- update_tool(
      query = "SELECT * FROM test_df WHERE id = 1",
      title = "Test Filter",
      table = "test_df"
    )

    expect_null(result@error)
    expect_equal(update_calls$query, "SELECT * FROM test_df WHERE id = 1")
    expect_equal(update_calls$title, "Test Filter")
    expect_equal(update_calls$table, "test_df")
  })

  it("passes reset_dashboard callback to tool", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    reset_called_with <- NULL
    client <- qc$client(
      tools = "update",
      reset_dashboard = function(table) {
        reset_called_with <<- table
      }
    )

    # Find and call the reset tool
    tools <- client$get_tools()
    reset_tool <- tools[[
      which(
        sapply(tools, function(t) {
          t@name == "querychat_reset_dashboard"
        })
      )
    ]]

    # Call the tool
    reset_tool("test_df")

    expect_equal(reset_called_with, "test_df")
  })

  it("returns independent client instances on each call", {
    qc <- QueryChat$new(
      new_test_df(),
      "test_df"
    )
    withr::defer(qc$cleanup())

    client1 <- qc$client()
    client2 <- qc$client()

    # Should be different objects
    expect_false(identical(client1, client2))

    # Modifying one shouldn't affect the other
    client1$set_turns(list(ellmer::Turn("user", "test message")))
    expect_length(client1$get_turns(), 1)
    expect_length(client2$get_turns(), 0)
  })

  it("returns independent instances when client spec is a Chat object", {
    withr::local_envvar(OPENAI_API_KEY = "boop")
    chat_spec <- ellmer::chat_openai()

    qc <- QueryChat$new(
      new_test_df(),
      "test_df",
      client = chat_spec
    )
    withr::defer(qc$cleanup())

    client1 <- qc$client()
    client2 <- qc$client()

    expect_false(identical(client1, client2))

    client1$set_turns(list(ellmer::Turn("user", "test message")))
    expect_length(client1$get_turns(), 1)
    expect_length(client2$get_turns(), 0)
  })

  it("respects QueryChat initialization tools by default", {
    qc_query_only <- QueryChat$new(
      new_test_df(),
      "test_df",
      tools = "query"
    )
    withr::defer(qc_query_only$cleanup())

    client <- qc_query_only$client()
    tool_names <- sapply(client$get_tools(), function(t) t@name)

    expect_contains(tool_names, "querychat_query")
    expect_false("querychat_update_dashboard" %in% tool_names)
  })
})

test_that("QueryChat$generate_greeting() generates a greeting using the LLM client", {
  skip_if_no_dataframe_engine()
  client <- mock_ellmer_chat_client(
    public = list(
      chat = function(message, ...) {
        expect_true(startsWith(message, querychat:::GREETING_MARKER))
        expect_match(message, "<schema>") # single table → schema included
        "Welcome! This is a mock response for testing."
      }
    )
  )

  test_df <- new_test_df()

  qc <- QueryChat$new(test_df, client = client)
  withr::defer(qc$cleanup())

  greeting <- qc$generate_greeting()
  expect_equal(greeting, "Welcome! This is a mock response for testing.")
})

test_that("generate_greeting() sends schema-embedded prompt for single table", {
  skip_if_no_dataframe_engine()
  client <- mock_ellmer_chat_client(
    public = list(
      chat = function(message, ...) {
        expect_true(startsWith(message, querychat:::GREETING_MARKER))
        expect_match(message, "<schema>")
        "Hello!"
      }
    )
  )
  test_df <- new_test_df()
  qc <- QueryChat$new(test_df, client = client)
  withr::defer(qc$cleanup())

  greeting <- qc$generate_greeting()
  expect_equal(greeting, "Hello!")
})

test_that("generate_greeting() omits schema for multi-table with no greeting_tables", {
  skip_if_no_dataframe_engine()
  client <- mock_ellmer_chat_client(
    public = list(
      chat = function(message, ...) {
        expect_true(startsWith(message, querychat:::GREETING_MARKER))
        expect_false(grepl("<schema>", message))
        "Hello!"
      }
    )
  )
  qc <- QueryChat$new(
    data_source = NULL,
    table_name = "placeholder",
    client = client
  )
  withr::defer(qc$cleanup())
  qc$add_table(new_test_df(), "t1")
  qc$add_table(data.frame(x = 1), "t2")

  qc$generate_greeting()
})

test_that("generate_greeting() includes schema for tables in greeting_tables", {
  skip_if_no_dataframe_engine()
  client <- mock_ellmer_chat_client(
    public = list(
      chat = function(message, ...) {
        expect_match(message, "amount")
        expect_false(grepl("\\bname\\b", message))
        "Hello!"
      }
    )
  )
  qc <- QueryChat$new(
    data_source = NULL,
    table_name = "placeholder",
    client = client,
    greeting_tables = "t1"
  )
  withr::defer(qc$cleanup())
  qc$add_table(data.frame(amount = c(1, 2)), "t1")
  qc$add_table(data.frame(name = c("A")), "t2")

  qc$generate_greeting()
})

test_that("QueryChat$server() errors when called outside Shiny context", {
  withr::local_envvar(OPENAI_API_KEY = "boop")

  test_df <- new_test_df()
  qc <- QueryChat$new(test_df, greeting = "Test")
  withr::defer(qc$cleanup())

  expect_snapshot(error = TRUE, {
    qc$server()
  })
})

describe("querychat()", {
  skip_if_no_dataframe_engine()
  withr::local_envvar(OPENAI_API_KEY = "boop")

  it("creates a QueryChat object", {
    test_df <- new_test_df()
    qc <- querychat(test_df, greeting = "Test greeting")
    withr::defer(qc$cleanup())

    expect_s3_class(qc, "QueryChat")
    expect_s3_class(qc_data_source(qc, "test_df"), "DataFrameSource")
    expect_equal(qc$greeting, "Test greeting")
  })

  it("infers table_name from variable name", {
    my_test_data <- new_test_df()
    qc <- querychat(my_test_data, greeting = "Test")
    withr::defer(qc$cleanup())

    expect_equal(
      qc_data_source(qc, "my_test_data")$table_name,
      "my_test_data"
    )
  })

  it("passes all arguments to QueryChat$new()", {
    test_df <- new_test_df()

    qc <- querychat(
      test_df,
      table_name = "custom_name",
      id = "custom_id",
      greeting = "Custom greeting",
      categorical_threshold = 10,
      cleanup = FALSE
    )
    withr::defer(qc$cleanup())

    expect_equal(qc$id, "custom_id")
    expect_equal(qc$greeting, "Custom greeting")
    expect_equal(qc_data_source(qc, "custom_name")$table_name, "custom_name")
  })
})

describe("QueryChat$console()", {
  local_mocked_r6_class(
    QueryChat,
    public = list(
      get_client_console = function() {
        private$.client_console
      }
    )
  )

  it("defaults to query-only tools (privacy-focused)", {
    qc <- local_querychat()

    live_console_called <- FALSE
    local_mocked_bindings(
      live_console = function(chat) {
        live_console_called <<- TRUE
      },
      .package = "ellmer"
    )

    qc$console()
    expect_true(live_console_called)

    console_client <- qc$get_client_console()
    expect_s3_class(console_client, "Chat")

    tools <- console_client$get_tools()
    tool_names <- names(tools)
    expect_contains(tool_names, "querychat_query")
  })

  it("persists console client across calls", {
    qc <- local_querychat()

    # Track live_console calls
    live_console_call_count <- 0
    local_mocked_bindings(
      live_console = function(chat) {
        live_console_call_count <<- live_console_call_count + 1
      },
      .package = "ellmer"
    )

    qc$console()
    first_client <- qc$get_client_console()

    qc$console()
    second_client <- qc$get_client_console()

    expect_identical(first_client, second_client)
    expect_equal(live_console_call_count, 2)
  })

  it("creates fresh client when `new = TRUE`", {
    qc <- local_querychat()
    local_mocked_bindings(live_console = identity, .package = "ellmer")

    qc$console()
    first_client <- qc$get_client_console()

    qc$console(new = TRUE)
    second_client <- qc$get_client_console()

    expect_false(identical(first_client, second_client))
  })

  it("allows overriding tools via `tools` parameter", {
    qc <- local_querychat()
    local_mocked_bindings(live_console = identity, .package = "ellmer")

    qc$console(tools = c("update", "query"))

    console_client <- qc$get_client_console()
    expect_s3_class(console_client, "Chat")

    tools <- console_client$get_tools()
    expect_contains(
      names(tools),
      c(
        "querychat_query",
        "querychat_update_dashboard",
        "querychat_reset_dashboard"
      )
    )
  })
})

describe("normalize_data_source()", {
  skip_if_no_dataframe_engine()

  it("returns DataSource objects unchanged", {
    test_df <- new_test_df()
    df_source <- DataFrameSource$new(test_df, "test_df")
    withr::defer(df_source$cleanup())

    result <- normalize_data_source(df_source, "test_df")

    expect_identical(result, df_source)
  })

  it("converts data.frame to DataFrameSource", {
    test_df <- new_test_df()

    result <- normalize_data_source(test_df, "test_df")
    withr::defer(result$cleanup())

    expect_s3_class(result, "DataFrameSource")
    expect_equal(result$table_name, "test_df")
  })

  it("converts DBIConnection to DBISource", {
    test_df <- new_test_df()
    db <- local_sqlite_connection(test_df)

    result <- normalize_data_source(db$conn, "test_table")

    expect_s3_class(result, "DBISource")
    expect_equal(result$table_name, "test_table")
  })

  it("errors with invalid data source types", {
    expect_snapshot(error = TRUE, {
      normalize_data_source("not_a_data_source", "table_name")
    })

    expect_snapshot(error = TRUE, {
      normalize_data_source(list(a = 1, b = 2), "table_name")
    })

    expect_snapshot(error = TRUE, {
      normalize_data_source(NULL, "table_name")
    })
  })
})

test_that("querychat_app() only cleans up data frame sources on exit", {
  local_mocked_r6_class(
    QueryChat,
    public = list(
      initialize = function(..., cleanup) {
        # have to use an option because the code is evaluated in a far-away env
        options(.test_cleanup = cleanup)
      },
      app = function(...) {}
    )
  )
  withr::local_options(rlang_interactive = TRUE)

  withr::with_options(list(.test_cleanup = NULL), {
    test_df <- new_test_df()
    querychat_app(test_df)
    cleanup_result <- getOption(".test_cleanup")
    expect_true(cleanup_result)
  })

  withr::with_options(list(.test_cleanup = NULL), {
    test_ds <- local_data_frame_source(new_test_df())
    querychat_app(test_ds)
    cleanup_result <- getOption(".test_cleanup")
    expect_false(cleanup_result)
  })

  withr::with_options(list(.test_cleanup = NULL), {
    con <- local_sqlite_connection(new_test_df())
    test_ds <- DBISource$new(con$conn, "test_table")
    querychat_app(test_ds)
    cleanup_result <- getOption(".test_cleanup")
    expect_false(cleanup_result)
  })
})

describe("QueryChat$server() client override", {
  it("accepts a client parameter", {
    withr::local_envvar(OPENAI_API_KEY = "boop")
    test_df <- new_test_df()
    qc <- QueryChat$new(test_df, table_name = "test_df", greeting = "Test")
    withr::defer(qc$cleanup())

    expect_error(
      qc$server(client = "openai"),
      "must be called within a Shiny server function"
    )
  })
})

describe("QueryChat deferred client with $server()", {
  it("$server() errors when data_source is NULL", {
    qc <- QueryChat$new(NULL, "users", greeting = "Test")
    expect_error(
      qc$server(),
      "must be called within a Shiny server function"
    )
  })

  it("$server(data_source=...) errors without Shiny session", {
    skip_if_no_dataframe_engine()
    qc <- QueryChat$new(NULL, "users", greeting = "Test")

    expect_error(
      qc$server(data_source = new_users_df()),
      "must be called within a Shiny server function"
    )
  })
})

describe("QueryChat$add_tables()", {
  local_multi_table_conn <- function(env = parent.frame()) {
    skip_if_not_installed("RSQLite")
    conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn), envir = env)
    DBI::dbWriteTable(
      conn,
      "orders",
      data.frame(id = 1:2, amount = c(9.99, 4.50))
    )
    DBI::dbWriteTable(
      conn,
      "customers",
      data.frame(id = 1:2, name = c("Alice", "Bob"))
    )
    conn
  }

  it("auto-discovery registers all tables", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    suppressWarnings(qc$add_tables(conn))
    expect_setequal(qc$table_names(), c("orders", "customers"))
  })

  it("explicit tables registers only those", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    qc$add_tables(conn, tables = "orders")
    expect_equal(qc$table_names(), "orders")
  })

  it("nonexistent table name raises error", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    expect_error(
      qc$add_tables(conn, tables = "nonexistent"),
      "not found"
    )
  })

  it("duplicate without replace raises error", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    qc$add_tables(conn, tables = "orders")
    expect_error(
      qc$add_tables(conn, tables = "orders"),
      "already exists"
    )
  })

  it("replace = TRUE on existing table succeeds", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    qc$add_tables(conn, tables = "orders")
    expect_no_error(qc$add_tables(conn, tables = "orders", replace = TRUE))
    expect_true("orders" %in% qc$table_names())
  })

  it("non-DBI argument raises error", {
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    expect_error(
      qc$add_tables(new_test_df()),
      "DBIConnection"
    )
  })

  it("empty tables vector raises error", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    expect_error(
      qc$add_tables(conn, tables = character(0)),
      "No tables found"
    )
  })

  it("calling after server initialization raises error", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    qc$.__enclos_env__$private$.server_initialized <- TRUE
    expect_error(
      qc$add_tables(conn),
      "after server initialization"
    )
  })

  it("system prompt built exactly once for multiple tables", {
    conn <- local_multi_table_conn()
    qc <- QueryChat$new(NULL, "placeholder", greeting = "Test")
    warns <- character(0)
    withCallingHandlers(
      qc$add_tables(conn),
      warning = function(w) {
        warns <<- c(warns, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    )
    multi_table_warns <- warns[grepl("Multiple tables", warns)]
    expect_length(multi_table_warns, 1L)
  })
})
