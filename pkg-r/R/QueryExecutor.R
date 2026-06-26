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
    validate_query = function(query) {
      cli::cli_abort(
        "{.fn validate_query} must be implemented by subclass",
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
    initialize = function(dataframes) {
      check_installed("duckdb")

      private$conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")

      for (name in names(dataframes)) {
        duckdb::duckdb_register(
          private$conn,
          name,
          dataframes[[name]],
          experimental = FALSE
        )
      }

      # Cache column names per table before lockdown
      for (name in names(dataframes)) {
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

    validate_query = function(query) {
      check_query(query)
      rs <- DBI::dbSendQuery(private$conn, query)
      on.exit(DBI::dbClearResult(rs))
      DBI::dbFetch(rs, n = 1)
      invisible(NULL)
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

    validate_query = function(query) {
      private$primary$test_query(query)
      invisible(NULL)
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

  if (inherits(first_source, "DataFrameSource")) {
    dataframes <- lapply(data_sources, function(ds) ds$get_data())
    return(DuckDBExecutor$new(dataframes))
  }

  DataSourceExecutor$new(data_sources)
}

# Validates that a new source is compatible with existing sources.
check_source_compatibility <- function(existing_sources, new_source, new_name) {
  if (length(existing_sources) == 0) {
    return(invisible(NULL))
  }

  first_source <- existing_sources[[1]]

  if (!identical(class(new_source), class(first_source))) {
    cli::cli_abort(
      c(
        "Cannot add {.cls {class(new_source)[1]}} table {.val {new_name}}: all tables must be the same type.",
        "i" = "Existing tables use {.cls {class(first_source)[1]}}."
      )
    )
  }

  invisible(NULL)
}
