local_pin_source <- function(
  data = mtcars[1:10, ],
  name = "test_data",
  type = "csv",
  ...,
  table_name = name,
  version = NULL,
  engine = NULL,
  env = parent.frame()
) {
  board <- pins::board_temp()
  suppressMessages(pins::pin_write(board, data, name, type = type, ...))
  ps <- PinSource$new(
    board,
    name,
    table_name = table_name,
    version = version,
    engine = engine
  )
  withr::defer(ps$cleanup(), envir = env)
  ps
}

describe("PinSource$new() — lazy path (parquet)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")
  skip_if_not_installed("nanoparquet")

  it("creates proper R6 object for parquet pin", {
    ps <- local_pin_source(type = "parquet")

    expect_s3_class(ps, "PinSource")
    expect_s3_class(ps, "DBISource")
    expect_equal(ps$get_db_type(), "DuckDB")
  })

  it("executes queries against parquet pin", {
    ps <- local_pin_source(type = "parquet")

    result <- ps$execute_query("SELECT * FROM test_data")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
    expect_equal(ncol(result), ncol(mtcars))
  })

  it("filters parquet pin data correctly", {
    ps <- local_pin_source(data = mtcars, name = "cars", type = "parquet")

    result <- ps$execute_query("SELECT * FROM cars WHERE mpg > 30")
    expect_s3_class(result, "data.frame")
    expect_true(all(result$mpg > 30))
  })
})

describe("PinSource$new() — lazy path (csv)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("reads csv pin via DuckDB file reader", {
    ps <- local_pin_source(name = "csv_data", type = "csv")

    result <- ps$execute_query("SELECT * FROM csv_data")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
  })

  it("filters csv pin data correctly", {
    ps <- local_pin_source(name = "csv_data", type = "csv")

    result <- ps$execute_query("SELECT * FROM csv_data WHERE mpg > 20")
    expect_s3_class(result, "data.frame")
    expect_true(all(result$mpg > 20))
  })
})

describe("PinSource$new() — lazy path (json)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("reads json pin via DuckDB file reader", {
    ps <- local_pin_source(name = "json_data", type = "json")

    result <- ps$get_data()
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
  })
})

describe("PinSource$new() — in-memory path (rds)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("reads rds pin into DuckDB", {
    ps <- local_pin_source(name = "rds_data", type = "rds")

    result <- ps$execute_query("SELECT * FROM rds_data")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
  })

  it("errors when rds pin contains a non-data-frame object", {
    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(board, list(a = 1, b = 2), "list_pin", type = "rds")
    )

    expect_error(
      PinSource$new(board, "list_pin"),
      "not a data frame"
    )
  })
})

describe("PinSource$new() — engine argument", {
  skip_if_not_installed("pins")
  skip_if_not_installed("RSQLite")

  it("uses SQLite for a data-frame (rds) pin", {
    ps <- local_pin_source(name = "rds_data", type = "rds", engine = "sqlite")

    expect_equal(ps$get_db_type(), "SQLite")
    result <- ps$execute_query("SELECT * FROM rds_data")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
  })

  it("warns and falls back to pin_read for a file-type pin", {
    expect_warning(
      ps <- local_pin_source(
        name = "csv_data",
        type = "csv",
        engine = "sqlite"
      ),
      "more efficiently"
    )

    expect_equal(ps$get_db_type(), "SQLite")
    expect_equal(nrow(ps$execute_query("SELECT * FROM csv_data")), 10)
  })
})

describe("PinSource$table_name", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("defaults to pin name", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "my_pin")

    expect_equal(ps$table_name, "my_pin")
  })

  it("can be overridden via table_name argument", {
    ps <- local_pin_source(
      data = mtcars[1:5, ],
      name = "my_pin",
      table_name = "custom_table"
    )

    expect_equal(ps$table_name, "custom_table")
    result <- ps$execute_query("SELECT * FROM custom_table")
    expect_equal(nrow(result), 5)
  })

  it("custom table_name cannot be accessed by pin name", {
    ps <- local_pin_source(
      data = mtcars[1:5, ],
      name = "my_pin",
      table_name = "custom_table"
    )

    expect_error(ps$execute_query("SELECT * FROM my_pin"))
  })
})

