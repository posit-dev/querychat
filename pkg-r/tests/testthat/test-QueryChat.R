describe("QueryChat$new()", {
  it("automatically converts data.frame to DataFrameSource", {
    qc <- QueryChat$new(
      data_source = new_test_df(),
      table_name = "test_df",
      greeting = "Test greeting"
    )
    withr::defer(qc$cleanup())

    expect_s3_class(qc$data_source, "DataSource")
    expect_s3_class(qc$data_source, "DataFrameSource")
  })

  it("accepts DataFrameSource directly", {
    df_source <- local_data_frame_source(new_test_df(), "test_source")

    qc <- QueryChat$new(
      data_source = df_source,
      table_name = "test_source",
      greeting = "Test greeting"
    )

    expect_s3_class(qc$data_source, "DataFrameSource")
    expect_equal(qc$data_source$table_name, "test_source")
  })

  it("accepts DBISource", {
    db <- local_sqlite_connection(new_test_df())
    dbi_source <- DBISource$new(db$conn, "test_table")

    qc <- QueryChat$new(
      data_source = dbi_source,
      table_name = "test_table",
      greeting = "Test greeting"
    )

    expect_s3_class(qc$data_source, "DBISource")
    expect_equal(qc$data_source$table_name, "test_table")
  })

  it("infers table_name from data.frame variable name", {
    my_data <- new_test_df()
    qc <- QueryChat$new(my_data, greeting = "Test")
    withr::defer(qc$cleanup())

    expect_equal(qc$data_source$table_name, "my_data")
    expect_equal(qc$id, "my_data")
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

    expect_s3_class(qc$data_source, "DBISource")
    expect_s3_class(qc$data_source, "DataSource")

    result_data <- qc$data_source$execute_query(NULL)
    expect_s3_class(result_data, "data.frame")
    expect_equal(nrow(result_data), 150)
    expect_equal(ncol(result_data), 5)

    query_result <- qc$data_source$execute_query(
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
  it("returns the data source object", {
    test_df <- new_test_df()
    qc <- QueryChat$new(test_df, greeting = "Test")
    withr::defer(qc$cleanup())

    ds <- qc$data_source

    expect_s3_class(ds, "DataSource")
    expect_s3_class(ds, "DataFrameSource")
    expect_equal(ds$table_name, "test_df")
  })
})

test_that("QueryChat$generate_greeting() generates a greeting using the LLM client", {
  MockChat <- R6::R6Class(
    "MockChat",
    inherit = asNamespace("ellmer")[["Chat"]],
    public = list(
      chat = function(message, ...) {
        expect_equal(message, GREETING_PROMPT)
        "Welcome! This is a mock response for testing."
      }
    )
  )

  test_df <- new_test_df()
  client <- MockChat$new(ellmer::Provider("test", "test", "test"))

  # Create a mock client that returns a fixed greeting
  qc <- QueryChat$new(test_df, client = client)
  withr::defer(qc$cleanup())

  greeting <- qc$generate_greeting()
  expect_equal(greeting, "Welcome! This is a mock response for testing.")
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
  withr::local_envvar(OPENAI_API_KEY = "boop")

  it("creates a QueryChat object", {
    test_df <- new_test_df()
    qc <- querychat(test_df, greeting = "Test greeting")
    withr::defer(qc$cleanup())

    expect_s3_class(qc, "QueryChat")
    expect_s3_class(qc$data_source, "DataFrameSource")
    expect_equal(qc$greeting, "Test greeting")
  })

  it("infers table_name from variable name", {
    my_test_data <- new_test_df()
    qc <- querychat(my_test_data, greeting = "Test")
    withr::defer(qc$cleanup())

    expect_equal(qc$data_source$table_name, "my_test_data")
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
    expect_equal(qc$data_source$table_name, "custom_name")
  })
})

describe("normalize_data_source()", {
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
