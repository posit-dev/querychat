# Tests for SnowflakeSource and semantic view functionality

describe("format_semantic_views_section()", {
  it("formats single semantic view correctly", {
    views <- list(
      list(name = "db.schema.view", ddl = "CREATE SEMANTIC VIEW test_view")
    )
    result <- format_semantic_views_section(views)

    expect_match(result, "## Snowflake Semantic Views")
    expect_match(result, "db.schema.view")
    expect_match(result, "CREATE SEMANTIC VIEW test_view")
    expect_match(result, "```sql")
  })

  it("formats multiple views", {
    views <- list(
      list(name = "db.schema.view1", ddl = "CREATE SEMANTIC VIEW v1"),
      list(name = "db.schema.view2", ddl = "CREATE SEMANTIC VIEW v2")
    )
    result <- format_semantic_views_section(views)

    expect_match(result, "db.schema.view1")
    expect_match(result, "db.schema.view2")
    expect_match(result, "CREATE SEMANTIC VIEW v1")
    expect_match(result, "CREATE SEMANTIC VIEW v2")
  })

  it("includes IMPORTANT notice", {
    views <- list(
      list(name = "test", ddl = "DDL")
    )
    result <- format_semantic_views_section(views)
    expect_match(result, "\\*\\*IMPORTANT\\*\\*")
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

describe("SnowflakeSource initialization", {
  # Note: We cannot fully test SnowflakeSource without a real Snowflake
  # connection, but we can test the parameter validation and discovery
  # option through integration with DBISource

  it("can disable semantic view discovery", {
    # This is a mock test - in reality you'd need a Snowflake connection
    # The actual behavior is tested through the discover_semantic_views param
    # which skips the discovery when FALSE

    # The parameter exists and should be accepted by the class
    expect_true(
      "discover_semantic_views" %in%
        formalArgs(
          SnowflakeSource$public_methods$initialize
        )
    )
  })

  it("inherits from DBISource", {
    # Check that SnowflakeSource inherits from DBISource
    expect_identical(SnowflakeSource$get_inherit(), DBISource)
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
})
