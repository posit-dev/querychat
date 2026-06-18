describe("column_range()", {
  it("creates S3 object with correct class", {
    cr <- column_range(min = 0, max = 100)
    expect_s3_class(cr, "querychat_column_range")
  })

  it("stores min and max", {
    cr <- column_range(min = 1.5, max = 99.9)
    expect_equal(cr$min, 1.5)
    expect_equal(cr$max, 99.9)
  })

  it("allows NULL min/max", {
    cr <- column_range()
    expect_null(cr$min)
    expect_null(cr$max)
  })
})

describe("column_spec()", {
  it("creates S3 object with correct class", {
    cs <- column_spec("price")
    expect_s3_class(cs, "querychat_column_spec")
  })

  it("stores name", {
    cs <- column_spec("price")
    expect_equal(cs$name, "price")
  })

  it("stores optional fields with defaults", {
    cs <- column_spec("price")
    expect_null(cs$type)
    expect_equal(cs$constraints, character())
    expect_null(cs$description)
    expect_null(cs$details)
    expect_null(cs$units)
    expect_null(cs$values)
    expect_null(cs$range)
    expect_null(cs$examples)
  })

  it("stores all provided fields", {
    cr <- column_range(min = 0, max = 1000)
    cs <- column_spec(
      name = "price",
      type = "currency",
      constraints = c("non-negative"),
      description = "Item price",
      details = "Longer details",
      units = "USD",
      values = NULL,
      range = cr,
      examples = c(10, 20, 50)
    )
    expect_equal(cs$name, "price")
    expect_equal(cs$type, "currency")
    expect_equal(cs$constraints, c("non-negative"))
    expect_equal(cs$description, "Item price")
    expect_equal(cs$details, "Longer details")
    expect_equal(cs$units, "USD")
    expect_s3_class(cs$range, "querychat_column_range")
    expect_equal(cs$examples, c(10, 20, 50))
  })

  it("errors if name is missing", {
    expect_error(column_spec())
  })
})

describe("table_spec()", {
  it("creates S3 object with correct class", {
    ts <- table_spec()
    expect_s3_class(ts, "querychat_table_spec")
  })

  it("stores description, details, columns with defaults", {
    ts <- table_spec()
    expect_null(ts$description)
    expect_null(ts$details)
    expect_equal(ts$columns, list())
  })

  it("stores provided fields", {
    cs <- column_spec("id")
    ts <- table_spec(
      description = "My table",
      details = "More details",
      columns = list(cs)
    )
    expect_equal(ts$description, "My table")
    expect_equal(ts$details, "More details")
    expect_length(ts$columns, 1)
    expect_s3_class(ts$columns[[1]], "querychat_column_spec")
  })
})

describe("relationship_spec()", {
  it("creates S3 object with correct class", {
    rs <- relationship_spec(join = "a.id = b.id")
    expect_s3_class(rs, "querychat_relationship_spec")
  })

  it("stores join (required)", {
    rs <- relationship_spec(join = "orders.customer_id = customers.id")
    expect_equal(rs$join, "orders.customer_id = customers.id")
  })

  it("stores optional description and cardinality", {
    rs <- relationship_spec(
      join = "a.id = b.id",
      description = "A joins B",
      cardinality = "one-to-many"
    )
    expect_equal(rs$description, "A joins B")
    expect_equal(rs$cardinality, "one-to-many")
  })

  it("defaults description and cardinality to NULL", {
    rs <- relationship_spec(join = "a.id = b.id")
    expect_null(rs$description)
    expect_null(rs$cardinality)
  })

  it("errors if join is missing", {
    expect_error(relationship_spec())
  })
})

describe("data_dict()", {
  it("creates S3 object with correct class", {
    dd <- data_dict()
    expect_s3_class(dd, "querychat_data_dict")
  })

  it("defaults all fields to NULL/empty", {
    dd <- data_dict()
    expect_null(dd$name)
    expect_null(dd$description)
    expect_equal(dd$tables, list())
    expect_equal(dd$relationships, list())
    expect_equal(dd$glossary, list())
  })

  it("stores all provided fields", {
    ts <- table_spec(description = "Orders table")
    rs <- relationship_spec(join = "orders.customer_id = customers.id")
    dd <- data_dict(
      name = "sales",
      description = "Sales domain",
      tables = list(orders = ts),
      relationships = list(rs),
      glossary = list(ARR = "Annual Recurring Revenue")
    )
    expect_equal(dd$name, "sales")
    expect_equal(dd$description, "Sales domain")
    expect_s3_class(dd$tables[["orders"]], "querychat_table_spec")
    expect_length(dd$relationships, 1)
    expect_equal(dd$glossary[["ARR"]], "Annual Recurring Revenue")
  })
})

