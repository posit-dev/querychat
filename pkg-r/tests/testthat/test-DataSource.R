describe("DataSource base class", {
  it("throws not_implemented_error for all abstract methods", {
    # Create a base DataSource object (shouldn't be done in practice)
    base_source <- DataSource$new()

    expect_snapshot(error = TRUE, {
      base_source$get_db_type()
    })

    expect_snapshot(error = TRUE, {
      base_source$get_schema()
    })

    expect_snapshot(error = TRUE, {
      base_source$execute_query("SELECT * FROM test")
    })

    expect_snapshot(error = TRUE, {
      base_source$test_query("SELECT * FROM test LIMIT 1")
    })

    expect_snapshot(error = TRUE, {
      base_source$get_data()
    })

    expect_snapshot(error = TRUE, {
      base_source$cleanup()
    })
  })
})

describe("DataSource$get_schema()", {
  it("returns proper schema for DataFrameSource", {
    skip_if_no_dataframe_engine()

    df_source <- local_data_frame_source(new_mixed_types_df())

    schema <- df_source$get_schema()
    expect_type(schema, "character")
    expect_match(schema, "Table: test_table")
    expect_match(schema, "id \\(INTEGER\\)")
    expect_match(schema, "name \\(TEXT\\)")
    expect_match(schema, "active \\(BOOLEAN\\)")
    expect_match(schema, "Categorical values")

    expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
  })

  it("returns proper schema for DBISource", {
    db <- local_sqlite_connection(new_test_df())

    dbi_source <- DBISource$new(db$conn, "test_table")
    schema <- dbi_source$get_schema()
    expect_type(schema, "character")
    expect_match(schema, "Table: `test_table`")
    expect_match(schema, "id \\(INTEGER\\)")
    expect_match(schema, "name \\(TEXT\\)")

    expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
  })

  it("correctly reports min/max values for numeric columns", {
    skip_if_no_dataframe_engine()

    df_source <- local_data_frame_source(new_metrics_df())

    schema <- df_source$get_schema()

    expect_match(schema, "- id \\(INTEGER\\)\\n  Range: 1 to 5")
    expect_match(schema, "- score \\(FLOAT\\)\\n  Range: 10\\.5 to 30\\.1")
    expect_match(schema, "- count \\(FLOAT\\)\\n  Range: 50 to 200")
  })
})

describe("DataSource$get_db_type()", {
  it("returns correct database type for DataFrameSource", {
    skip_if_no_dataframe_engine()

    df_source <- local_data_frame_source(new_test_df())
    db_type <- df_source$get_db_type()
    expect_true(db_type %in% c("DuckDB", "SQLite"))
  })

  it("returns correct type for SQLite connections", {
    skip_if_not_installed("RSQLite")

    db <- local_sqlite_connection(new_test_df())
    db_source <- DBISource$new(db$conn, "test_table")

    expect_equal(db_source$get_db_type(), "SQLite")
  })
})

describe("DataSource$get_data()", {
  test_df <- new_test_df()

  it("returns all data for both DataFrameSource and DBISource", {
    skip_if_no_dataframe_engine()
    skip_if_not_installed("RSQLite")

    df_source <- local_data_frame_source(test_df)

    result <- df_source$get_data()
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 5)
    expect_equal(ncol(result), 3)

    db <- local_sqlite_connection(test_df)

    dbi_source <- DBISource$new(db$conn, "test_table")
    result <- dbi_source$get_data()
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 5)
    expect_equal(ncol(result), 3)
  })
})

