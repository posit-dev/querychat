describe("QueryChat$new()", {
  test_df <- new_test_df(3)

  it("automatically converts data.frame to DataFrameSource", {
    qc <- QueryChat$new(
      data_source = test_df,
      table_name = "test_df",
      greeting = "Test greeting"
    )
    withr::defer(qc$cleanup())

    expect_s3_class(qc$data_source, "DataSource")
    expect_s3_class(qc$data_source, "DataFrameSource")
  })

  it("accepts DataFrameSource directly", {
    df_source <- local_data_frame_source(test_df, "test_source")

    qc <- QueryChat$new(
      data_source = df_source,
      table_name = "test_source",
      greeting = "Test greeting"
    )

    expect_s3_class(qc$data_source, "DataFrameSource")
    expect_equal(qc$data_source$table_name, "test_source")
  })

  it("accepts DBISource", {
    db <- local_sqlite_connection(test_df)
    dbi_source <- DBISource$new(db$conn, "test_table")

    qc <- QueryChat$new(
      data_source = dbi_source,
      table_name = "test_table",
      greeting = "Test greeting"
    )

    expect_s3_class(qc$data_source, "DBISource")
    expect_equal(qc$data_source$table_name, "test_table")
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
