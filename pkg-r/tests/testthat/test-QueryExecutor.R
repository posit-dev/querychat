describe("DataSourceExecutor", {
  skip_if_not_installed("duckdb")

  users_source <- local_data_frame_source(new_users_df(), "users")
  sources <- list(users = users_source)
  executor <- DataSourceExecutor$new(sources)

  it("delegates execute_query() to primary source", {
    result <- executor$execute_query("SELECT * FROM users WHERE age > 28")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 3)
  })

  it("delegates test_query() to the named source", {
    result <- executor$test_query("SELECT * FROM users", "users")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
  })

  it("returns correct get_db_type()", {
    expect_equal(executor$get_db_type(), "DuckDB")
  })

  it("gets schema for a named table", {
    schema <- executor$get_schema("users", categorical_threshold = 20)
    expect_type(schema, "character")
    expect_match(schema, "Table: users")
    expect_match(schema, "id")
    expect_match(schema, "name")
    expect_match(schema, "age")
  })
})

describe("DuckDBExecutor", {
  skip_if_not_installed("duckdb")

  it("registers multiple data frames for cross-table JOINs", {
    scores <- data.frame(
      id = 1:5,
      score = c(90, 85, 92, 78, 88),
      stringsAsFactors = FALSE
    )
    sources <- list(
      users = local_data_frame_source(new_users_df(), "users"),
      scores = local_data_frame_source(scores, "scores")
    )
    executor <- DuckDBExecutor$new(sources)
    withr::defer(executor$cleanup())

    result <- executor$execute_query(
      "SELECT u.name, s.score FROM users u JOIN scores s ON u.id = s.id"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 5)
    expect_true("name" %in% names(result))
    expect_true("score" %in% names(result))
  })

  it("enforces require_all_columns per table in test_query()", {
    sources <- list(users = local_data_frame_source(new_users_df(), "users"))
    executor <- DuckDBExecutor$new(sources)
    withr::defer(executor$cleanup())

    # Query that drops a column should fail with require_all_columns = TRUE
    expect_error(
      executor$test_query(
        "SELECT id, name FROM users",
        "users",
        require_all_columns = TRUE
      ),
      class = "querychat_missing_columns_error"
    )

    # Full select should pass
    expect_no_error(
      executor$test_query(
        "SELECT * FROM users",
        "users",
        require_all_columns = TRUE
      )
    )
  })

  it("locks down the connection (DDL like CREATE TABLE should fail)", {
    sources <- list(users = local_data_frame_source(new_users_df(), "users"))
    executor <- DuckDBExecutor$new(sources)
    withr::defer(executor$cleanup())

    expect_error(
      executor$execute_query("CREATE TABLE new_table (id INTEGER)")
    )
  })

  it("returns correct get_db_type()", {
    sources <- list(users = local_data_frame_source(new_users_df(), "users"))
    executor <- DuckDBExecutor$new(sources)
    withr::defer(executor$cleanup())

    expect_equal(executor$get_db_type(), "DuckDB")
  })

  it("gets schema for a named table", {
    sources <- list(users = local_data_frame_source(new_users_df(), "users"))
    executor <- DuckDBExecutor$new(sources)
    withr::defer(executor$cleanup())

    schema <- executor$get_schema("users", categorical_threshold = 20)
    expect_type(schema, "character")
    expect_match(schema, "Table: users")
    expect_match(schema, "id")
    expect_match(schema, "name")
    expect_match(schema, "age")
  })
})

describe("build_query_executor()", {
  skip_if_not_installed("duckdb")

  it("returns DataSourceExecutor for a single table", {
    sources <- list(users = local_data_frame_source(new_users_df(), "users"))
    executor <- build_query_executor(sources)

    expect_s3_class(executor, "DataSourceExecutor")
    expect_s3_class(executor, "QueryExecutor")
  })

  it("returns DuckDBExecutor for multiple DataFrameSources", {
    sources <- list(
      users = local_data_frame_source(new_users_df(), "users"),
      test = local_data_frame_source(new_test_df(), "test")
    )
    executor <- build_query_executor(sources)
    withr::defer(executor$cleanup())

    expect_s3_class(executor, "DuckDBExecutor")
    expect_s3_class(executor, "QueryExecutor")
  })

  it("returns DataSourceExecutor for multiple DBISources sharing same connection", {
    skip_if_not_installed("RSQLite")

    conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn))

    DBI::dbWriteTable(conn, "users", new_users_df())
    DBI::dbWriteTable(conn, "test_table", new_test_df())

    sources <- list(
      users = DBISource$new(conn, "users"),
      test_table = DBISource$new(conn, "test_table")
    )
    executor <- build_query_executor(sources)

    expect_s3_class(executor, "DataSourceExecutor")
    expect_s3_class(executor, "QueryExecutor")
  })
})

describe("check_source_compatibility()", {
  skip_if_not_installed("duckdb")

  it("accepts compatible DataFrameSources", {
    source1 <- local_data_frame_source(new_users_df(), "users")
    source2 <- local_data_frame_source(new_test_df(), "test")

    existing <- list(users = source1)
    expect_no_error(check_source_compatibility(existing, source2, "test"))
  })

  it("accepts an empty existing list (first table)", {
    source1 <- local_data_frame_source(new_users_df(), "users")
    expect_no_error(check_source_compatibility(list(), source1, "users"))
  })

  it("rejects mixed source types (DataFrameSource + DBISource)", {
    skip_if_not_installed("RSQLite")

    df_source <- local_data_frame_source(new_users_df(), "users")

    conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn))
    DBI::dbWriteTable(conn, "test_table", new_test_df())
    dbi_source <- DBISource$new(conn, "test_table")

    existing <- list(users = df_source)
    expect_error(
      check_source_compatibility(existing, dbi_source, "test_table")
    )
  })

  it("rejects DBISources on different connections", {
    skip_if_not_installed("RSQLite")

    conn1 <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn1))
    conn2 <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn2))

    DBI::dbWriteTable(conn1, "users", new_users_df())
    DBI::dbWriteTable(conn2, "test_table", new_test_df())

    source1 <- DBISource$new(conn1, "users")
    source2 <- DBISource$new(conn2, "test_table")

    expect_error(
      check_source_compatibility(list(users = source1), source2, "test_table"),
      "same connection"
    )
  })
})
