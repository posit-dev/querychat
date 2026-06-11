local_pin_source <- function(
  board,
  name,
  ...,
  env = parent.frame()
) {
  ps <- PinSource$new(board, name, ...)
  withr::defer(ps$cleanup(), envir = env)
  ps
}

describe("PinSource prerequisites", {
  it("skip if pins or duckdb not installed", {
    skip_if_not_installed("pins")
    skip_if_not_installed("duckdb")
    expect_true(TRUE)
  })
})

describe("PinSource$new() — lazy path (parquet)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("creates proper R6 object for parquet pin", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:10, ], "test_data", type = "parquet")

    ps <- local_pin_source(board, "test_data")

    expect_s3_class(ps, "PinSource")
    expect_s3_class(ps, "DBISource")
    expect_equal(ps$get_db_type(), "DuckDB")
  })

  it("executes queries against parquet pin", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:10, ], "test_data", type = "parquet")

    ps <- local_pin_source(board, "test_data")

    result <- ps$execute_query("SELECT * FROM test_data")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
    expect_equal(ncol(result), ncol(mtcars))
  })

  it("filters parquet pin data correctly", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars, "cars", type = "parquet")

    ps <- local_pin_source(board, "cars")

    result <- ps$execute_query("SELECT * FROM cars WHERE mpg > 30")
    expect_s3_class(result, "data.frame")
    expect_true(all(result$mpg > 30))
  })
})

describe("PinSource$new() — lazy path (csv)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("reads csv pin via DuckDB file reader", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:10, ], "csv_data", type = "csv")

    ps <- local_pin_source(board, "csv_data")

    result <- ps$execute_query("SELECT * FROM csv_data")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
  })

  it("filters csv pin data correctly", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:10, ], "csv_data", type = "csv")

    ps <- local_pin_source(board, "csv_data")

    result <- ps$execute_query("SELECT * FROM csv_data WHERE mpg > 20")
    expect_s3_class(result, "data.frame")
    expect_true(all(result$mpg > 20))
  })
})

describe("PinSource$new() — lazy path (json)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("reads json pin via DuckDB file reader", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:10, ], "json_data", type = "json")

    ps <- local_pin_source(board, "json_data")

    result <- ps$get_data()
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
  })
})

describe("PinSource$new() — in-memory path (rds)", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("reads rds pin into DuckDB", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:10, ], "rds_data", type = "rds")

    ps <- local_pin_source(board, "rds_data")

    result <- ps$execute_query("SELECT * FROM rds_data")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 10)
  })

  it("errors when rds pin contains a non-data-frame object", {
    board <- pins::board_temp()
    pins::pin_write(board, list(a = 1, b = 2), "list_pin", type = "rds")

    expect_error(
      PinSource$new(board, "list_pin"),
      "not a data frame"
    )
  })
})

describe("PinSource$table_name", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("defaults to pin name", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "my_pin", type = "parquet")

    ps <- local_pin_source(board, "my_pin")

    expect_equal(ps$table_name, "my_pin")
  })

  it("can be overridden via table_name argument", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "my_pin", type = "parquet")

    ps <- local_pin_source(board, "my_pin", table_name = "custom_table")

    expect_equal(ps$table_name, "custom_table")
    result <- ps$execute_query("SELECT * FROM custom_table")
    expect_equal(nrow(result), 5)
  })

  it("custom table_name cannot be accessed by pin name", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "my_pin", type = "parquet")

    ps <- local_pin_source(board, "my_pin", table_name = "custom_table")

    expect_error(ps$execute_query("SELECT * FROM my_pin"))
  })
})

describe("PinSource$get_schema()", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("returns a character schema string", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "schema_test", type = "parquet")

    ps <- local_pin_source(board, "schema_test")

    schema <- ps$get_schema()
    expect_type(schema, "character")
  })

  it("schema includes table name", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "schema_test", type = "parquet")

    ps <- local_pin_source(board, "schema_test")

    expect_match(ps$get_schema(), "schema_test")
  })

  it("schema includes column names", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "schema_test", type = "parquet")

    ps <- local_pin_source(board, "schema_test")

    expect_match(ps$get_schema(), "mpg")
    expect_match(ps$get_schema(), "cyl")
  })
})

describe("PinSource$test_query()", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("returns exactly one row", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:10, ], "tq_test", type = "parquet")

    ps <- local_pin_source(board, "tq_test")

    result <- ps$test_query("SELECT * FROM tq_test")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
  })

  it("returns zero rows when query matches nothing", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "tq_test", type = "parquet")

    ps <- local_pin_source(board, "tq_test")

    result <- ps$test_query("SELECT * FROM tq_test WHERE mpg > 9999")
    expect_equal(nrow(result), 0)
  })
})

describe("PinSource$get_data_description()", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("returns a character string", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "minimal_pin", type = "parquet")

    ps <- local_pin_source(board, "minimal_pin")

    expect_type(ps$get_data_description(), "character")
  })

  it("includes title when set", {
    board <- pins::board_temp()
    pins::pin_write(
      board, mtcars[1:5, ], "described_pin",
      type = "parquet",
      title = "Motor Trend Cars"
    )

    ps <- local_pin_source(board, "described_pin")

    expect_match(ps$get_data_description(), "Motor Trend Cars")
  })

  it("includes description when set", {
    board <- pins::board_temp()
    pins::pin_write(
      board, mtcars[1:5, ], "described_pin",
      type = "parquet",
      description = "Performance data for automobiles"
    )

    ps <- local_pin_source(board, "described_pin")

    expect_match(ps$get_data_description(), "Performance data for automobiles")
  })

  it("includes formatted tags when set", {
    board <- pins::board_temp()
    pins::pin_write(
      board, mtcars[1:5, ], "tagged_pin",
      type = "parquet",
      tags = c("cars", "performance")
    )

    ps <- local_pin_source(board, "tagged_pin")

    expect_match(ps$get_data_description(), "Tags: cars, performance")
  })

  it("formats title, description, and tags together", {
    board <- pins::board_temp()
    pins::pin_write(
      board, mtcars[1:5, ], "full_pin",
      type = "parquet",
      title = "Motor Trend Cars",
      description = "Performance data for automobiles",
      tags = c("cars", "performance")
    )

    ps <- local_pin_source(board, "full_pin")

    desc <- ps$get_data_description()
    expect_match(desc, "Motor Trend Cars")
    expect_match(desc, "Performance data for automobiles")
    expect_match(desc, "Tags: cars, performance")
  })

  it("returns a string even when no explicit metadata is set", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "bare_pin", type = "parquet")

    ps <- local_pin_source(board, "bare_pin")

    expect_type(ps$get_data_description(), "character")
  })
})

describe("PinSource DuckDB security lockdown", {
  skip_if_not_installed("pins")
  skip_if_not_installed("duckdb")

  it("blocks external file access after data loading", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "secure_test", type = "parquet")

    ps <- local_pin_source(board, "secure_test")

    expect_error(
      ps$execute_query("SELECT * FROM read_csv_auto('/etc/passwd')")
    )
  })

  it("blocks local filesystem access", {
    board <- pins::board_temp()
    pins::pin_write(board, mtcars[1:5, ], "secure_test2", type = "parquet")

    ps <- local_pin_source(board, "secure_test2")

    expect_error(
      ps$execute_query("SELECT * FROM read_parquet('/tmp/any_file.parquet')")
    )
  })
})