describe("PinSource$get_schema()", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("returns a character schema string", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "schema_test")

    schema <- ps$get_schema()
    expect_type(schema, "character")
  })

  it("schema includes table name", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "schema_test")

    expect_match(ps$get_schema(), "schema_test")
  })

  it("schema includes column names", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "schema_test")

    expect_match(ps$get_schema(), "mpg")
    expect_match(ps$get_schema(), "cyl")
  })
})

describe("PinSource$test_query()", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("returns exactly one row", {
    ps <- local_pin_source(name = "tq_test")

    result <- ps$test_query("SELECT * FROM tq_test")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
  })

  it("returns zero rows when query matches nothing", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "tq_test")

    result <- ps$test_query("SELECT * FROM tq_test WHERE mpg > 9999")
    expect_equal(nrow(result), 0)
  })
})

describe("PinSource$get_data_description()", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("returns a character string", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "minimal_pin")

    expect_type(ps$get_data_description(), "character")
  })

  it("includes title when set", {
    ps <- local_pin_source(
      data = mtcars[1:5, ],
      name = "described_pin",
      title = "Motor Trend Cars"
    )

    expect_match(ps$get_data_description(), "Motor Trend Cars")
  })

  it("includes description when set", {
    ps <- local_pin_source(
      data = mtcars[1:5, ],
      name = "described_pin",
      description = "Performance data for automobiles"
    )

    expect_match(ps$get_data_description(), "Performance data for automobiles")
  })

  it("includes formatted tags when set", {
    ps <- local_pin_source(
      data = mtcars[1:5, ],
      name = "tagged_pin",
      tags = c("cars", "performance")
    )

    expect_match(ps$get_data_description(), "Tags: cars, performance")
  })

  it("formats title, description, and tags together", {
    ps <- local_pin_source(
      data = mtcars[1:5, ],
      name = "full_pin",
      title = "Motor Trend Cars",
      description = "Performance data for automobiles",
      tags = c("cars", "performance")
    )

    desc <- ps$get_data_description()
    expect_match(desc, "Motor Trend Cars")
    expect_match(desc, "Performance data for automobiles")
    expect_match(desc, "Tags: cars, performance")
  })

  it("returns a string even when no explicit metadata is set", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "bare_pin")

    expect_type(ps$get_data_description(), "character")
  })
})

describe("PinSource$new() — error paths", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")
  skip_if_not_installed("nanoparquet")

  it("rejects multi-file pins", {
    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(board, mtcars[1:5, ], "multi_pin", type = "parquet")
    )

    local_mocked_bindings(
      pin_download = function(...) c("/fake/a.parquet", "/fake/b.parquet"),
      .package = "pins"
    )
    expect_error(
      PinSource$new(board, "multi_pin"),
      "contains 2 files"
    )
  })
})

describe("PinSource DuckDB security lockdown", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("blocks external file access after data loading", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "secure_test")

    expect_error(
      ps$execute_query("SELECT * FROM read_csv_auto('/etc/passwd')")
    )
  })

  it("blocks local filesystem access", {
    ps <- local_pin_source(data = mtcars[1:5, ], name = "secure_test")

    expect_error(
      ps$execute_query("SELECT * FROM read_parquet('/tmp/any_file.parquet')")
    )
  })
})

