#' Snowflake Source
#'
#' A DataSource implementation for Snowflake database connections with
#' Semantic View support. This class extends DBISource to automatically detect
#' and provide context about Snowflake Semantic Views when available.
#'
#' @noRd
SnowflakeSource <- R6::R6Class(
  "SnowflakeSource",
  inherit = DBISource,
  private = list(
    semantic_views = NULL
  ),
  public = list(
    #' @description
    #' Create a new SnowflakeSource
    #'
    #' @param conn A DBI connection object to Snowflake
    #' @param table_name Name of the table in the database
    #'
    #' @return A new SnowflakeSource object
    initialize = function(conn, table_name) {
      super$initialize(conn, table_name)

      # Discover semantic views at initialization
      private$semantic_views <- discover_semantic_views(conn)
    },

    #' @description
    #' Check if semantic views are available
    #' @return TRUE if semantic views were discovered
    has_semantic_views = function() {
      length(private$semantic_views) > 0
    },

    #' @description
    #' Get the list of discovered semantic views
    #' @return A list of semantic view info (name and ddl)
    get_semantic_views = function() {
      private$semantic_views
    },

    #' @description
    #' Get schema information for the database table, including semantic views
    #'
    #' @param categorical_threshold Maximum number of unique values for a text
    #'   column to be considered categorical (default: 20)
    #' @return A string describing the schema
    get_schema = function(categorical_threshold = 20) {
      # Get base schema from parent
      schema <- super$get_schema(categorical_threshold = categorical_threshold)

      # If no semantic views, return base schema
      if (!self$has_semantic_views()) {
        return(schema)
      }

      # Add semantic view information
      semantic_section <- format_semantic_views_section(private$semantic_views)
      paste(schema, semantic_section, sep = "\n\n")
    }
  )
)


#' Discover Semantic Views in Snowflake
#'
#' @param conn A DBI connection to Snowflake
#' @return A list of semantic views with name and ddl
#' @noRd
discover_semantic_views <- function(conn) {
  semantic_views <- list()


  tryCatch(
    {
      # Check for semantic views in the current schema
      result <- DBI::dbGetQuery(conn, "SHOW SEMANTIC VIEWS")

      if (nrow(result) == 0) {
        return(list())
      }

      for (i in seq_len(nrow(result))) {
        row <- result[i, ]
        view_name <- row[["name"]]
        database_name <- row[["database_name"]]
        schema_name <- row[["schema_name"]]

        if (is.null(view_name) || is.na(view_name)) {
          next
        }

        # Build fully qualified name
        fq_name <- paste(database_name, schema_name, view_name, sep = ".")

        # Get the DDL for this semantic view
        ddl <- get_semantic_view_ddl(conn, fq_name)
        if (!is.null(ddl)) {
          semantic_views <- c(semantic_views, list(list(
            name = fq_name,
            ddl = ddl
          )))
        }
      }
    },
    error = function(e) {
      # Log warning but don't fail - gracefully fall back to no semantic views
      cli::cli_warn("Failed to discover semantic views: {conditionMessage(e)}")
    }
  )

  semantic_views
}


#' Get the DDL for a Semantic View
#'
#' @param conn A DBI connection to Snowflake
#' @param fq_name Fully qualified name (database.schema.view_name)
#' @return The DDL text, or NULL if retrieval failed
#' @noRd
get_semantic_view_ddl <- function(conn, fq_name) {
  tryCatch(
    {
      query <- sprintf("SELECT GET_DDL('SEMANTIC_VIEW', '%s')", fq_name)
      result <- DBI::dbGetQuery(conn, query)
      if (nrow(result) > 0 && ncol(result) > 0) {
        as.character(result[[1, 1]])
      } else {
        NULL
      }
    },
    error = function(e) {
      cli::cli_warn("Failed to get DDL for semantic view {fq_name}: {conditionMessage(e)}")
      NULL
    }
  )
}


#' Format Semantic Views Section for Schema Output
#'
#' @param semantic_views A list of semantic view info (name and ddl)
#' @return A formatted string describing the semantic views
#' @noRd
format_semantic_views_section <- function(semantic_views) {
  lines <- c(
    "## Snowflake Semantic Views",
    "",
    "This database has Semantic Views available. Semantic Views provide a curated",
    "layer over raw data with pre-defined metrics, dimensions, and relationships.",
    "They encode business logic and calculation rules that ensure consistent,",
    "accurate results.",
    "",
    "**IMPORTANT**: When a Semantic View covers the data you need, prefer it over",
    "raw table queries to benefit from certified metric definitions.",
    ""
  )

  for (sv in semantic_views) {
    lines <- c(
      lines,
      sprintf("### Semantic View: `%s`", sv$name),
      "",
      "```sql",
      sv$ddl,
      "```",
      ""
    )
  }

  paste(lines, collapse = "\n")
}


#' Check if a connection is a Snowflake connection
#'
#' @param conn A DBI connection object
#' @return TRUE if the connection is to Snowflake
#' @noRd
is_snowflake_connection <- function(conn) {
  if (!inherits(conn, "DBIConnection")) {
    return(FALSE)
  }

  # Check for known Snowflake connection classes
  if (inherits(conn, "Snowflake")) {
    return(TRUE)
  }

  # Check dbms.name from connection info
  tryCatch(
    {
      conn_info <- DBI::dbGetInfo(conn)
      dbms_name <- tolower(conn_info[["dbms.name"]] %||% "")
      grepl("snowflake", dbms_name, ignore.case = TRUE)
    },
    error = function(e) FALSE
  )
}
