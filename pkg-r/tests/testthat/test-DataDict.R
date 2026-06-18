describe("read_data_dict()", {
  it("reads a YAML file and returns a plain list", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines(
      c(
        "name: test",
        "description: Test domain",
        "tables:",
        "  orders:",
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
    expect_true(is.list(dd[["tables"]][["orders"]]))
    expect_equal(dd[["tables"]][["orders"]][["description"]], "Orders table")
    expect_length(dd[["tables"]][["orders"]][["columns"]], 1)
    expect_equal(dd[["tables"]][["orders"]][["columns"]][[1]][["name"]], "id")
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
        "  products:",
        "    columns:",
        "      - name: price",
        "        range:",
        "          min: 0",
        "          max: 999",
        "      - name: category",
        "        values: [A, B, C]"
      ),
      yaml_file
    )

    dd <- read_data_dict(yaml_file)
    cols <- dd[["tables"]][["products"]][["columns"]]
    price_col <- cols[[1]]
    cat_col <- cols[[2]]

    expect_equal(price_col[["range"]][["min"]], 0)
    expect_equal(price_col[["range"]][["max"]], 999)
    expect_equal(cat_col[["values"]], c("A", "B", "C"))
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
        orders = list(
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
    expect_equal(result[["tables"]][["orders"]][["description"]], "Orders table")
    expect_null(result[["tables"]][["orders"]][["columns"]])
    expect_null(result[["tables"]][["orders"]][["details"]])
  })

  it("includes relationships as list of non-NULL fields", {
    dd <- list(
      relationships = list(
        list(join = "a.id = b.id", description = "A to B", cardinality = "one-to-many")
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
    dd <- list(tables = list(no_desc = list()))
    result <- data_dict_to_prompt_list(dd)
    expect_true("tables" %in% names(result))
    expect_null(result[["tables"]][["no_desc"]])
  })
})
