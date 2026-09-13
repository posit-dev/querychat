test_that("TableSet requires at least one data source", {
  sp <- QueryChatSystemPrompt$new(
    prompt_template = system.file(
      "prompts",
      "prompt.md",
      package = "querychat"
    ),
    data_sources = list()
  )
  expect_error(TableSet$new(list(), sp), "at least one")
})

test_that("TableSet requires a named list of data sources", {
  skip_if_no_dataframe_engine()
  ds <- local_data_frame_source(new_test_df())
  sp <- QueryChatSystemPrompt$new(
    prompt_template = system.file(
      "prompts",
      "prompt.md",
      package = "querychat"
    ),
    data_sources = list(test_table = ds)
  )
  expect_error(TableSet$new(list(ds), sp), "named")
})

test_that("TableSet$table_names() preserves registration order", {
  skip_if_not_installed("duckdb")
  a <- local_data_frame_source(new_test_df(), "a")
  b <- local_data_frame_source(new_users_df(), "b")
  ts <- local_table_set(list(a = a, b = b))
  expect_equal(ts$table_names(), c("a", "b"))
})

test_that("TableSet builds its executor lazily and caches it", {
  skip_if_no_dataframe_engine()
  ds <- local_data_frame_source(new_test_df())
  ts <- local_table_set(list(test_table = ds))

  expect_false(ts$executor_built())
  first <- ts$executor()
  expect_true(ts$executor_built())
  expect_identical(ts$executor(), first)
  expect_s3_class(first, "DataSourceExecutor")
})

test_that("TableSet uses DuckDBExecutor for several data frames", {
  skip_if_not_installed("duckdb")
  a <- local_data_frame_source(new_test_df(), "a")
  b <- local_data_frame_source(new_users_df(), "b")
  ts <- local_table_set(list(a = a, b = b))
  expect_s3_class(ts$executor(), "DuckDBExecutor")
})

test_that("TableSet$cleanup_executor() is a no-op before the executor is built", {
  skip_if_no_dataframe_engine()
  ds <- local_data_frame_source(new_test_df())
  ts <- local_table_set(list(test_table = ds))
  expect_no_error(ts$cleanup_executor())
  expect_false(ts$executor_built())
})

test_that("TableSet$cleanup_executor() closes a built DuckDB executor", {
  skip_if_not_installed("duckdb")
  a <- local_data_frame_source(new_test_df(), "a")
  b <- local_data_frame_source(new_users_df(), "b")
  ts <- local_table_set(list(a = a, b = b))
  ex <- ts$executor()
  ts$cleanup_executor()
  expect_error(ex$execute_query("SELECT 1"))
  expect_false(ts$executor_built())
})

test_that("TableSet$cleanup_executor() is safe to call twice", {
  skip_if_not_installed("duckdb")
  a <- local_data_frame_source(new_test_df(), "a")
  b <- local_data_frame_source(new_users_df(), "b")
  ts <- local_table_set(list(a = a, b = b))
  ts$executor()
  ts$cleanup_executor()
  expect_no_error(ts$cleanup_executor())
})

test_that("TableSet fields are read-only", {
  skip_if_no_dataframe_engine()
  ds <- local_data_frame_source(new_test_df())
  ts <- local_table_set(list(test_table = ds))
  expect_error(ts$data_sources <- list(), "read-only")
  expect_error(ts$system_prompt <- NULL, "read-only")
  expect_error(ts$data_description <- "x", "read-only")
})

test_that("validate_source_group_compatibility() rejects mixed source types", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("RSQLite")
  df_source <- local_data_frame_source(new_test_df(), "a")
  db <- local_sqlite_connection(table_name = "b")
  db_source <- DBISource$new(db$conn, "b")
  expect_error(
    validate_source_group_compatibility(list(a = df_source, b = db_source)),
    "same type"
  )
  expect_no_error(validate_source_group_compatibility(list(a = df_source)))
})
