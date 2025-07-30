#' Create a data source for querychat
#'
#' Generic function to create a data source for querychat. This function
#' dispatches to appropriate methods based on input.
#'
#' @param x A data frame or DBI connection
#' @param table_name The name to use for the table in the data source. Can be:
#'   - A character string (e.g., "table_name")
#'   - Or, for tables contained within catalogs or schemas, a [DBI::Id()] object (e.g., `DBI::Id(schema = "schema_name", table = "table_name")`)
#' @param categorical_threshold For text columns, the maximum number of unique values to consider as a categorical variable
#' @param ... Additional arguments passed to specific methods
#' @return A querychat_data_source object
#' @export
querychat_data_source <- function(x, ...) {
  UseMethod("querychat_data_source")
}

#' @export
#' @rdname querychat_data_source
querychat_data_source.data.frame <- function(
  x,
  table_name = NULL,
  categorical_threshold = 20,
  ...
) {
  if (is.null(table_name)) {
    # Infer table name from dataframe name, if not already added
    table_name <- deparse(substitute(x))
    if (is.null(table_name) || table_name == "NULL" || table_name == "x") {
      rlang::abort(
        "Unable to infer table name. Please specify `table_name` argument explicitly."
      )
    }
  }

  is_table_name_ok <- is.character(table_name) &&
    length(table_name) == 1 &&
    grepl("^[a-zA-Z][a-zA-Z0-9_]*$", table_name, perl = TRUE)
  if (!is_table_name_ok) {
    rlang::abort(
      "`table_name` argument must be a string containing a valid table name."
    )
  }

  # Create duckdb connection
  conn <- DBI::dbConnect(duckdb::duckdb(), dbdir = ":memory:")
  duckdb::duckdb_register(conn, table_name, x, experimental = FALSE)

  structure(
    list(
      conn = conn,
      table_name = table_name,
      categorical_threshold = categorical_threshold
    ),
    class = c("data_frame_source", "dbi_source", "querychat_data_source")
  )
}

#' @export
#' @rdname querychat_data_source
querychat_data_source.DBIConnection <- function(
  x,
  table_name,
  categorical_threshold = 20,
  ...
) {
  # Handle different types of table_name inputs
  if (inherits(table_name, "Id")) {
    # DBI::Id object - keep as is
  } else if (is.character(table_name) && length(table_name) == 1) {
    # Character string - keep as is
  } else {
    # Invalid input
    rlang::abort(
      "`table_name` must be a single character string or a DBI::Id object"
    )
  }

  # Check if table exists
  if (!DBI::dbExistsTable(x, table_name)) {
    rlang::abort(paste0(
      "Table ",
      DBI::dbQuoteIdentifier(x, table_name),
      " not found in database. If you're using a table in a catalog or schema, pass a DBI::Id",
      " object to `table_name`"
    ))
  }

  structure(
    list(
      conn = x,
      table_name = table_name,
      categorical_threshold = categorical_threshold
    ),
    class = c("dbi_source", "querychat_data_source")
  )
}

#' Execute a SQL query on a data source
#'
#' @param source A querychat_data_source object
#' @param query SQL query string
#' @param ... Additional arguments passed to methods
#' @return Result of the query as a data frame
#' @export
execute_query <- function(source, query, ...) {
  UseMethod("execute_query")
}

#' @export
execute_query.dbi_source <- function(source, query, ...) {
  if (is.null(query) || query == "") {
    # For a null or empty query, default to returning the whole table (ie SELECT *)
    query <- paste0(
      "SELECT * FROM ",
      DBI::dbQuoteIdentifier(source$conn, source$table_name)
    )
  }
  # Execute the query directly
  DBI::dbGetQuery(source$conn, query)
}


#' Get a lazy representation of a data source
#'
#' @param source A querychat_data_source object
#' @param query SQL query string
#' @param ... Additional arguments passed to methods
#' @return A lazy representation (typically a dbplyr tbl)
#' @export
get_lazy_data <- function(source, query, ...) {
  UseMethod("get_lazy_data")
}

#' @export
get_lazy_data.dbi_source <- function(
  source,
  query = NULL,
  ...
) {
  if (is.null(query) || query == "") {
    # For a null or empty query, default to returning the whole table (ie SELECT *)
    dplyr::tbl(source$conn, source$table_name)
  } else {
    # Clean the SQL query to avoid dbplyr issues with syntax problems
    cleaned_query <- clean_sql(query, enforce_select = TRUE)

    if (is.null(cleaned_query)) {
      # If cleaning results in an empty query, raise an error
      rlang::abort(c(
        "Query cleaning resulted in an empty query.",
        "i" = "Check the original query for proper syntax.",
        "i" = "Query may consist only of comments or invalid SQL."
      ))
    } else {
      # Use dbplyr::sql to create a safe SQL query object with the cleaned query
      # No fallback to full table on error - let errors propagate to the caller
      dplyr::tbl(source$conn, dbplyr::sql(cleaned_query))
    }
  }
}


#' Test a SQL query on a data source.
#'
#' @param source A querychat_data_source object
#' @param query SQL query string
#' @param ... Additional arguments passed to methods
#' @return Result of the query, limited to one row of data.
#' @export
test_query <- function(source, query, ...) {
  UseMethod("test_query")
}

#' @export
test_query.dbi_source <- function(source, query, ...) {
  rs <- DBI::dbSendQuery(source$conn, query)
  df <- DBI::dbFetch(rs, n = 1)
  DBI::dbClearResult(rs)
  df
}

#' Clean up a data source (close connections, etc.)
#'
#' @param source A querychat_data_source object
#' @param ... Additional arguments passed to methods
#' @return NULL (invisibly)
#' @export
cleanup_source <- function(source, ...) {
  UseMethod("cleanup_source")
}

#' @export
cleanup_source.dbi_source <- function(source, ...) {
  if (!is.null(source$conn) && DBI::dbIsValid(source$conn)) {
    DBI::dbDisconnect(source$conn)
  }
  invisible(NULL)
}
