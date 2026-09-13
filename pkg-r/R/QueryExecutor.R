# Private R6 classes for multi-table query execution.
#
# These classes are not exported. They provide a unified interface over
# different data source configurations (single DBI connection, shared DuckDB
# for multiple data frames, etc.).

QueryExecutor <- R6::R6Class(
  "QueryExecutor",
  public = list(
    execute_query = function(query) {
      cli::cli_abort(
        "{.fn execute_query} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },
    test_query = function(query, table_name, require_all_columns = FALSE) {
      cli::cli_abort(
        "{.fn test_query} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },
    get_db_type = function() {
      cli::cli_abort(
        "{.fn get_db_type} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },
    get_schema = function(
      table_name,
      categorical_threshold,
      table_spec = NULL
    ) {
      cli::cli_abort(
        "{.fn get_schema} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },
    get_schema_result = function(
      table_name,
      categorical_threshold,
      table_spec = NULL
    ) {
      cli::cli_abort(
        "{.fn get_schema_result} must be implemented by subclass",
        class = "not_implemented_error"
      )
    },
    cleanup = function() {
      invisible(NULL)
    }
  )
)

DuckDBExecutor <- R6::R6Class(
  "DuckDBExecutor",
  inherit = QueryExecutor,
  private = list(
    conn = NULL,
    table_columns = list()
  ),
  public = list(
    # `data_sources` is a named list of DataFrameSource and/or PinSource
    # objects; each materializes its table into one shared connection, then
    # the connection is locked down once.
    initialize = function(data_sources) {
      check_installed("duckdb")

      private$conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")

      for (name in names(data_sources)) {
        data_sources[[name]]$register_into(private$conn, name)
      }

      # Cache column names per table before lockdown
      for (name in names(data_sources)) {
        cols <- colnames(
          DBI::dbGetQuery(
            private$conn,
            sprintf(
              "SELECT * FROM %s WHERE 1=0",
              DBI::dbQuoteIdentifier(private$conn, name)
            )
          )
        )
        private$table_columns[[name]] <- cols
      }

      duckdb_lock_down(private$conn)
    },

    execute_query = function(query) {
      check_query(query)
      DBI::dbGetQuery(private$conn, query)
    },

    test_query = function(query, table_name, require_all_columns = FALSE) {
      check_query(query)

      rs <- DBI::dbSendQuery(private$conn, query)
      df <- DBI::dbFetch(rs, n = 1)
      DBI::dbClearResult(rs)

      if (require_all_columns) {
        result_columns <- names(df)
        expected <- private$table_columns[[table_name]]
        missing_columns <- setdiff(expected, result_columns)

        if (length(missing_columns) > 0) {
          missing_list <- paste0("'", missing_columns, "'", collapse = ", ")
          cli::cli_abort(
            c(
              "Query result missing required columns: {missing_list}",
              "i" = "The query must return all original table columns (in any order)."
            ),
            class = "querychat_missing_columns_error"
          )
        }
      }

      df
    },

    get_db_type = function() "DuckDB",

    get_schema = function(
      table_name,
      categorical_threshold,
      table_spec = NULL
    ) {
      get_schema_impl(
        private$conn,
        table_name,
        categorical_threshold,
        table_spec = table_spec
      )
    },

    get_schema_result = function(
      table_name,
      categorical_threshold,
      table_spec = NULL
    ) {
      details <- build_column_details_impl(
        private$conn,
        table_name,
        categorical_threshold,
        table_spec = table_spec
      )
      list(
        text = format_schema_from_details(
          as.character(DBI::dbQuoteIdentifier(private$conn, table_name)),
          details
        ),
        columns = details
      )
    },

    cleanup = function() {
      if (!is.null(private$conn) && DBI::dbIsValid(private$conn)) {
        DBI::dbDisconnect(private$conn, shutdown = TRUE)
      }
      invisible(NULL)
    }
  )
)

DataSourceExecutor <- R6::R6Class(
  "DataSourceExecutor",
  inherit = QueryExecutor,
  private = list(
    data_sources = NULL,
    primary = NULL
  ),
  public = list(
    initialize = function(data_sources) {
      private$data_sources <- data_sources
      private$primary <- data_sources[[1]]
    },

    execute_query = function(query) {
      private$primary$execute_query(query)
    },

    test_query = function(query, table_name, require_all_columns = FALSE) {
      private$data_sources[[table_name]]$test_query(
        query,
        require_all_columns = require_all_columns
      )
    },

    get_db_type = function() {
      private$primary$get_db_type()
    },

    get_schema = function(
      table_name,
      categorical_threshold,
      table_spec = NULL
    ) {
      private$data_sources[[table_name]]$get_schema(
        categorical_threshold,
        table_spec = table_spec
      )
    },

    get_schema_result = function(
      table_name,
      categorical_threshold,
      table_spec = NULL
    ) {
      private$data_sources[[table_name]]$get_schema_result(
        categorical_threshold,
        table_spec = table_spec
      )
    },

    cleanup = function() {
      invisible(NULL)
    }
  )
)

# Factory function: chooses executor type based on data source types.
build_query_executor <- function(data_sources) {
  if (length(data_sources) == 1) {
    return(DataSourceExecutor$new(data_sources))
  }

  first_source <- data_sources[[1]]

  if (
    inherits(first_source, "DataFrameSource") ||
      inherits(first_source, "PinSource")
  ) {
    return(DuckDBExecutor$new(data_sources))
  }

  DataSourceExecutor$new(data_sources)
}

# DataFrameSources and PinSources can share a DuckDBExecutor connection.
is_duckdb_family_source <- function(x) {
  inherits(x, "DataFrameSource") || inherits(x, "PinSource")
}

# Validates that a new source is compatible with existing sources.
check_source_compatibility <- function(existing_sources, new_source, new_name) {
  if (length(existing_sources) == 0) {
    return(invisible(NULL))
  }

  first_source <- existing_sources[[1]]

  if (
    is_duckdb_family_source(new_source) && is_duckdb_family_source(first_source)
  ) {
    # Pins materialized into SQLite can't live in a DuckDB executor, so
    # multi-table groups containing sqlite-engine pins are rejected.
    for (existing_name in names(existing_sources)) {
      src <- existing_sources[[existing_name]]
      if (inherits(src, "PinSource") && identical(src$engine, "sqlite")) {
        cli::cli_abort(
          c(
            "Cannot add table {.val {new_name}}: pin {.val {existing_name}} uses {.code engine = \"sqlite\"}, which can't join the shared DuckDB connection used for multi-table chats.",
            "i" = "Recreate pin {.val {existing_name}} with {.code engine = \"duckdb\"} to combine it with other tables."
          )
        )
      }
    }
    if (
      inherits(new_source, "PinSource") &&
        identical(new_source$engine, "sqlite")
    ) {
      cli::cli_abort(
        c(
          "Cannot add pin {.val {new_name}} with {.code engine = \"sqlite\"}: multi-table chats are served by a shared DuckDB connection, which SQLite pins can't join.",
          "i" = "Use {.code engine = \"duckdb\"} to combine pins with other tables."
        )
      )
    }
    return(invisible(NULL))
  }

  if (!identical(class(new_source), class(first_source))) {
    cli::cli_abort(
      c(
        "Cannot add {.cls {class(new_source)[1]}} table {.val {new_name}}: all tables must be the same type.",
        "i" = "Existing tables use {.cls {class(first_source)[1]}}.",
        "i" = "Pins and data frames may be combined with each other, but not with database-backed sources."
      )
    )
  }

  # DataFrameSource inherits DBISource but is exempt: each instance opens its
  # own in-memory connection by design, and multi-table data frames are served
  # by a shared DuckDBExecutor instead.
  if (
    inherits(new_source, "DBISource") &&
      !inherits(new_source, "DataFrameSource") &&
      !identical(new_source$conn, first_source$conn)
  ) {
    cli::cli_abort(
      c(
        "Cannot add table {.val {new_name}}: all database tables must share the same connection.",
        "i" = "Use {.fn $add_tables} to register tables from a single connection."
      )
    )
  }

  invisible(NULL)
}

# Validates that every source in a group is compatible with the others.
validate_source_group_compatibility <- function(data_sources) {
  existing <- list()
  for (name in names(data_sources)) {
    check_source_compatibility(existing, data_sources[[name]], name)
    existing[[name]] <- data_sources[[name]]
  }
  invisible(NULL)
}