describe("DataSource$execute_query()", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("RSQLite")

  test_df <- new_test_df(rows = 4)
  df_source <- local_data_frame_source(test_df)
  db <- local_sqlite_connection(test_df)
  dbi_source <- DBISource$new(db$conn, "test_table")

  it("executes queries for DataFrameSource", {
    result <- df_source$execute_query(
      "SELECT * FROM test_table WHERE value > 25"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
  })

  it("executes queries for DBISource", {
    result <- dbi_source$execute_query(
      "SELECT * FROM test_table WHERE value > 25"
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
  })

  it("handles empty and null queries for DataFrameSource", {
    result_null <- df_source$execute_query(NULL)
    expect_equal(result_null, test_df)

    result_empty <- df_source$execute_query("")
    expect_equal(result_empty, test_df)
  })

  it("handles empty and null queries for DBISource", {
    result_null <- dbi_source$execute_query(NULL)
    expect_equal(result_null, test_df)

    result_empty <- dbi_source$execute_query("")
    expect_equal(result_empty, test_df)
  })

  it("handles filter and sort queries in DBISource", {
    test_users_df <- new_users_df()
    db <- local_sqlite_connection(test_users_df, "users")

    db_source <- DBISource$new(db$conn, "users")

    result <- db_source$execute_query("SELECT * FROM users WHERE age > 30")
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(result$name, c("Charlie", "Eve"))

    all_data <- db_source$execute_query(NULL)
    expect_equal(all_data, test_users_df)

    ordered_result <- db_source$execute_query(
      "SELECT * FROM users ORDER BY age DESC"
    )
    expect_equal(ordered_result$name[1], "Charlie")
  })

  it("handles SQL with inline comments", {
    inline_comment_query <- "
    SELECT id, value -- This is a comment
    FROM test_table
    WHERE value > 25 -- Filter for higher values
    "

    result <- df_source$execute_query(inline_comment_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    multiple_comments_query <- "
    SELECT -- Get only these columns
      id, -- ID column
      value -- Value column
    FROM test_table -- Our test table
    WHERE value > 25 -- Only higher values
    "

    result <- df_source$execute_query(multiple_comments_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with multiline comments", {
    multiline_comment_query <- "
    /*
     * This is a multiline comment
     * that spans multiple lines
     */
    SELECT id, value
    FROM test_table
    WHERE value > 25
    "

    result <- df_source$execute_query(multiline_comment_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    embedded_multiline_query <- "
    SELECT id, /* comment between columns */ value
    FROM /* this is
         * a multiline
         * comment
         */ test_table
    WHERE value /* another comment */ > 25
    "

    result <- df_source$execute_query(embedded_multiline_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with trailing semicolons", {
    query_with_semicolon <- "
    SELECT id, value
    FROM test_table
    WHERE value > 25;
    "

    result <- df_source$execute_query(query_with_semicolon)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    query_with_multiple_semicolons <- "
    SELECT id, value
    FROM test_table
    WHERE value > 25;;;;
    "

    result <- df_source$execute_query(query_with_multiple_semicolons)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with mixed comments and semicolons", {
    complex_query <- "
    /*
     * This is a complex query with different comment styles
     */
    SELECT
      id, -- This is the ID column
      value /* Value column */
    FROM
      test_table -- Our test table
    WHERE
      /* Only get higher values */
      value > 25; -- End of query
    "

    result <- df_source$execute_query(complex_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)

    tricky_comment_query <- "
    SELECT id, value
    FROM test_table
    /* Comment with SQL-like syntax:
     * SELECT * FROM another_table;
     */
    WHERE value > 25 -- WHERE id = 'value; DROP TABLE test;'
    "

    result <- df_source$execute_query(tricky_comment_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })

  it("handles SQL with unusual whitespace patterns", {
    unusual_whitespace_query <- "

       SELECT   id,    value

      FROM     test_table

      WHERE    value>25

    "

    result <- df_source$execute_query(unusual_whitespace_query)
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 2)
    expect_equal(ncol(result), 2)
  })
})

describe("test_query() column validation", {
  skip_if_no_dataframe_engine()

  it("allows all columns through, regardless of order", {
    source <- local_data_frame_source(new_test_df())

    # Should succeed with all columns
    result <- source$test_query(
      "SELECT * FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), c("id", "name", "value"))

    # Should succeed with all columns in different order
    result <- source$test_query(
      "SELECT value, id, name FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(sort(names(result)), c("id", "name", "value"))
  })

  it("allows additional computed columns when require_all_columns=TRUE", {
    source <- local_data_frame_source(new_test_df())

    # Should succeed with all columns plus computed columns
    result <- source$test_query(
      "SELECT *, value * 2 as doubled FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_true(all(c("id", "name", "value", "doubled") %in% names(result)))
  })

  it("fails when columns are missing and require_all_columns=TRUE", {
    source <- local_data_frame_source(new_test_df())

    # Should fail when missing one column
    expect_error(
      source$test_query(
        "SELECT id, name FROM test_table",
        require_all_columns = TRUE
      ),
      class = "querychat_missing_columns_error"
    )

    # Should fail when missing multiple columns
    expect_error(
      source$test_query(
        "SELECT id FROM test_table",
        require_all_columns = TRUE
      ),
      class = "querychat_missing_columns_error"
    )
  })

  it("does not validate when require_all_columns=FALSE (default)", {
    source <- local_data_frame_source(new_test_df())

    # Should succeed with subset of columns when not validating
    result <- source$test_query("SELECT id FROM test_table")
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), "id")

    result <- source$test_query(
      "SELECT id FROM test_table",
      require_all_columns = FALSE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), "id")
  })

  it("provides helpful error message listing missing columns", {
    source <- local_data_frame_source(new_test_df())

    expect_snapshot(error = TRUE, {
      source$test_query(
        "SELECT id FROM test_table",
        require_all_columns = TRUE
      )
    })

    expect_snapshot(error = TRUE, {
      source$test_query(
        "SELECT id, name FROM test_table",
        require_all_columns = TRUE
      )
    })
  })

  it("works with DBISource as well", {
    db <- local_sqlite_connection(new_test_df(), "test_table")
    source <- DBISource$new(db$conn, "test_table")

    # Should succeed with all columns
    result <- source$test_query(
      "SELECT * FROM test_table",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(names(result), c("id", "name", "value"))

    # Should fail when missing columns
    expect_error(
      source$test_query(
        "SELECT id FROM test_table",
        require_all_columns = TRUE
      ),
      class = "querychat_missing_columns_error"
    )
  })

  it("handles empty result sets correctly", {
    source <- local_data_frame_source(new_test_df())

    # Query with no matches should still validate columns
    result <- source$test_query(
      "SELECT * FROM test_table WHERE id > 999",
      require_all_columns = TRUE
    )
    expect_s3_class(result, "data.frame")
    expect_equal(nrow(result), 0)
    expect_equal(names(result), c("id", "name", "value"))
  })
})

describe("check_query() blocks dangerous operations", {
  skip_if_no_dataframe_engine()

  df_source <- local_data_frame_source(new_test_df())

  it("allows valid SELECT queries", {
    expect_no_error(check_query("SELECT * FROM test_table"))
    expect_no_error(check_query("select * from test_table"))
    expect_no_error(check_query("  SELECT * FROM test_table  "))
    expect_no_error(check_query("\nSELECT * FROM test_table\n"))
  })

  it("blocks always-blocked keywords", {
    always_blocked <- c(
      "DELETE",
      "TRUNCATE",
      "CREATE",
      "DROP",
      "ALTER",
      "GRANT",
      "REVOKE",
      "EXEC",
      "EXECUTE",
      "CALL"
    )

    for (keyword in always_blocked) {
      expect_error(
        check_query(paste(keyword, "something")),
        regexp = "disallowed operation",
        info = paste("Failed for keyword:", keyword)
      )
    }
  })

  it("blocks update keywords by default", {
    update_keywords <- c("INSERT", "UPDATE", "MERGE", "REPLACE", "UPSERT")

    for (keyword in update_keywords) {
      expect_error(
        check_query(paste(keyword, "something")),
        regexp = "update operation",
        info = paste("Failed for keyword:", keyword)
      )
    }
  })

  it("normalizes whitespace and case", {
    expect_error(check_query("  delete   FROM table  "), regexp = "disallowed")
    expect_error(check_query("\n\nDELETE\n\nFROM table"), regexp = "disallowed")
    expect_error(check_query("\tDELETE\tFROM\ttable"), regexp = "disallowed")
    expect_error(check_query("DeLeTe FROM table"), regexp = "disallowed")
  })

  it("escape hatch via option enables update keywords", {
    withr::local_options(querychat.enable_update_queries = TRUE)

    expect_no_error(check_query("INSERT INTO table VALUES (1)"))
    expect_no_error(check_query("UPDATE table SET x = 1"))
    expect_no_error(check_query("MERGE INTO table USING"))
    expect_no_error(check_query("REPLACE INTO table VALUES (1)"))
    expect_no_error(check_query("UPSERT INTO table VALUES (1)"))
  })

  it("escape hatch via envvar enables update keywords", {
    withr::local_envvar(QUERYCHAT_ENABLE_UPDATE_QUERIES = "true")

    expect_no_error(check_query("INSERT INTO table VALUES (1)"))
    expect_no_error(check_query("UPDATE table SET x = 1"))

    # Also accepts other truthy values
    withr::local_envvar(QUERYCHAT_ENABLE_UPDATE_QUERIES = "1")
    expect_no_error(check_query("INSERT INTO table VALUES (1)"))

    withr::local_envvar(QUERYCHAT_ENABLE_UPDATE_QUERIES = "YES")
    expect_no_error(check_query("INSERT INTO table VALUES (1)"))
  })

  it("escape hatch does NOT enable always-blocked keywords", {
    withr::local_options(querychat.enable_update_queries = TRUE)

    expect_error(check_query("DELETE FROM table"), regexp = "disallowed")
    expect_error(check_query("DROP TABLE table"), regexp = "disallowed")
    expect_error(check_query("TRUNCATE TABLE table"), regexp = "disallowed")
  })

  it("is integrated into execute_query()", {
    expect_error(
      df_source$execute_query("DELETE FROM test_table"),
      regexp = "disallowed operation"
    )
    expect_error(
      df_source$execute_query("INSERT INTO test_table VALUES (1, 'a', 1)"),
      regexp = "update operation"
    )
  })

  it("does not block keywords in column names or values", {
    expect_no_error(check_query("SELECT update_count FROM table"))
    expect_no_error(check_query("SELECT * FROM delete_logs"))
  })
})

test_that("subclasses of DataSource implement its methods", {
  # Get all exported objects from the package namespace
  ns <- asNamespace("querychat")
  exported_names <- getNamespaceExports(ns)

  # Helper function to check if an R6 class inherits from DataSource
  inherits_from_datasource <- function(r6_class) {
    if (is.null(r6_class) || !R6::is.R6Class(r6_class)) {
      return(FALSE)
    }
    if (r6_class$classname == "DataSource") {
      return(TRUE)
    }
    # Check parent class recursively using get_inherit()
    tryCatch(
      {
        parent <- r6_class$get_inherit()
        if (!is.null(parent)) {
          return(inherits_from_datasource(parent))
        }
      },
      error = function(e) {
        # No parent class
      }
    )
    return(FALSE)
  }

  # Find all R6 classes that inherit from DataSource
  datasource_subclasses <- list()
  for (name in exported_names) {
    obj <- get(name, envir = ns)
    if (R6::is.R6Class(obj) && obj$classname != "DataSource") {
      if (inherits_from_datasource(obj)) {
        datasource_subclasses[[name]] <- obj
      }
    }
  }

  # Ensure we found some subclasses
  skip_if(
    length(datasource_subclasses) == 0,
    "querychat doesn't include any DataSource subclasses?"
  )

  # Get the base DataSource methods and their formal arguments
  base_methods <- lapply(DataSource$public_methods, formals)

  # Helper to get all methods (including inherited) for a class
  get_all_methods <- function(r6_class) {
    all_methods <- list()
    current_class <- r6_class

    while (!is.null(current_class) && R6::is.R6Class(current_class)) {
      # Add methods from current class
      for (method_name in names(current_class$public_methods)) {
        if (!method_name %in% names(all_methods)) {
          all_methods[[method_name]] <- current_class$public_methods[[
            method_name
          ]]
        }
      }

      # Move to parent class
      tryCatch(
        {
          current_class <- current_class$get_inherit()
        },
        error = function(e) {
          current_class <- NULL
        }
      )
    }

    all_methods
  }

  # Check each subclass
  for (class_name in names(datasource_subclasses)) {
    subclass <- datasource_subclasses[[class_name]]

    # Get all methods including inherited ones
    all_methods <- get_all_methods(subclass)

    for (method_name in names(base_methods)) {
      # Check that the method exists (including inherited methods)
      expect(
        method_name %in% names(all_methods),
        cli::format_inline(
          "{.cls {class_name}} must implement required `DataSource` method {.code {method_name}()}."
        )
      )

      if (method_name %in% names(all_methods)) {
        # Get the method's formal arguments
        subclass_formals <- formals(all_methods[[method_name]])
        base_formals <- base_methods[[method_name]]

        # Get argument names (excluding ...)
        base_args <- names(base_formals)
        subclass_args <- names(subclass_formals)

        # Check that all base arguments are present in subclass
        # (subclass can have additional arguments)
        missing_args <- setdiff(base_args, subclass_args)

        expect(
          length(missing_args) == 0,
          cli::format_inline(
            "{.code {class_name}${method_name}()} does not implement all arguments from {.code DataSource${method_name}()}. ",
            "\nMissing: {.and {.code {missing_args}}}"
          )
        )
      }
    }
  }
})
