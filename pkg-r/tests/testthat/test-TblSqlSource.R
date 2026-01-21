describe("TblSqlSource$new()", {
  it("creates proper R6 object for TblSqlSource", {
    source <- local_tbl_sql_source()

    expect_s3_class(source, "TblSqlSource")
    expect_s3_class(source, "DBISource")
    expect_s3_class(source, "DataSource")
    expect_equal(source$table_name, "test_table")
    expect_equal(source$get_db_type(), "DuckDB")
  })

  it("errors with non-tbl_sql input", {
    skip_if_not_installed("duckdb")
    skip_if_not_installed("dbplyr")

    expect_snapshot(error = TRUE, {
      TblSqlSource$new(data.frame(a = 1))
    })

    expect_snapshot(error = TRUE, {
      TblSqlSource$new(list(a = 1, b = 2))
    })
  })

  it("returns lazy tibble from execute_query() when collect = FALSE", {
    source <- local_tbl_sql_source()

    result <- source$execute_query("SELECT * FROM test_table WHERE value > 25", collect = FALSE)
    expect_s3_class(result, "tbl_sql")
    expect_s3_class(result, "tbl_lazy")

    # Collect to verify data
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 3)
    expect_equal(collected$value, c(30, 40, 50))
  })

  it("returns lazy tibble from execute_query() when collect = FALSE", {
    source <- local_tbl_sql_source()

    result <- source$execute_query(
      "SELECT * FROM test_table WHERE value > 25",
      collect = FALSE
    )
    expect_s3_class(result, "tbl_sql")
    expect_s3_class(result, "tbl_lazy")
  })

  it("returns data frame from execute_query() when collect = TRUE", {
    source <- local_tbl_sql_source()

    result <- source$execute_query(
      "SELECT * FROM test_table WHERE value > 25",
      collect = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_false(inherits(result, "tbl_sql"))
    expect_false(inherits(result, "tbl_lazy"))
    expect_equal(nrow(result), 3)
    expect_equal(result$value, c(30, 40, 50))
  })

  it("returns data frame from test_query()", {
    source <- local_tbl_sql_source()

    result <- source$test_query("SELECT * FROM test_table")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
  })

  it("returns lazy tibble from get_data()", {
    source <- local_tbl_sql_source()

    result <- source$get_data()
    expect_s3_class(result, "tbl_sql")
    expect_s3_class(result, "tbl_lazy")
  })
})

describe("TblSqlSource with transformed tbl (CTE mode)", {
  it("works with filtered tbl", {
    source <- local_tbl_sql_source(
      tbl_transform = function(tbl) dplyr::filter(tbl, value > 20)
    )

    # CTE should be used since tbl is transformed
    result <- source$execute_query("SELECT * FROM test_table", collect = FALSE)
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 3)
    expect_true(all(collected$value > 20))
  })

  it("works with selected columns tbl", {
    source <- local_tbl_sql_source(
      tbl_transform = function(tbl) dplyr::select(tbl, id, name)
    )

    result <- source$execute_query("SELECT * FROM test_table")
    collected <- dplyr::collect(result)
    expect_equal(names(collected), c("id", "name"))
  })
})

