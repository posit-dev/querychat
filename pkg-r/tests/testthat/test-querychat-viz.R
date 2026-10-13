describe("ggsql execution through a caching reader", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("ggsql", minimum_version = "0.5.2.9000")

  it("executes a basic ggsql query", {
    ds <- local_data_frame_source(new_test_df())
    reader <- viz_caching_reader(ds)
    spec <- ggsql::ggsql_execute(
      reader,
      "SELECT * FROM test_table VISUALISE value AS x DRAW histogram"
    )
    expect_s3_class(spec, "Spec")
  })

  it("supports uppercase column references without renaming", {
    df <- data.frame(
      ROOM_TYPE = c("Entire home", "Private room"),
      listings = c(10, 20)
    )
    ds <- local_data_frame_source(df, table_name = "upper_table")
    reader <- viz_caching_reader(ds)
    spec <- ggsql::ggsql_execute(
      reader,
      paste(
        "SELECT ROOM_TYPE, listings FROM upper_table",
        "VISUALISE ROOM_TYPE AS x, listings AS y DRAW bar"
      )
    )
    expect_s3_class(spec, "Spec")
  })

  it("supports FROM before VISUALISE", {
    ds <- local_data_frame_source(new_test_df())
    reader <- viz_caching_reader(ds)
    spec <- ggsql::ggsql_execute(
      reader,
      "FROM test_table VISUALISE value AS x DRAW histogram"
    )
    expect_s3_class(spec, "Spec")
  })

  it("supports layer-level FROM sources", {
    # Previously rejected with "Layer-specific sources are not currently
    # supported"; the caching reader stages each layer source through its
    # private cache, so the query now runs end to end.
    ds <- local_data_frame_source(new_test_df())
    reader <- viz_caching_reader(ds)
    spec <- ggsql::ggsql_execute(
      reader,
      "VISUALISE value AS x DRAW histogram MAPPING value AS x FROM test_table"
    )
    expect_s3_class(spec, "Spec")
  })

  it("supports single-relation raw + summary overlay", {
    df <- data.frame(
      x = c(1, 1, 2, 2),
      y = c(10, 20, 30, 40),
      category = c("a", "b", "a", "b")
    )
    ds <- local_data_frame_source(df, table_name = "sales")
    reader <- viz_caching_reader(ds)
    query <- "
    WITH raw AS (
        SELECT x, y, category, 'raw' AS layer_type FROM sales
    ),
    summary AS (
        SELECT x, AVG(y) AS y, category, 'summary' AS layer_type
        FROM sales GROUP BY x, category
    ),
    combined AS (
        SELECT * FROM raw UNION ALL SELECT * FROM summary
    )
    SELECT * FROM combined
    VISUALISE x AS x, y AS y
    DRAW point MAPPING category AS color FILTER layer_type = 'raw'
    DRAW line MAPPING category AS color FILTER layer_type = 'summary'
    "
    spec <- ggsql::ggsql_execute(reader, query)
    expect_s3_class(spec, "Spec")
    expect_equal(ggsql::ggsql_metadata(spec)$rows, 4)
  })
})

describe("viz caching behavior", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("ggsql", minimum_version = "0.5.2.9000")

  # Wraps a DataFrameSource, counting base reads that reach it.
  counting_executor <- function(ds) {
    env <- new.env(parent = emptyenv())
    env$calls <- 0L
    env$execute_query <- function(sql) {
      env$calls <- env$calls + 1L
      ds$execute_query(sql)
    }
    env
  }

  it("identical queries share memoized source reads through one reader", {
    ds <- local_data_frame_source(new_test_df())
    executor <- counting_executor(ds)
    reader <- viz_caching_reader(executor)

    query <- "SELECT * FROM test_table VISUALISE value AS x DRAW point"
    ggsql::ggsql_execute(reader, query)
    ggsql::ggsql_execute(reader, query)
    expect_equal(executor$calls, 1L)
  })

  it("independent readers do not share memoized reads", {
    # Guards against reintroducing an implicit shared registry: readers own
    # their caches, so two readers over one source each re-read it.
    ds <- local_data_frame_source(new_test_df())
    executor <- counting_executor(ds)

    query <- "SELECT * FROM test_table VISUALISE value AS x DRAW point"
    ggsql::ggsql_execute(viz_caching_reader(executor), query)
    ggsql::ggsql_execute(viz_caching_reader(executor), query)
    expect_equal(executor$calls, 2L)
  })
})