describe("read_data_dict()", {
  it("reads a YAML file and returns querychat_data_dict", {
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
    expect_s3_class(dd, "querychat_data_dict")
    expect_equal(dd$name, "test")
    expect_equal(dd$description, "Test domain")
    expect_s3_class(dd$tables[["orders"]], "querychat_table_spec")
    expect_equal(dd$tables[["orders"]]$description, "Orders table")
    expect_length(dd$tables[["orders"]]$columns, 1)
    expect_equal(dd$tables[["orders"]]$columns[[1]]$name, "id")
    expect_length(dd$relationships, 1)
    expect_equal(
      dd$relationships[[1]]$join,
      "orders.customer_id = customers.id"
    )
    expect_equal(dd$glossary[["ARR"]], "Annual Recurring Revenue")
  })

  it("defaults name to file stem when not in YAML", {
    yaml_file <- withr::local_tempfile(fileext = ".yaml")
    writeLines("description: No name here", yaml_file)

    dd <- read_data_dict(yaml_file)
    expect_equal(dd$name, tools::file_path_sans_ext(basename(yaml_file)))
  })

  it("reads a complex YAML with column range and values", {
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
    cols <- dd$tables[["products"]]$columns
    price_col <- cols[[1]]
    cat_col <- cols[[2]]

    expect_s3_class(price_col$range, "querychat_column_range")
    expect_equal(price_col$range$min, 0)
    expect_equal(price_col$range$max, 999)
    expect_equal(cat_col$values, c("A", "B", "C"))
  })
})

describe("data_dict_to_prompt_list()", {
  it("returns list with name and description", {
    dd <- data_dict(name = "sales", description = "Sales domain")
    result <- data_dict_to_prompt_list(dd)
    expect_equal(result[["name"]], "sales")
    expect_equal(result[["description"]], "Sales domain")
  })

  it("omits NULL name and description", {
    dd <- data_dict()
    result <- data_dict_to_prompt_list(dd)
    expect_false("name" %in% names(result))
    expect_false("description" %in% names(result))
  })

  it("includes table descriptions but strips column details", {
    ts <- table_spec(
      description = "Orders table",
      details = "Long details that should not appear",
      columns = list(
        column_spec("id", description = "PK", details = "Internal only")
      )
    )
    dd <- data_dict(tables = list(orders = ts))
    result <- data_dict_to_prompt_list(dd)
    expect_true("tables" %in% names(result))
    expect_equal(result$tables[["orders"]][["description"]], "Orders table")
    # No column info in prompt list
    expect_null(result$tables[["orders"]][["columns"]])
    expect_null(result$tables[["orders"]][["details"]])
  })

  it("includes relationships as list of non-NULL fields", {
    rs <- relationship_spec(
      join = "a.id = b.id",
      description = "A to B",
      cardinality = "one-to-many"
    )
    dd <- data_dict(relationships = list(rs))
    result <- data_dict_to_prompt_list(dd)
    expect_true("relationships" %in% names(result))
    expect_length(result$relationships, 1)
    rel <- result$relationships[[1]]
    expect_equal(rel[["join"]], "a.id = b.id")
    expect_equal(rel[["description"]], "A to B")
    expect_equal(rel[["cardinality"]], "one-to-many")
  })

  it("includes glossary", {
    dd <- data_dict(glossary = list(ARR = "Annual Recurring Revenue"))
    result <- data_dict_to_prompt_list(dd)
    expect_true("glossary" %in% names(result))
    expect_equal(result$glossary[["ARR"]], "Annual Recurring Revenue")
  })

  it("omits empty tables, relationships, glossary", {
    dd <- data_dict()
    result <- data_dict_to_prompt_list(dd)
    expect_false("tables" %in% names(result))
    expect_false("relationships" %in% names(result))
    expect_false("glossary" %in% names(result))
  })

  it("includes table entry as NULL when table has no description", {
    ts <- table_spec()
    dd <- data_dict(tables = list(no_desc = ts))
    result <- data_dict_to_prompt_list(dd)
    expect_true("tables" %in% names(result))
    expect_null(result$tables[["no_desc"]])
  })
})
