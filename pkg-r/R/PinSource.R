#' Pin Source
#'
#' @description
#' A DataSource implementation that reads data from a
#' [pins](https://pins.rstudio.com/) board. When the `"duckdb"` engine is used
#' and the pin type is one DuckDB can read natively (parquet, CSV, JSON), the
#' data is loaded directly from the cached pin files into DuckDB without
#' deserializing into R. For other pin types (e.g. RDS), or when the `"sqlite"`
#' engine is used, the data is deserialized via `pin_read()` and must produce
#' a data frame (or tibble), which is then registered with the chosen engine
#' just like [DataFrameSource].
#'
#' When loaded into DuckDB, the connection's external file access is locked
#' down so that LLM-generated SQL cannot reach the filesystem.
#'
#' If the pin has a title, description, or tags, [QueryChat] uses them as
#' the default `data_description`, which you can override.
#'
#' @section Lazy queries with pins:
#'
#' `PinSource` materializes the full dataset into DuckDB. For large parquet
#' pins where you want lazy query execution, read the pin files yourself and
#' pass a `tbl_sql` to [querychat()] instead:
#'
#' ```r
#' paths <- pins::pin_download(board, "my_pin")
#' con <- DBI::dbConnect(duckdb::duckdb())
#' DBI::dbExecute(
#'   con,
#'   sprintf("CREATE VIEW my_pin AS SELECT * FROM read_parquet('%s')", paths[1])
#' )
#' qc <- querychat(dplyr::tbl(con, "my_pin"))
#' ```
#'
#' The pin files are still downloaded to a local cache --- `pin_download()`
#' always fetches them. But rather than loading everything into memory, DuckDB
#' reads the parquet file lazily through dbplyr.
#'
#' This approach skips the security lockdown that `PinSource` applies, so
#' LLM-generated SQL can access files on the local system.
#'
#' @examples
#' if (rlang::is_installed(c("pins", "duckdb"))) {
#'   # Create a temporary board and pin some data
#'   board <- pins::board_temp()
#'   pins::pin_write(board, mtcars, "mtcars", type = "parquet")
#'
#'   # Create a PinSource
#'   ps <- PinSource$new(board, "mtcars")
#'
#'   # Query the pinned data
#'   ps$execute_query("SELECT * FROM mtcars WHERE mpg > 25")
#'
#'   ps$cleanup()
#' }
#'
#' @export
PinSource <- R6::R6Class(
  "PinSource",
  inherit = DBISource,
  public = list(
    #' @description
    #' Create a new PinSource
    #'
    #' @param board A pins board object (e.g. from [pins::board_folder()] or
    #'   [pins::board_connect()]).
    #' @param name Name of the pin to read.
    #' @param ... Not used; included for extensibility.
    #' @param table_name Name to use for the table in SQL queries. Defaults to
    #'   the pin name.
    #' @param version Pin version to read. If `NULL` (default), reads the
    #'   latest version.
    #' @param engine Database engine to use: `"duckdb"` or `"sqlite"`. Set the
    #'   global option `querychat.DataFrameSource.engine` to specify the default
    #'   engine. If `NULL` (default), uses the first available engine from
    #'   duckdb or RSQLite (in that order). Parquet, CSV, and JSON pins are read
    #'   most efficiently with the `"duckdb"` engine; with `"sqlite"` they are
    #'   deserialized via `pin_read()` instead.
    #'
    #' @return A new PinSource object
    initialize = function(
      board,
      name,
      ...,
      table_name = name,
      version = NULL,
      engine = getOption("querychat.DataFrameSource.engine", NULL)
    ) {
      rlang::check_installed("pins", reason = "to use PinSource.")
      rlang::check_dots_empty()

      engine <- engine %||% get_default_dataframe_engine()
      engine <- tolower(engine)
      arg_match(engine, c("duckdb", "sqlite"))

      table_name <- sanitize_table_name(table_name)
      private$.pin_meta <- pins::pin_meta(board, name, version = version)

      pin_type <- private$.pin_meta$type
      duckdb_file_types <- c("parquet", "csv", "json")
      use_duckdb_file_read <- engine == "duckdb" &&
        pin_type %in% duckdb_file_types

      if (use_duckdb_file_read) {
        check_installed("duckdb")
        con <- DBI::dbConnect(duckdb::duckdb())
        con_owned <- FALSE
        on.exit(if (!con_owned) DBI::dbDisconnect(con), add = TRUE)

        paths <- pins::pin_download(board, name, version = version)
        if (length(paths) != 1) {
          cli::cli_abort(
            "Pin {.val {name}} contains {length(paths)} files, but PinSource requires a single-file pin (as created by {.fn pins::pin_write})."
          )
        }
        reader_fn <- switch(
          pin_type,
          parquet = "read_parquet",
          csv = "read_csv_auto",
          json = "read_json_auto"
        )
        if (pin_type == "json") {
          DBI::dbExecute(con, "INSTALL json")
          DBI::dbExecute(con, "LOAD json")
        }
        quoted_path <- DBI::dbQuoteLiteral(con, paths[[1]])
        sql <- sprintf(
          "CREATE TABLE %s AS SELECT * FROM %s(%s)",
          DBI::dbQuoteIdentifier(con, table_name),
          reader_fn,
          quoted_path
        )
        DBI::dbExecute(con, sql)
        duckdb_lock_down(con)
      } else {
        if (engine == "sqlite" && pin_type %in% duckdb_file_types) {
          cli::cli_warn(
            c(
              "Reading {pin_type} pin {.val {name}} into SQLite.",
              "i" = "The {.pkg duckdb} engine reads {pin_type} pins more efficiently. Install {.pkg duckdb} or pass {.code engine = \"duckdb\"} to read the pin files directly."
            )
          )
        }
        data <- pins::pin_read(board, name, version = version)
        if (!is.data.frame(data)) {
          cli::cli_abort(
            "Pin {.val {name}} contains {.obj_type_friendly {data}}, not a data frame."
          )
        }
        con <- new_dataframe_connection(data, table_name, engine)
        con_owned <- FALSE
        on.exit(if (!con_owned) DBI::dbDisconnect(con), add = TRUE)
      }

      super$initialize(con, table_name)
      con_owned <- TRUE
    },

    #' @description
    #' Get a human-readable description of the pin for use in the system prompt.
    #'
    #' @return A string with the pin title, description, and tags, or an empty
    #'   string if none are set.
    get_data_description = function() {
      meta <- private$.pin_meta
      parts <- character()
      if (nzchar(meta$title %||% "")) {
        parts <- c(parts, meta$title)
      }
      if (nzchar(meta$description %||% "")) {
        parts <- c(parts, meta$description)
      }
      if (length(meta$tags) > 0) {
        parts <- c(parts, paste("Tags:", paste(meta$tags, collapse = ", ")))
      }
      paste(parts, collapse = "\n\n")
    }
  ),
  private = list(
    .pin_meta = NULL
  )
)
