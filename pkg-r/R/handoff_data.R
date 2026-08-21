materialize_handoff_data <- function(
  catalog,
  data_sources,
  referenced_tables,
  max_bytes = 5 * 1024^2
) {
  validate_handoff_referenced_tables(catalog, referenced_tables)
  unique_tables <- unique(referenced_tables)

  bundled_files <- list()
  bundled_tables <- character()
  combined_size <- 0

  for (table_name in unique_tables) {
    entry <- catalog$entries[[table_name]]
    if (!identical(entry$mode, "dataframe")) {
      next
    }

    csv_bytes <- export_handoff_data_csv(data_sources[[table_name]], table_name)
    combined_size <- combined_size + length(csv_bytes)
    if (combined_size > max_bytes) {
      return(build_externalized_handoff_data_context(catalog, unique_tables))
    }

    bundled_files[[paste0(table_name, ".csv")]] <- csv_bytes
    bundled_tables <- c(bundled_tables, table_name)
  }

  build_handoff_data_context(
    catalog,
    unique_tables,
    bundled_files,
    bundled_tables
  )
}

export_handoff_csv <- function(data_source) {
  df <- data_source$get_data()
  con <- rawConnection(raw(0), "w")
  on.exit(close(con), add = TRUE)
  utils::write.csv(df, con, row.names = FALSE)
  rawConnectionValue(con)
}

prepare_handoff_data <- function(data_sources, language) {
  check_handoff_data_language(language)
  if (!is.list(data_sources)) {
    cli::cli_abort("{.arg data_sources} must be a named list.")
  }
  source_names <- names(data_sources)
  if (
    length(data_sources) > 0L &&
      (is.null(source_names) ||
        anyNA(source_names) ||
        any(!nzchar(source_names)) ||
        anyDuplicated(source_names))
  ) {
    cli::cli_abort(
      "{.arg data_sources} must have unique, nonempty table names."
    )
  }

  entries <- Map(
    function(table_name, source) {
      list(
        table_name = table_name,
        db_type = source$get_db_type(),
        mode = if (inherits(source, "DataFrameSource")) {
          "dataframe"
        } else {
          "database"
        }
      )
    },
    source_names,
    data_sources
  )
  names(entries) <- source_names

  instructions <- vapply(
    entries,
    function(entry) {
      render_handoff_data_instructions(
        entry,
        bundled = identical(entry$mode, "dataframe"),
        language = language
      )
    },
    character(1)
  )

  list(
    entries = entries,
    prompt_instructions = paste(instructions, collapse = "\n\n"),
    language = language
  )
}

render_handoff_data_instructions <- function(entry, bundled, language) {
  check_handoff_data_entry(entry)
  check_bool(bundled)
  check_handoff_data_language(language)

  if (bundled) {
    return(handoff_bundled_csv_instructions(entry$table_name, language))
  }
  if (identical(entry$mode, "database")) {
    return(handoff_database_instructions(
      entry$table_name,
      entry$db_type,
      language
    ))
  }
  handoff_external_dataframe_instructions(
    entry$table_name,
    entry$db_type,
    language
  )
}

handoff_bundled_csv_instructions <- function(table_name, language) {
  introduction <- paste0(
    "A CSV file named `",
    table_name,
    ".csv` is bundled alongside this handoff in the download.\n"
  )
  setup <- if (identical(language, "python")) {
    paste0(
      "Generate Python code that loads this CSV with `duckdb.connect()` ",
      "and DuckDB's `read_csv_auto()`, registering it as the `\"",
      table_name,
      "\"` table.\n"
    )
  } else {
    paste0(
      "Generate R code that connects with ",
      "`DBI::dbConnect(duckdb::duckdb())`, loads this CSV, and registers ",
      "it as the `\"",
      table_name,
      "\"` table with `DBI::dbWriteTable()`.\n"
    )
  }
  paste0(
    introduction,
    setup,
    "The handoff must run with the bundled CSV in the same directory."
  )
}

