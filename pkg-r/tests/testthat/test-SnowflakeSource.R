# Tests for Snowflake semantic view functionality in DBISource

describe("format_semantic_view_ddls()", {
  it("formats single semantic view correctly", {
    views <- list(
      list(name = "db.schema.view", ddl = "CREATE SEMANTIC VIEW test_view")
    )
    result <- format_semantic_view_ddls(views)

    expect_match(result, "db.schema.view")
    expect_match(result, "CREATE SEMANTIC VIEW test_view")
    expect_match(result, "```sql")
  })

  it("formats multiple views", {
    views <- list(
      list(name = "db.schema.view1", ddl = "CREATE SEMANTIC VIEW v1"),
      list(name = "db.schema.view2", ddl = "CREATE SEMANTIC VIEW v2")
    )
    result <- format_semantic_view_ddls(views)

    expect_match(result, "db.schema.view1")
    expect_match(result, "db.schema.view2")
    expect_match(result, "CREATE SEMANTIC VIEW v1")
    expect_match(result, "CREATE SEMANTIC VIEW v2")
  })
})

describe("get_semantic_views_section_impl()", {
  it("includes IMPORTANT notice", {
    views <- list(
      list(name = "test", ddl = "DDL")
    )
    result <- get_semantic_views_section_impl(views)
    expect_match(result, "\\*\\*IMPORTANT\\*\\*")
  })

  it("includes section header", {
    views <- list(
      list(name = "test", ddl = "DDL")
    )
    result <- get_semantic_views_section_impl(views)
    expect_match(result, "## Semantic Views")
  })

  it("returns empty string for empty views list", {
    result <- get_semantic_views_section_impl(list())
    expect_equal(result, "")
  })
})

describe("SQL escaping in get_semantic_view_ddl()", {
  it("escapes single quotes in view names", {
    # We can't test the full function without a Snowflake connection,
    # but we can test the escaping logic directly
    fq_name <- "db.schema.test'view"
    safe_name <- gsub("'", "''", fq_name, fixed = TRUE)

    expect_equal(safe_name, "db.schema.test''view")
  })

  it("leaves normal names unchanged", {
    fq_name <- "db.schema.normal_view"
    safe_name <- gsub("'", "''", fq_name, fixed = TRUE)

    expect_equal(safe_name, "db.schema.normal_view")
  })
})

describe("is_snowflake_connection()", {
  it("returns FALSE for non-Snowflake connections", {
    skip_if_not_installed("RSQLite")

    conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn))

    expect_false(is_snowflake_connection(conn))
  })

  it("returns FALSE for non-DBI objects", {
    expect_false(is_snowflake_connection(NULL))
    expect_false(is_snowflake_connection("not a connection"))
    expect_false(is_snowflake_connection(list(fake = "connection")))
    expect_false(is_snowflake_connection(123))
  })
})

describe("DBISource semantic views", {
  it("get_semantic_views_section() returns empty for non-Snowflake", {
    skip_if_not_installed("RSQLite")

    conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn))
    DBI::dbWriteTable(conn, "test_table", data.frame(x = 1:3))

    source <- DBISource$new(conn, "test_table")
    expect_equal(source$get_semantic_views_section(), "")
  })
})

describe("discover_semantic_views_impl()", {
  it("propagates errors (not swallowed)", {
    skip_if_not_installed("RSQLite")

    # SQLite doesn't have SHOW SEMANTIC VIEWS, so it should error
    conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn))

    # Without tryCatch wrapping, this should error (not return empty list)
    # The error is a syntax error since SQLite doesn't support SHOW command
    expect_error(
      discover_semantic_views_impl(conn),
      "SHOW"
    )
  })

  it("respects QUERYCHAT_DISABLE_SEMANTIC_VIEWS env var", {
    skip_if_not_installed("RSQLite")

    conn <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
    withr::defer(DBI::dbDisconnect(conn))

    withr::with_envvar(c("QUERYCHAT_DISABLE_SEMANTIC_VIEWS" = "1"), {
      # Should return empty list without querying (no error from SQLite)
      result <- discover_semantic_views_impl(conn)
      expect_equal(result, list())
    })
  })
})
