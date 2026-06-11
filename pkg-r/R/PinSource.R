#' Pin Source
#'
#' @description
#' A DataSource implementation that reads data from a
#' [pins](https://pins.rstudio.com/) board. For pin types that DuckDB can read
#' natively (parquet, CSV, JSON), the data is loaded directly from the cached
#' pin files into DuckDB without deserializing into R. For other pin types
#' (e.g. RDS), the data is deserialized via `pin_read()` and must produce
#' a data frame (or tibble) to be registered with DuckDB.
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
    #'
    #' @return A new PinSource object
    initialize = function(board, name, ..., table_name = name, version = NULL) {
      rlang::check_installed("pins", reason = "to use PinSource.")
      rlang::check_installed("duckdb", reason = "to use PinSource.")
      rlang::check_dots_empty()

      table_name <- sanitize_table_name(table_name)
      private$.pin_meta <- pins::pin_meta(board, name, version = version)
      private$.board <- board
      private$.pin_name <- name

      pin_type <- private$.pin_meta$type
      con <- DBI::dbConnect(duckdb::duckdb())

      duckdb_file_types <- c("parquet", "csv", "json")

      if (pin_type %in% duckdb_file_types) {
        paths <- pins::pin_download(board, name, version = version)
        reader_fn <- switch(pin_type,
          parquet = "read_parquet",
          csv = "read_csv_auto",
          json = "read_json_auto"
        )
        quoted_path <- DBI::dbQuoteLiteral(con, paths[[1]])
        sql <- sprintf(
          "CREATE TABLE %s AS SELECT * FROM %s(%s)",
          DBI::dbQuoteIdentifier(con, table_name),
          reader_fn,
          quoted_path
        )
        DBI::dbExecute(con, sql)
      } else {
        data <- pins::pin_read(board, name, version = version)
        if (!is.data.frame(data)) {
          DBI::dbDisconnect(con)
          cli::cli_abort(
            "Pin {.val {name}} contains {.obj_type_friendly {data}}, not a data frame."
          )
        }
        duckdb::dbWriteTable(con, table_name, data)
      }

      DBI::dbExecute(
        con,
        r"(
-- extensions: lock down supply chain + auto behaviors
SET allow_community_extensions = false;
SET allow_unsigned_extensions = false;
SET autoinstall_known_extensions = false;
SET autoload_known_extensions = false;

-- external I/O: block file/database/network access from SQL
SET enable_external_access = false;
SET disabled_filesystems = 'LocalFileSystem';

-- freeze configuration so user SQL can't relax anything
SET lock_configuration = true;
        )"
      )

      super$initialize(con, table_name)
    },

    #' @description
    #' Get a human-readable description of the pin for use in the system prompt.
    #'
    #' @return A string with the pin title, description, and tags, or an empty
    #'   string if none are set.
    get_data_description = function() {
      meta <- private$.pin_meta
      parts <- character()
      if (nzchar(meta$title %||% "")) parts <- c(parts, meta$title)
      if (nzchar(meta$description %||% "")) parts <- c(parts, meta$description)
      if (length(meta$tags) > 0) {
        parts <- c(parts, paste("Tags:", paste(meta$tags, collapse = ", ")))
      }
      paste(parts, collapse = "\n\n")
    }
  ),
  private = list(
    .pin_meta = NULL,
    .board = NULL,
    .pin_name = NULL
  )
)
