describe("prepare_handoff_data()", {
  it("classifies DataFrameSource separately from other source classes", {
    skip_if_no_dataframe_engine()
    dataframe <- local_recording_data_frame_source(engine = "sqlite")
    database <- new_fake_handoff_data_source()

    catalog <- prepare_handoff_data(
      list(tips = dataframe$source, orders = database),
      language = "python"
    )

    expect_identical(catalog$entries$tips$mode, "dataframe")
    expect_identical(catalog$entries$orders$mode, "database")
    expect_identical(catalog$entries$tips$table_name, "tips")
    expect_identical(catalog$entries$orders$db_type, "PostgreSQL")
  })

  it("classifies DBISource and TblSqlSource as database sources", {
    skip_if_not_installed("RSQLite")
    sqlite <- local_sqlite_connection(table_name = "orders")
    dbi_source <- DBISource$new(sqlite$conn, "orders")
    tbl_source <- local_tbl_sql_source(table_name = "sales")

    catalog <- prepare_handoff_data(
      list(orders = dbi_source, sales = tbl_source),
      language = "python"
    )

    expect_identical(catalog$entries$orders$mode, "database")
    expect_identical(catalog$entries$sales$mode, "database")
  })

  it("returns the final catalog shape and describes every source", {
    skip_if_no_dataframe_engine()
    first <- local_recording_data_frame_source(
      table_name = "first",
      engine = "sqlite"
    )
    second <- local_recording_data_frame_source(
      table_name = "second",
      engine = "sqlite"
    )

    catalog <- prepare_handoff_data(
      list(first = first$source, second = second$source),
      language = "r"
    )

    expect_named(
      catalog,
      c("entries", "prompt_instructions", "language"),
      ignore.order = FALSE
    )
    expect_named(catalog$entries, c("first", "second"))
    expect_identical(catalog$language, "r")
    expect_match(catalog$prompt_instructions, "first.csv", fixed = TRUE)
    expect_match(catalog$prompt_instructions, "second.csv", fixed = TRUE)
  })

  it("does not read or materialize dataframe data", {
    skip_if_no_dataframe_engine()
    used <- local_recording_data_frame_source(
      table_name = "used",
      engine = "sqlite"
    )
    unused <- local_recording_data_frame_source(
      table_name = "unused",
      engine = "sqlite"
    )

    catalog <- prepare_handoff_data(
      list(used = used$source, unused = unused$source),
      language = "python"
    )

    expect_identical(used$state$get_data_calls, 0L)
    expect_identical(unused$state$get_data_calls, 0L)
    expect_false("bundled_files" %in% names(catalog))
  })

  it("rejects unsupported languages", {
    expect_snapshot(
      error = TRUE,
      prepare_handoff_data(
        list(orders = new_fake_handoff_data_source()),
        language = "javascript"
      )
    )
  })
})

describe("render_handoff_data_instructions()", {
  it("uses target-language APIs for bundled CSV data", {
    entry <- list(
      table_name = "tips",
      db_type = "DuckDB",
      mode = "dataframe"
    )

    python <- render_handoff_data_instructions(entry, TRUE, "python")
    r <- render_handoff_data_instructions(entry, TRUE, "r")

    expect_match(python, "duckdb.connect()", fixed = TRUE)
    expect_no_match(python, "DBI::dbConnect", fixed = TRUE)
    expect_match(r, "DBI::dbConnect(duckdb::duckdb())", fixed = TRUE)
    expect_no_match(r, "duckdb.connect()", fixed = TRUE)
  })

  it("uses target-language credential APIs for database data", {
    entry <- list(
      table_name = "orders",
      db_type = "PostgreSQL",
      mode = "database"
    )

    python <- render_handoff_data_instructions(entry, FALSE, "python")
    r <- render_handoff_data_instructions(entry, FALSE, "r")

    expect_match(python, 'os.environ["DATABASE_URL"]', fixed = TRUE)
    expect_no_match(python, "Sys.getenv", fixed = TRUE)
    expect_match(r, 'Sys.getenv("DATABASE_URL")', fixed = TRUE)
    expect_no_match(r, "os.environ", fixed = TRUE)
    expect_match(python, "Do not hardcode", fixed = TRUE)
    expect_match(r, "Do not hardcode", fixed = TRUE)
  })

  it("renders safe external-data guidance for unbundled dataframes", {
    entry <- list(
      table_name = "tips",
      db_type = "DuckDB",
      mode = "dataframe"
    )

    instructions <- render_handoff_data_instructions(entry, FALSE, "r")

    expect_match(instructions, "DATA SETUP", fixed = TRUE)
    expect_match(instructions, "user-supplied", fixed = TRUE)
    expect_match(instructions, 'Sys.getenv("DATABASE_URL")', fixed = TRUE)
    expect_match(instructions, "Do not claim to know", fixed = TRUE)
  })
})

