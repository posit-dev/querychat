describe("QueryChatSystemPrompt$new()", {
  it("initializes with string template", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Template: {{schema}}",
      data_source = ds
    )

    expect_type(sp$template, "character")
    expect_true(grepl("Template:", sp$template))
    expect_type(sp$schema, "character")
    expect_equal(sp$categorical_threshold, 10)
  })

  it("initializes with file path template", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    temp_file <- withr::local_tempfile(fileext = ".md")
    writeLines("File template: {{db_type}}", temp_file)

    sp <- QueryChatSystemPrompt$new(
      prompt_template = temp_file,
      data_source = ds
    )

    expect_type(sp$template, "character")
    expect_true(grepl("File template:", sp$template))
  })

  it("initializes with string data_description", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Template",
      data_source = ds,
      data_description = "Test data description"
    )

    expect_equal(sp$data_description, "Test data description")
  })

  it("initializes with file path data_description", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    temp_file <- withr::local_tempfile(fileext = ".txt")
    writeLines("Data from file", temp_file)

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Template",
      data_source = ds,
      data_description = temp_file
    )

    expect_equal(sp$data_description, "Data from file")
  })

  it("initializes with string extra_instructions", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Template",
      data_source = ds,
      extra_instructions = "Extra instructions here"
    )

    expect_equal(sp$extra_instructions, "Extra instructions here")
  })

  it("initializes with file path extra_instructions", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    temp_file <- withr::local_tempfile(fileext = ".txt")
    writeLines("Instructions from file", temp_file)

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Template",
      data_source = ds,
      extra_instructions = temp_file
    )

    expect_equal(sp$extra_instructions, "Instructions from file")
  })

  it("stores categorical_threshold", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Template",
      data_source = ds,
      categorical_threshold = 25
    )

    expect_equal(sp$categorical_threshold, 25)
  })

  it("handles NULL data_description and extra_instructions", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Template",
      data_source = ds
    )

    expect_null(sp$data_description)
    expect_null(sp$extra_instructions)
  })
})

describe("QueryChatSystemPrompt$render()", {
  it("renders with both tools", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#has_tool_update}}update enabled{{/has_tool_update}}",
      "{{#has_tool_query}}query enabled{{/has_tool_query}}",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds
    )

    result <- sp$render(c("update", "query"))

    expect_true(grepl("update enabled", result))
    expect_true(grepl("query enabled", result))
  })

  it("renders with query only", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#has_tool_update}}update enabled{{/has_tool_update}}",
      "{{#has_tool_query}}query enabled{{/has_tool_query}}",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds
    )

    result <- sp$render("query")

    expect_false(grepl("update enabled", result))
    expect_true(grepl("query enabled", result))
  })

  it("renders with update only", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#has_tool_update}}update enabled{{/has_tool_update}}",
      "{{#has_tool_query}}query enabled{{/has_tool_query}}",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds
    )

    result <- sp$render("update")

    expect_true(grepl("update enabled", result))
    expect_false(grepl("query enabled", result))
  })

  it("renders with NULL tools", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#has_tool_update}}update enabled{{/has_tool_update}}",
      "{{#has_tool_query}}query enabled{{/has_tool_query}}",
      "Always shown",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds
    )

    result <- sp$render(NULL)

    expect_false(grepl("update enabled", result))
    expect_false(grepl("query enabled", result))
    expect_true(grepl("Always shown", result))
  })

  it("includes schema in rendered output", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Schema: {{schema}}",
      data_source = ds
    )

    result <- sp$render(NULL)

    expect_true(grepl("Schema:", result))
    expect_true(grepl("test_table", result))
  })

  it("includes db_type in rendered output", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Database: {{db_type}}",
      data_source = ds
    )

    result <- sp$render(NULL)

    expect_true(grepl("Database:", result))
    expect_true(grepl("DuckDB", result))
  })

  it("includes data_description when provided", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#data_description}}Description: {{data_description}}{{/data_description}}",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds,
      data_description = "My test data"
    )

    result <- sp$render(NULL)

    expect_true(grepl("Description: My test data", result))
  })

  it("excludes data_description when NULL", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#data_description}}Description: {{data_description}}{{/data_description}}",
      "Other content",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds
    )

    result <- sp$render(NULL)

    expect_false(grepl("Description:", result))
    expect_true(grepl("Other content", result))
  })

  it("includes extra_instructions when provided", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#extra_instructions}}Instructions: {{extra_instructions}}{{/extra_instructions}}",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds,
      extra_instructions = "Be concise"
    )

    result <- sp$render(NULL)

    expect_true(grepl("Instructions: Be concise", result))
  })

  it("excludes extra_instructions when NULL", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- paste(
      "{{#extra_instructions}}Instructions: {{extra_instructions}}{{/extra_instructions}}",
      "Other content",
      sep = "\n"
    )

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds
    )

    result <- sp$render(NULL)

    expect_false(grepl("Instructions:", result))
    expect_true(grepl("Other content", result))
  })

  it("detects DuckDB correctly", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    template <- "{{#is_duck_db}}DuckDB detected{{/is_duck_db}}"

    sp <- QueryChatSystemPrompt$new(
      prompt_template = template,
      data_source = ds
    )

    result <- sp$render(NULL)

    # DataFrameSource uses DuckDB under the hood
    expect_true(grepl("DuckDB detected", result))
  })

  it("returns character string", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = "Simple template",
      data_source = ds
    )

    result <- sp$render(NULL)

    expect_type(result, "character")
    expect_true(nchar(result) > 0)
  })
})

