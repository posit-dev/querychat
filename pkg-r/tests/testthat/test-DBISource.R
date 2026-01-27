describe("DBISource$new()", {
  it("creates proper R6 object for DBISource", {
    db <- local_sqlite_connection(new_users_df(), "users")

    db_source <- DBISource$new(db$conn, "users")
    expect_s3_class(db_source, "DBISource")
    expect_s3_class(db_source, "DataSource")
    expect_equal(db_source$table_name, "users")
  })

  it("errors with non-DBI connection", {
    expect_snapshot(error = TRUE, {
      DBISource$new(list(fake = "connection"), "test_table")
    })

    expect_snapshot(error = TRUE, {
      DBISource$new(NULL, "test_table")
    })

    expect_snapshot(error = TRUE, {
      DBISource$new("not a connection", "test_table")
    })
  })

  it("errors with invalid table_name types", {
    db <- local_sqlite_connection(new_test_df())

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, 123)
    })

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, c("table1", "table2"))
    })

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, list(name = "table"))
    })
  })

  it("errors when table does not exist", {
    db <- local_sqlite_connection(new_test_df(), "existing_table")

    expect_snapshot(error = TRUE, {
      DBISource$new(db$conn, "non_existent_table")
    })
  })
})

describe("DBISource$test_query()", {
  test_df <- new_users_df()
  db <- local_sqlite_connection(test_df, "test_table")
  dbi_source <- DBISource$new(db$conn, "test_table")

  it("correctly retrieves one row of data", {
    result <- dbi_source$test_query("SELECT * FROM test_table")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$id, 1)

    result <- dbi_source$test_query("SELECT * FROM test_table WHERE age > 29")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$age, 30)

    result <- dbi_source$test_query(
      "SELECT * FROM test_table ORDER BY age DESC"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_equal(result$age, 35)

    result <- dbi_source$test_query(
      "SELECT * FROM test_table WHERE age > 100"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 0)
  })

  it("handles errors correctly", {
    expect_error(dbi_source$test_query("SELECT * WRONG SYNTAX"))

    expect_error(dbi_source$test_query("SELECT * FROM non_existent_table"))

    expect_error(dbi_source$test_query(
      "SELECT non_existent_column FROM test_table"
    ))
  })

  it("works with different data types", {
    db <- local_sqlite_connection(new_types_df(), "types_table")
    dbi_source <- DBISource$new(db$conn, "types_table")

    result <- dbi_source$test_query("SELECT * FROM types_table")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 1)
    expect_type(result$text_col, "character")
    expect_type(result$num_col, "double")
    expect_type(result$int_col, "integer")
    expect_type(result$bool_col, "integer")
  })
})