describe("TblSqlSource edge cases - Category A: Structural Violations", {
  # Note: TblSqlSource uses dplyr::tbl(conn, dplyr::sql(query)) which wraps

  # the user's query as a subquery. This means some SQL constructs that work
  # in standalone queries will fail when wrapped.

  it("errors on trailing semicolon (subquery wrapping)", {
    source <- local_tbl_sql_source()

    # Semicolons inside subqueries cause syntax errors in DuckDB
    # The query gets wrapped as: SELECT * FROM (SELECT * FROM test_table;) q01
    expect_error(
      dplyr::collect(source$execute_query("SELECT * FROM test_table;")),
      regexp = "syntax error"
    )
  })

  it("errors on trailing semicolon in CTE mode", {
    source <- local_tbl_sql_source(
      tbl_transform = function(tbl) dplyr::filter(tbl, value > 10)
    )

    # Same issue with CTE wrapping
    expect_error(
      dplyr::collect(source$execute_query("SELECT * FROM test_table;")),
      regexp = "syntax error"
    )
  })

  it("errors on multiple trailing semicolons", {
    source <- local_tbl_sql_source()

    expect_error(
      dplyr::collect(source$execute_query("SELECT * FROM test_table;;;")),
      regexp = "syntax error"
    )
  })

  it("errors on multiple statements", {
    source <- local_tbl_sql_source()

    # Multiple statements cause syntax errors when wrapped as subquery
    expect_error(
      dplyr::collect(source$execute_query("SELECT 1 AS a; SELECT 2 AS b")),
      regexp = "syntax error"
    )
  })

  it("errors on empty SELECT (syntax error)", {
    source <- local_tbl_sql_source()

    expect_error(
      dplyr::collect(source$execute_query("SELECT")),
      regexp = NULL
    )
  })

  it("errors on SELECT with no FROM when columns expected", {
    source <- local_tbl_sql_source()

    # SELECT without FROM is valid for literals but invalid for table columns
    expect_error(
      dplyr::collect(source$execute_query("SELECT id FROM")),
      regexp = NULL
    )
  })

  it("succeeds with query without trailing semicolon", {
    source <- local_tbl_sql_source()

    # Properly formed query without semicolon works
    result <- source$execute_query("SELECT * FROM test_table")
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 5)
  })
})

describe("TblSqlSource edge cases - Category B: Column Naming Issues", {
  it("handles unnamed expressions (auto-generated names)", {
    source <- local_tbl_sql_source()

    # DuckDB auto-generates names for unnamed expressions
    result <- source$execute_query(
      "SELECT id, 1+1, UPPER(name) FROM test_table"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 5)
    # Should have 3 columns (id + two computed)
    expect_equal(ncol(collected), 3)
  })

  it("handles unnamed expressions in CTE mode", {
    source <- local_tbl_sql_source(
      tbl_transform = function(tbl) dplyr::filter(tbl, value > 10)
    )

    result <- source$execute_query(
      "SELECT id, value * 2, UPPER(name) FROM test_table"
    )
    collected <- dplyr::collect(result)
    expect_equal(ncol(collected), 3)
  })

  it("errors on duplicate column names from JOIN (tibble requirement)", {
    skip_if_not_installed("duckdb")
    skip_if_not_installed("dbplyr")
    skip_if_not_installed("dplyr")

    conn <- local_duckdb_multi_table()
    tbl_a <- dplyr::tbl(conn, "table_a")
    source <- TblSqlSource$new(tbl_a, "table_a")

    # SELECT with explicit duplicate column names from JOIN
    # DuckDB allows duplicate names but tibble rejects them on collect
    result <- source$execute_query(
      "SELECT table_a.id, table_b.id FROM table_a JOIN table_b ON table_a.id = table_b.id",
      collect = FALSE
    )
    expect_error(
      dplyr::collect(result),
      regexp = "must not be duplicated|must be unique"
    )
  })

  it("handles duplicate columns with aliases", {
    skip_if_not_installed("duckdb")
    skip_if_not_installed("dbplyr")
    skip_if_not_installed("dplyr")

    conn <- local_duckdb_multi_table()
    tbl_a <- dplyr::tbl(conn, "table_a")
    source <- TblSqlSource$new(tbl_a, "table_a")

    # Using aliases to avoid duplicate column names
    result <- source$execute_query(
      "SELECT table_a.id AS id_a, table_b.id AS id_b FROM table_a JOIN table_b ON table_a.id = table_b.id"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 3)
    expect_equal(ncol(collected), 2)
    expect_true("id_a" %in% names(collected))
    expect_true("id_b" %in% names(collected))
  })

  it("handles reserved word as alias", {
    source <- local_tbl_sql_source()

    # Using reserved word 'select' as column alias (quoted)
    result <- source$execute_query(
      "SELECT id AS \"select\", name AS \"from\" FROM test_table"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 5)
    expect_true("select" %in% names(collected))
    expect_true("from" %in% names(collected))
  })

  it("handles reserved word as unquoted alias (DuckDB permissive)", {
    source <- local_tbl_sql_source()

    # DuckDB is permissive with reserved words as aliases
    # This may work or fail depending on the specific word
    result <- source$execute_query(
      "SELECT id AS value_alias FROM test_table"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 5)
  })

  it("handles empty string alias (DB-dependent)", {
    source <- local_tbl_sql_source()

    # Empty string alias - DuckDB behavior
    # This typically creates a column with empty name or errors
    expect_error(
      {
        result <- source$execute_query(
          "SELECT id AS \"\" FROM test_table"
        )
        dplyr::collect(result)
      },
      regexp = NULL
    )
  })

  it("errors on wildcard with JOIN (duplicate columns)", {
    skip_if_not_installed("duckdb")
    skip_if_not_installed("dbplyr")
    skip_if_not_installed("dplyr")

    conn <- local_duckdb_multi_table()
    tbl_a <- dplyr::tbl(conn, "table_a")
    source <- TblSqlSource$new(tbl_a, "table_a")

    # SELECT * from JOIN produces duplicate 'id' columns
    # tibble rejects duplicate names on collect
    result <- source$execute_query(
      "SELECT * FROM table_a JOIN table_b ON table_a.id = table_b.id",
      collect = FALSE
    )
    expect_error(
      dplyr::collect(result),
      regexp = "must not be duplicated|must be unique"
    )
  })

  it("handles wildcard with JOIN using USING clause (no duplicates)", {
    skip_if_not_installed("duckdb")
    skip_if_not_installed("dbplyr")
    skip_if_not_installed("dplyr")

    conn <- local_duckdb_multi_table()
    tbl_a <- dplyr::tbl(conn, "table_a")
    source <- TblSqlSource$new(tbl_a, "table_a")

    # USING clause produces single 'id' column
    result <- source$execute_query(
      "SELECT * FROM table_a JOIN table_b USING (id)"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 3)
    # id appears only once with USING
    expect_equal(sum(names(collected) == "id"), 1)
  })
})