describe("QueryChat + PinSource integration", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("auto-fills data_description from pin metadata", {
    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(
        board,
        mtcars[1:5, ],
        "cars",
        type = "csv",
        title = "Motor Trend Cars",
        description = "Road test data"
      )
    )
    ps <- PinSource$new(board, "cars")
    qc <- QueryChat$new(data_source = ps, table_name = "cars", greeting = "Hi")
    withr::defer(qc$cleanup())

    prompt <- qc$system_prompt
    expect_match(prompt, "Motor Trend Cars")
    expect_match(prompt, "Road test data")
  })

  it("explicit data_description overrides pin metadata", {
    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(
        board,
        mtcars[1:5, ],
        "cars",
        type = "csv",
        title = "Motor Trend Cars"
      )
    )
    ps <- PinSource$new(board, "cars")
    qc <- QueryChat$new(
      data_source = ps,
      table_name = "cars",
      greeting = "Hi",
      data_description = "Custom description"
    )
    withr::defer(qc$cleanup())

    prompt <- qc$system_prompt
    expect_match(prompt, "Custom description")
    expect_no_match(prompt, "Motor Trend Cars")
  })

  it("clears auto-filled description when switching data source", {
    skip_if_no_dataframe_engine()

    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(
        board,
        mtcars[1:5, ],
        "cars",
        type = "csv",
        title = "Motor Trend Cars"
      )
    )
    ps <- PinSource$new(board, "cars")
    qc <- QueryChat$new(data_source = ps, table_name = "cars", greeting = "Hi")

    prompt_before <- qc$system_prompt
    expect_match(prompt_before, "Motor Trend Cars")

    qc$add_table(new_test_df(), 'cars', replace = TRUE)
    prompt_after <- qc$system_prompt
    expect_no_match(prompt_after, "Motor Trend Cars")

    qc$cleanup()
  })
})

test_that("PinSource$cleanup() disconnects the connection it opened", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")
  skip_if_not_installed("nanoparquet")

  ps <- local_pin_source(type = "parquet")
  conn <- ps$conn

  ps$cleanup()

  expect_false(DBI::dbIsValid(conn))
})