handoff_external_dataframe_instructions <- function(
  table_name,
  db_type,
  language
) {
  credential_example <- if (identical(language, "python")) {
    '`os.environ["DATABASE_URL"]`'
  } else {
    '`Sys.getenv("DATABASE_URL")`'
  }
  paste0(
    'The original in-memory DataFrame for table "',
    table_name,
    "\" is not bundled.\n",
    "It was exposed through a ",
    db_type,
    " in-memory database.\n",
    "The handoff requires a user-supplied data file or equivalent database ",
    "connection.\n\n",
    "Generate a clearly marked DATA SETUP section at the top of the handoff.\n",
    "Put setup code in a dedicated DATA SETUP block that loads the data and ",
    "registers it under the existing table name `\"",
    table_name,
    "\"`.\n",
    "Use environment variables for any credentials, such as ",
    credential_example,
    ".\n",
    "Do not hardcode credentials.\n",
    "Do not claim to know the original file path, connection string, or ",
    "credentials.\n",
    "This setup may need adjustment before the handoff can run."
  )
}

handoff_database_instructions <- function(table_name, db_type, language) {
  connection <- if (identical(language, "python")) {
    paste0(
      "Use the appropriate Python database client. For credentials, use ",
      'environment variables such as `os.environ["DATABASE_URL"]`.\n'
    )
  } else {
    paste0(
      "Use DBI with the appropriate database backend. For credentials, use ",
      'environment variables such as `Sys.getenv("DATABASE_URL")`.\n'
    )
  }
  paste0(
    "The data comes from a ",
    db_type,
    ' database with a table named "',
    table_name,
    "\".\n\n",
    "Generate a clearly marked DATA SETUP section at the top of the handoff.\n",
    "Include a TODO comment for the ",
    db_type,
    " database connection.\n",
    connection,
    "Do not hardcode passwords or connection strings.\n",
    "Make the required user change clear before the handoff runs."
  )
}

export_handoff_data_csv <- function(data_source, table_name) {
  tryCatch(
    export_handoff_csv(data_source),
    error = function(err) {
      cli::cli_abort(
        "Handoff data could not export dataframe table {.val {table_name}} as CSV.",
        parent = err
      )
    }
  )
}

validate_handoff_referenced_tables <- function(catalog, referenced_tables) {
  missing <- setdiff(referenced_tables, names(catalog$entries))
  if (length(missing) > 0L) {
    cli::cli_abort(
      "Handoff referenced unknown tables: {.val {missing}}"
    )
  }
}

build_handoff_data_context <- function(
  catalog,
  referenced_tables,
  bundled_files,
  bundled_tables,
  externalized_dataframe_tables = character()
) {
  instructions <- vapply(
    referenced_tables,
    function(table_name) {
      render_handoff_data_instructions(
        catalog$entries[[table_name]],
        bundled = table_name %in% bundled_tables,
        language = catalog$language
      )
    },
    character(1)
  )

  list(
    data_instructions = paste(instructions, collapse = "\n\n"),
    bundled_files = bundled_files,
    bundled_tables = bundled_tables,
    externalized_dataframe_tables = externalized_dataframe_tables
  )
}

build_externalized_handoff_data_context <- function(
  catalog,
  referenced_tables
) {
  externalized <- referenced_tables[
    vapply(
      referenced_tables,
      function(table_name) {
        identical(catalog$entries[[table_name]]$mode, "dataframe")
      },
      logical(1)
    )
  ]

  build_handoff_data_context(
    catalog,
    referenced_tables,
    bundled_files = list(),
    bundled_tables = character(),
    externalized_dataframe_tables = externalized
  )
}

check_handoff_data_entry <- function(entry) {
  required <- c("table_name", "db_type", "mode")
  if (!is.list(entry) || !identical(names(entry), required)) {
    cli::cli_abort(
      "{.arg entry} must contain table_name, db_type, and mode."
    )
  }
  check_scalar_character(entry$table_name, "entry$table_name")
  check_scalar_character(entry$db_type, "entry$db_type")
  if (
    !is.character(entry$mode) ||
      length(entry$mode) != 1L ||
      is.na(entry$mode) ||
      !entry$mode %in% c("dataframe", "database")
  ) {
    cli::cli_abort(
      "{.field entry$mode} must be {.val dataframe} or {.val database}."
    )
  }
}

check_handoff_data_language <- function(language) {
  if (
    !is.character(language) ||
      length(language) != 1L ||
      is.na(language) ||
      !language %in% c("python", "r")
  ) {
    cli::cli_abort(
      "{.arg language} must be one of {.val python} or {.val r}."
    )
  }
}
