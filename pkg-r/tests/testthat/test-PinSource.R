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