describe("PinSource multi-table support", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")
  skip_if_not_installed("nanoparquet")

  it("accepts a second pin via check_source_compatibility", {
    ps1 <- local_pin_source(name = "pin_a", type = "parquet")
    ps2 <- local_pin_source(name = "pin_b", type = "parquet")

    expect_no_error(
      check_source_compatibility(list(pin_a = ps1), ps2, "pin_b")
    )
  })

  it("queries across two pins through a shared DuckDB executor", {
    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(
        board,
        data.frame(id = 1:3, x = c(10, 20, 30)),
        "pin_a",
        type = "parquet"
      )
    )
    suppressMessages(
      pins::pin_write(
        board,
        data.frame(id = 1:3, y = c("a", "b", "c")),
        "pin_b",
        type = "csv"
      )
    )

    qc <- QueryChat$new(board, "pin_a")
    withr::defer(qc$cleanup())
    qc$add_table(board, "pin_b")

    executor <- qc$.__enclos_env__$private$.table_set$executor()
    expect_s3_class(executor, "DuckDBExecutor")

    joined <- executor$execute_query(
      "SELECT a.x, b.y FROM pin_a a JOIN pin_b b ON a.id = b.id ORDER BY a.id"
    )
    expect_equal(joined$x, c(10, 20, 30))
    expect_equal(joined$y, c("a", "b", "c"))

    # Per-table schema and validation work for both pins
    schema <- executor$get_schema("pin_b", categorical_threshold = 20)
    expect_match(schema, "Table: pin_b")
    expect_no_error(
      executor$test_query(
        "SELECT * FROM pin_b",
        "pin_b",
        require_all_columns = TRUE
      )
    )
  })

  it("mixes pins and data frames in one executor", {
    ps1 <- local_pin_source(name = "pin_a", type = "parquet")
    df_source <- local_data_frame_source(new_test_df(), "test")

    executor <- build_query_executor(list(pin_a = ps1, test = df_source))
    withr::defer(executor$cleanup())

    expect_s3_class(executor, "DuckDBExecutor")
    result <- executor$execute_query(
      "SELECT COUNT(*) AS n FROM pin_a CROSS JOIN test"
    )
    expect_equal(result$n, 10 * nrow(new_test_df()))
  })

  it("materializes the snapshotted version on versioned boards", {
    board <- pins::board_temp(versioned = TRUE)
    suppressMessages(
      pins::pin_write(board, data.frame(x = 1:4), "pin_a", type = "parquet")
    )
    ps1 <- PinSource$new(board, "pin_a")
    withr::defer(ps1$cleanup())
    ps2 <- local_pin_source(name = "pin_b", type = "parquet")

    # New version of pin_a published after its PinSource was built
    suppressMessages(
      pins::pin_write(board, data.frame(x = 1), "pin_a", type = "parquet")
    )

    executor <- build_query_executor(list(pin_a = ps1, pin_b = ps2))
    withr::defer(executor$cleanup())

    expect_equal(nrow(executor$execute_query("SELECT * FROM pin_a")), 4)
  })

  it("falls back to the source's copy when the snapshot version is pruned", {
    # Non-versioned boards drop the old version on rewrite, so the version
    # snapshotted at construction no longer exists at registration time.
    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(board, data.frame(x = 1:4), "pin_a", type = "parquet")
    )
    ps1 <- PinSource$new(board, "pin_a")
    withr::defer(ps1$cleanup())
    ps2 <- local_pin_source(name = "pin_b", type = "parquet")

    suppressMessages(
      pins::pin_write(board, data.frame(x = 1), "pin_a", type = "parquet")
    )

    executor <- build_query_executor(list(pin_a = ps1, pin_b = ps2))
    withr::defer(executor$cleanup())

    expect_equal(nrow(executor$execute_query("SELECT * FROM pin_a")), 4)
  })

  it("leaves pin connections open when the executor is cleaned up", {
    ps1 <- local_pin_source(name = "pin_a", type = "parquet")
    ps2 <- local_pin_source(name = "pin_b", type = "parquet")
    executor <- build_query_executor(list(pin_a = ps1, pin_b = ps2))

    # The shared connection is executor-owned; pins keep their own.
    executor$cleanup()

    expect_true(DBI::dbIsValid(ps1$conn))
    expect_true(DBI::dbIsValid(ps2$conn))
    expect_equal(nrow(ps2$execute_query("SELECT * FROM pin_b")), 10)
  })

  it("rejects adding a sqlite-engine pin to a multi-table group", {
    skip_if_not_installed("RSQLite")
    ps1 <- local_pin_source(name = "pin_a", type = "parquet")
    ps_sqlite <- suppressWarnings(
      local_pin_source(name = "pin_b", engine = "sqlite")
    )

    expect_error(
      check_source_compatibility(list(pin_a = ps1), ps_sqlite, "pin_b"),
      "engine = \"sqlite\""
    )
  })

  it("rejects adding any table when an existing pin uses sqlite", {
    skip_if_not_installed("RSQLite")
    ps_sqlite <- suppressWarnings(
      local_pin_source(name = "pin_a", engine = "sqlite")
    )
    df_source <- local_data_frame_source(new_test_df(), "test")

    expect_error(
      check_source_compatibility(list(pin_a = ps_sqlite), df_source, "test"),
      "engine = \"sqlite\""
    )
  })

  it("QueryChat$add_table() accepts a second pin", {
    board <- pins::board_temp()
    suppressMessages(
      pins::pin_write(board, mtcars[1:5, ], "pin_a", type = "parquet")
    )
    suppressMessages(
      pins::pin_write(board, mtcars[1:5, ], "pin_b", type = "parquet")
    )

    qc <- QueryChat$new(board, "pin_a")
    withr::defer(qc$cleanup())

    expect_no_error(qc$add_table(board, "pin_b"))
  })
})
