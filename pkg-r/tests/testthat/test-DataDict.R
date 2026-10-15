describe("read_data_dict()", {
  it("reads a YAML file and returns a plain list", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines(
      c(
        "$version: \"0.1.0\"",
        "name: test",
        "description: Test domain",
        "tables:",
        "  - name: orders",
        "    description: Orders table",
        "    columns:",
        "      - name: id",
        "        type: integer",
        "        description: Primary key",
        "relationships:",
        "  - join: orders.customer_id = customers.id",
        "    description: Order belongs to customer",
        "    cardinality: many-to-one",
        "glossary:",
        "  ARR: Annual Recurring Revenue"
      ),
      yaml_file
    )

    dd <- read_data_dict(yaml_file)
    expect_true(is.list(dd))
    expect_equal(dd[["name"]], "test")
    expect_equal(dd[["description"]], "Test domain")
    orders <- dd[["tables"]][[1]]
    expect_equal(orders[["name"]], "orders")
    expect_equal(orders[["description"]], "Orders table")
    expect_length(orders[["columns"]], 1)
    expect_equal(orders[["columns"]][[1]][["name"]], "id")
    expect_length(dd[["relationships"]], 1)
    expect_equal(
      dd[["relationships"]][[1]][["join"]],
      "orders.customer_id = customers.id"
    )
    expect_equal(dd[["glossary"]][["ARR"]], "Annual Recurring Revenue")
  })

  it("defaults name to file stem when not in YAML", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines("description: No name here", yaml_file)

    dd <- read_data_dict(yaml_file)
    expect_equal(dd[["name"]], tools::file_path_sans_ext(basename(yaml_file)))
  })

  it("reads a YAML with column range and values", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines(
      c(
        "tables:",
        "  - name: products",
        "    columns:",
        "      - name: price",
        "        range: [0, 999]",
        "      - name: category",
        "        values: [A, B, C]"
      ),
      yaml_file
    )

    dd <- read_data_dict(yaml_file)
    cols <- dd[["tables"]][[1]][["columns"]]
    price_col <- cols[[1]]
    cat_col <- cols[[2]]

    expect_equal(price_col[["range"]][[1]], 0)
    expect_equal(price_col[["range"]][[2]], 999)
    expect_equal(cat_col[["values"]], c("A", "B", "C"))
  })
})

describe("dd_tables_by_name()", {
  it("keys the table list by name", {
    dd <- list(
      tables = list(
        list(name = "orders", description = "Orders"),
        list(name = "customers", description = "Customers")
      )
    )
    tables <- dd_tables_by_name(dd)
    expect_equal(names(tables), c("orders", "customers"))
    expect_equal(tables[["orders"]][["description"]], "Orders")
  })

  it("returns an empty list when there are no tables", {
    expect_equal(dd_tables_by_name(list()), list())
    expect_equal(dd_tables_by_name(list(tables = list())), list())
  })

  it("skips table entries without a name", {
    dd <- list(tables = list(list(description = "No name")))
    expect_equal(dd_tables_by_name(dd), list())
  })

  it("keeps the first entry on duplicate names", {
    dd <- list(
      tables = list(
        list(name = "orders", description = "First"),
        list(name = "orders", description = "Second")
      )
    )
    tables <- dd_tables_by_name(dd)
    expect_equal(tables[["orders"]][["description"]], "First")
  })
})

describe("dd_check_spec_compat()", {
  it("accepts the supported $version without warning", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines('$version: "0.1.0"', yaml_file)
    expect_no_warning(read_data_dict(yaml_file))
  })

  it("treats a null $version as absent", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines(c("$version:", "tables: []"), yaml_file)
    expect_no_warning(read_data_dict(yaml_file))
  })

  it("warns when $version is newer, but still reads the file", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines('$version: "99.0.0"', yaml_file)
    expect_warning(dd <- read_data_dict(yaml_file), "best-effort basis")
    expect_equal(dd[["$version"]], "99.0.0")
  })

  it("errors when $version predates the first spec version", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines('$version: "0.0.9"', yaml_file)
    expect_error(read_data_dict(yaml_file), "can read")
  })

  it("errors when $version is invalid", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines('$version: "not-a-version"', yaml_file)
    expect_error(read_data_dict(yaml_file), "can read")
  })

  it("errors when tables uses the legacy mapping format", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines(c("tables:", "  orders:", "    columns: []"), yaml_file)
    expect_error(read_data_dict(yaml_file), "outdated format")
  })

  it("errors when a table entry has no name", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines(c("tables:", "  - description: No name"), yaml_file)
    expect_error(read_data_dict(yaml_file), "has no")
  })
})

describe("data_dict_to_prompt_list()", {
  it("returns list with name and description", {
    dd <- list(name = "sales", description = "Sales domain")
    result <- data_dict_to_prompt_list(dd)
    expect_equal(result[["name"]], "sales")
    expect_equal(result[["description"]], "Sales domain")
  })

  it("omits NULL name and description", {
    dd <- list()
    result <- data_dict_to_prompt_list(dd)
    expect_false("name" %in% names(result))
    expect_false("description" %in% names(result))
  })

  it("includes table descriptions but strips column details", {
    dd <- list(
      tables = list(
        list(
          name = "orders",
          description = "Orders table",
          details = "Long details that should not appear",
          columns = list(
            list(name = "id", description = "PK", details = "Internal only")
          )
        )
      )
    )
    result <- data_dict_to_prompt_list(dd)
    expect_true("tables" %in% names(result))
    expect_equal(
      result[["tables"]][["orders"]][["description"]],
      "Orders table"
    )
    expect_null(result[["tables"]][["orders"]][["columns"]])
    expect_null(result[["tables"]][["orders"]][["details"]])
  })

  it("includes relationships as list of non-NULL fields", {
    dd <- list(
      relationships = list(
        list(
          join = "a.id = b.id",
          description = "A to B",
          cardinality = "one-to-many"
        )
      )
    )
    result <- data_dict_to_prompt_list(dd)
    expect_true("relationships" %in% names(result))
    expect_length(result[["relationships"]], 1)
    rel <- result[["relationships"]][[1]]
    expect_equal(rel[["join"]], "a.id = b.id")
    expect_equal(rel[["description"]], "A to B")
    expect_equal(rel[["cardinality"]], "one-to-many")
  })

  it("includes glossary", {
    dd <- list(glossary = list(ARR = "Annual Recurring Revenue"))
    result <- data_dict_to_prompt_list(dd)
    expect_true("glossary" %in% names(result))
    expect_equal(result[["glossary"]][["ARR"]], "Annual Recurring Revenue")
  })

  it("omits empty tables, relationships, glossary", {
    dd <- list()
    result <- data_dict_to_prompt_list(dd)
    expect_false("tables" %in% names(result))
    expect_false("relationships" %in% names(result))
    expect_false("glossary" %in% names(result))
  })

  it("includes table entry as NULL when table has no description", {
    dd <- list(tables = list(list(name = "no_desc")))
    result <- data_dict_to_prompt_list(dd)
    expect_true("tables" %in% names(result))
    expect_null(result[["tables"]][["no_desc"]])
  })
})