describe("QueryChatSystemPrompt with full prompt.md template", {
  it("renders full template with data_description", {
    df <- new_test_df(3)
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = system.file(
        "prompts",
        "prompt.md",
        package = "querychat"
      ),
      data_source = ds,
      data_description = "A test dataframe"
    )
    prompt <- sp$render(NULL)

    expect_type(prompt, "character")
    expect_true(nchar(prompt) > 0)
    expect_match(prompt, "A test dataframe")
    expect_match(prompt, "Table: test_table")
  })

  it("includes DuckDB-specific content for DuckDB sources", {
    df <- new_test_df()
    ds <- DataFrameSource$new(df, "test_table")
    withr::defer(ds$cleanup())

    sp <- QueryChatSystemPrompt$new(
      prompt_template = system.file(
        "prompts",
        "prompt.md",
        package = "querychat"
      ),
      data_source = ds
    )
    sys_prompt <- sp$render(NULL)

    expect_equal(ds$get_db_type(), "DuckDB")
    expect_true(grepl("DuckDB SQL Tips", sys_prompt, fixed = TRUE))
  })

  it("handles categorical_threshold with full template", {
    # Create a source with categorical data
    df_with_categories <- data.frame(
      id = 1:10,
      category = rep(c("A", "B", "C", "D", "E"), each = 2)
    )
    cat_source <- DataFrameSource$new(df_with_categories, "test_table")
    withr::defer(cat_source$cleanup())

    # With low threshold, categories should not be listed
    sp_low <- QueryChatSystemPrompt$new(
      prompt_template = system.file(
        "prompts",
        "prompt.md",
        package = "querychat"
      ),
      data_source = cat_source,
      categorical_threshold = 3
    )
    prompt_low <- sp_low$render(NULL)
    expect_false(grepl("Categorical values:", prompt_low))

    # With high threshold, categories should be listed
    sp_high <- QueryChatSystemPrompt$new(
      prompt_template = system.file(
        "prompts",
        "prompt.md",
        package = "querychat"
      ),
      data_source = cat_source,
      categorical_threshold = 10
    )
    prompt_high <- sp_high$render(NULL)
    expect_match(prompt_high, "Categorical values:")
  })
})