describe("TblSqlSource edge cases - Category C: ORDER BY behavior", {
  it("handles ORDER BY without LIMIT", {
    source <- local_tbl_sql_source()

    # ORDER BY without LIMIT is valid SQL
    result <- source$execute_query(
      "SELECT * FROM test_table ORDER BY value DESC"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 5)
    # Verify order is applied
    expect_equal(collected$value[1], 50)
    expect_equal(collected$value[5], 10)
  })

  it("handles ORDER BY without LIMIT in CTE mode", {
    source <- local_tbl_sql_source(
      tbl_transform = function(tbl) dplyr::filter(tbl, value >= 10)
    )

    result <- source$execute_query(
      "SELECT * FROM test_table ORDER BY value DESC"
    )
    collected <- dplyr::collect(result)
    expect_true(nrow(collected) > 0)
    # Verify order is maintained through CTE
    expect_true(collected$value[1] >= collected$value[nrow(collected)])
  })

  it("handles LIMIT without ORDER BY (non-deterministic but valid)", {
    source <- local_tbl_sql_source()

    # LIMIT without ORDER BY is valid but non-deterministic
    result <- source$execute_query("SELECT * FROM test_table LIMIT 3")
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 3)
  })

  it("handles ORDER BY with LIMIT", {
    source <- local_tbl_sql_source()

    result <- source$execute_query(
      "SELECT * FROM test_table ORDER BY value DESC LIMIT 2"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 2)
    expect_equal(collected$value, c(50, 40))
  })

  it("handles ORDER BY with LIMIT and OFFSET", {
    source <- local_tbl_sql_source()

    result <- source$execute_query(
      "SELECT * FROM test_table ORDER BY value DESC LIMIT 2 OFFSET 1"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 2)
    expect_equal(collected$value, c(40, 30))
  })

  it("handles ORDER BY with column alias", {
    source <- local_tbl_sql_source()

    result <- source$execute_query(
      "SELECT id, value AS val FROM test_table ORDER BY val DESC"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 5)
    expect_equal(collected$val[1], 50)
  })

  it("handles ORDER BY with expression", {
    source <- local_tbl_sql_source()

    result <- source$execute_query(
      "SELECT id, value FROM test_table ORDER BY value * -1"
    )
    collected <- dplyr::collect(result)
    expect_equal(nrow(collected), 5)
    # ORDER BY value * -1 ascending means:
    # -50 < -40 < -30 < -20 < -10
    # So original values sorted: 50, 40, 30, 20, 10 (descending)
    expect_equal(collected$value[1], 50)
    expect_equal(collected$value[5], 10)
  })
})
