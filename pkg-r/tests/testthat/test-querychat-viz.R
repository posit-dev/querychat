describe("extract_visualise_table()", {
  it("extracts bare identifier", {
    expect_equal(
      extract_visualise_table(
        "VISUALISE x AS x, y AS y FROM my_table DRAW point"
      ),
      "my_table"
    )
  })

  it("extracts quoted identifier", {
    expect_equal(
      extract_visualise_table('VISUALISE x AS x FROM "My Table" DRAW point'),
      '"My Table"'
    )
  })

  it("returns NULL when no FROM in VISUALISE", {
    expect_null(extract_visualise_table("VISUALISE x AS x, y AS y DRAW point"))
  })

  it("ignores FROM inside DRAW clause", {
    visual <- "VISUALISE x AS x FROM data DRAW point MAPPING x FROM other"
    expect_equal(extract_visualise_table(visual), "data")
  })
})

describe("has_layer_level_source()", {
  it("detects DRAW-level FROM source", {
    expect_true(
      has_layer_level_source(
        "VISUALISE x AS x DRAW point MAPPING x FROM my_table"
      )
    )
  })

  it("ignores VISUALISE-level FROM", {
    expect_false(
      has_layer_level_source(
        "VISUALISE x AS x FROM my_table DRAW point"
      )
    )
  })

  it("ignores SCALE FROM", {
    expect_false(
      has_layer_level_source(
        "VISUALISE x AS x DRAW bar SCALE fill FROM 'red'"
      )
    )
  })
})

describe("execute_ggsql()", {
  skip_if_no_dataframe_engine()
  skip_if_not_installed("ggsql")

  it("executes a basic ggsql query", {
    ds <- local_data_frame_source(new_test_df())
    validated <- ggsql::ggsql_validate(
      "SELECT * FROM test_table VISUALISE value AS x DRAW histogram"
    )
    spec <- execute_ggsql(ds, validated)
    expect_s3_class(spec, "Spec")
  })

  it("lowercases column names", {
    df <- data.frame(ID = 1:3, VALUE = c(10, 20, 30))
    ds <- local_data_frame_source(df, table_name = "upper_table")
    validated <- ggsql::ggsql_validate(
      "SELECT id, value FROM upper_table VISUALISE value AS x DRAW histogram"
    )
    spec <- execute_ggsql(ds, validated)
    expect_s3_class(spec, "Spec")
  })

  it("supports FROM before VISUALISE", {
    ds <- local_data_frame_source(new_test_df())
    validated <- ggsql::ggsql_validate(
      "FROM test_table VISUALISE value AS x DRAW histogram"
    )
    expect_true(validated$valid)
    expect_true(validated$has_visual)
    expect_equal(validated$sql, "SELECT * FROM test_table")
    expect_equal(validated$visual, "VISUALISE value AS x DRAW histogram")

    spec <- execute_ggsql(ds, validated)
    expect_s3_class(spec, "Spec")
  })

  it("rejects layer-level FROM sources", {
    ds <- local_data_frame_source(new_test_df())
    # This is a synthetic test — construct a validated object whose
    # visual has a layer-level source
    expect_error(
      {
        validated <- list(
          sql = "SELECT * FROM test_table",
          visual = "VISUALISE value AS x DRAW point MAPPING x FROM other_table"
        )
        execute_ggsql(ds, validated)
      },
      "Layer-specific sources"
    )
  })
})