describe("materialize_handoff_data()", {
  it("rejects unknown referenced tables before exporting", {
    skip_if_no_dataframe_engine()
    fixture <- local_recording_data_frame_source(
      table_name = "tips",
      engine = "sqlite"
    )
    sources <- list(tips = fixture$source)
    catalog <- prepare_handoff_data(sources, language = "python")

    expect_snapshot(
      error = TRUE,
      materialize_handoff_data(catalog, sources, "missing")
    )
    expect_identical(fixture$state$get_data_calls, 0L)
  })

  it("deduplicates referenced tables in first-reference order", {
    skip_if_no_dataframe_engine()
    first <- local_recording_data_frame_source(
      table_name = "first",
      engine = "sqlite"
    )
    second <- local_recording_data_frame_source(
      table_name = "second",
      engine = "sqlite"
    )
    sources <- list(first = first$source, second = second$source)
    catalog <- prepare_handoff_data(sources, language = "python")

    context <- materialize_handoff_data(
      catalog,
      sources,
      c("second", "first", "second")
    )

    expect_identical(context$bundled_tables, c("second", "first"))
    expect_identical(names(context$bundled_files), c("second.csv", "first.csv"))
  })

  it("exports only referenced dataframe tables and skips database sources", {
    skip_if_no_dataframe_engine()
    dataframe <- local_recording_data_frame_source(
      table_name = "tips",
      engine = "sqlite"
    )
    unused <- local_recording_data_frame_source(
      table_name = "unused",
      engine = "sqlite"
    )
    database <- new_fake_handoff_data_source(table_name = "orders")
    sources <- list(
      tips = dataframe$source,
      unused = unused$source,
      orders = database
    )
    catalog <- prepare_handoff_data(sources, language = "python")

    context <- materialize_handoff_data(catalog, sources, c("tips", "orders"))

    expect_setequal(names(context$bundled_files), "tips.csv")
    expect_identical(context$bundled_tables, "tips")
    expect_identical(dataframe$state$get_data_calls, 1L)
    expect_identical(unused$state$get_data_calls, 0L)
  })

  it("produces UTF-8 CSV bytes with a header row", {
    skip_if_no_dataframe_engine()
    fixture <- local_recording_data_frame_source(
      data = data.frame(name = "café", stringsAsFactors = FALSE),
      table_name = "tips",
      engine = "sqlite"
    )
    sources <- list(tips = fixture$source)
    catalog <- prepare_handoff_data(sources, language = "python")

    context <- materialize_handoff_data(catalog, sources, "tips")

    csv_text <- rawToChar(context$bundled_files[["tips.csv"]])
    expect_match(csv_text, '^"name"', perl = TRUE)
    expect_match(csv_text, "café", fixed = TRUE)
  })

  it("externalizes every referenced dataframe when one export exceeds the byte budget", {
    skip_if_no_dataframe_engine()
    fixture <- local_recording_data_frame_source(
      table_name = "tips",
      engine = "sqlite"
    )
    sources <- list(tips = fixture$source)
    catalog <- prepare_handoff_data(sources, language = "python")

    context <- materialize_handoff_data(catalog, sources, "tips", max_bytes = 1)

    expect_identical(context$bundled_files, list())
    expect_identical(context$bundled_tables, character())
    expect_identical(context$externalized_dataframe_tables, "tips")
    expect_match(context$data_instructions, "DATA SETUP", fixed = TRUE)
    expect_match(context$data_instructions, "may need adjustment", fixed = TRUE)
  })

  it("externalizes every referenced dataframe when the combined budget is exceeded", {
    skip_if_no_dataframe_engine()
    first <- local_recording_data_frame_source(
      table_name = "tips",
      engine = "sqlite"
    )
    second <- local_recording_data_frame_source(
      table_name = "tips_copy",
      engine = "sqlite"
    )
    sources <- list(tips = first$source, tips_copy = second$source)
    catalog <- prepare_handoff_data(sources, language = "python")
    one_table <- materialize_handoff_data(catalog, sources, "tips")

    context <- materialize_handoff_data(
      catalog,
      sources,
      c("tips", "tips_copy"),
      max_bytes = length(one_table$bundled_files[["tips.csv"]]) + 1
    )

    expect_identical(context$bundled_files, list())
    expect_identical(context$bundled_tables, character())
    expect_identical(
      context$externalized_dataframe_tables,
      c("tips", "tips_copy")
    )
  })

  it("wraps export failures in a stable handoff-specific message", {
    skip_if_no_dataframe_engine()
    fixture <- local_recording_data_frame_source(
      table_name = "tips",
      engine = "sqlite"
    )
    fixture$state$get_data_error <- simpleError("cannot export")
    sources <- list(tips = fixture$source)
    catalog <- prepare_handoff_data(sources, language = "python")

    expect_snapshot(
      error = TRUE,
      materialize_handoff_data(catalog, sources, "tips")
    )
    expect_identical(fixture$state$get_data_calls, 1L)
  })
})
