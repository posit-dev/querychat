#' Data Dictionary for Rich Table Metadata
#'
#' @description
#' A data dictionary provides rich per-table and per-column metadata to the LLM,
#' allowing you to document tables and columns without relying entirely on
#' live statistics inferred from the data source.
#'
#' For columns listed in a data dictionary:
#' * `values` replaces categorical inference (no `SELECT DISTINCT` query).
#' * `range` replaces live min/max statistics queries.
#' * `description` is forwarded verbatim to the LLM's schema view.
#'
#' Columns not listed fall back to the normal live-statistics path.
#'
#' @param name Short identifier for this dictionary's domain (e.g. `"sales"`).
#'   When loading from YAML via [read_data_dict()], defaults to the file stem
#'   if not set explicitly.
#' @param description One-line summary of the domain.
#' @param tables Named list of [table_spec()] objects, keyed by table name.
#'   Table names must match those registered with `QueryChat`.
#' @param relationships List of [relationship_spec()] objects declaring
#'   cross-table relationships.
#' @param glossary Named list or character vector of domain term definitions
#'   (e.g. `list(ARR = "Annual Recurring Revenue")`).
#'
#' @return A `querychat_data_dict` S3 object.
#' @export
data_dict <- function(
  name = NULL,
  description = NULL,
  tables = list(),
  relationships = list(),
  glossary = list()
) {
  check_string(name, allow_null = TRUE)
  check_string(description, allow_null = TRUE)

  structure(
    list(
      name = name,
      description = description,
      tables = tables,
      relationships = relationships,
      glossary = glossary
    ),
    class = "querychat_data_dict"
  )
}

#' @describeIn data_dict Per-table metadata.
#'
#' @param description Short description of the table, forwarded to the LLM's
#'   schema view.
#' @param details Longer narrative shown only in the on-demand `get_schema`
#'   tool response.
#' @param columns List of [column_spec()] objects. Columns not listed here are
#'   documented using live statistics inferred from the data.
#'
#' @return A `querychat_table_spec` S3 object.
#' @export
table_spec <- function(description = NULL, details = NULL, columns = list()) {
  check_string(description, allow_null = TRUE)
  check_string(details, allow_null = TRUE)

  structure(
    list(description = description, details = details, columns = columns),
    class = "querychat_table_spec"
  )
}

#' @describeIn data_dict Per-column metadata.
#'
#' @param name Column name as it appears in the data source.
#' @param type Human-readable type override (e.g. `"date"`, `"currency"`).
#'   When supplied, this replaces the inferred SQL type in the LLM schema view.
#' @param constraints Free-text constraints conveyed to the LLM
#'   (e.g. `"non-negative"`). A character vector; defaults to `character()`.
#' @param description Short description forwarded verbatim to the LLM's schema
#'   view.
#' @param details Longer narrative about the column, used only in the on-demand
#'   `get_schema` tool response.
#' @param units Unit label (e.g. `"kg"`, `"USD"`), included in the schema view.
#' @param values Exhaustive list of valid values. Replaces categorical inference
#'   for this column — querychat will not query the data source for distinct
#'   values when this is set.
#' @param range A [column_range()] object giving inclusive min/max bounds.
#'   Replaces live min/max statistics queries when set.
#' @param examples Representative sample values shown to the LLM as context.
#'
#' @return A `querychat_column_spec` S3 object.
#' @export
column_spec <- function(
  name,
  type = NULL,
  constraints = character(),
  description = NULL,
  details = NULL,
  units = NULL,
  values = NULL,
  range = NULL,
  examples = NULL
) {
  check_string(name)
  check_string(type, allow_null = TRUE)
  check_string(description, allow_null = TRUE)
  check_string(details, allow_null = TRUE)
  check_string(units, allow_null = TRUE)

  structure(
    list(
      name = name,
      type = type,
      constraints = constraints,
      description = description,
      details = details,
      units = units,
      values = values,
      range = range,
      examples = examples
    ),
    class = "querychat_column_spec"
  )
}

#' @describeIn data_dict Inclusive numeric range for a column.
#'
#' Pass to the `range` argument of [column_spec()] to override live min/max
#' statistics queries.
#'
#' @param min Minimum value (inclusive).
#' @param max Maximum value (inclusive).
#'
#' @return A `querychat_column_range` S3 object.
#' @export
column_range <- function(min = NULL, max = NULL) {
  structure(list(min = min, max = max), class = "querychat_column_range")
}

#' @describeIn data_dict A declared relationship between two tables.
#'
#' @param join SQL JOIN clause or expression that links the tables
#'   (e.g. `"orders.customer_id = customers.id"`).
#' @param description Human-readable description of the relationship.
#' @param cardinality Cardinality string (e.g. `"one-to-many"`).
#'
#' @return A `querychat_relationship_spec` S3 object.
#' @export
relationship_spec <- function(join, description = NULL, cardinality = NULL) {
  check_string(join)
  check_string(description, allow_null = TRUE)
  check_string(cardinality, allow_null = TRUE)

  structure(
    list(join = join, description = description, cardinality = cardinality),
    class = "querychat_relationship_spec"
  )
}

#' Read a Data Dictionary from YAML
#'
#' @description
#' Loads a [data_dict()] from a YAML file. The YAML schema mirrors the
#' constructor arguments. If `name` is absent from the file, it defaults to
#' the file stem.
#'
#' @param path Path to the YAML file.
#'
#' @return A `querychat_data_dict` S3 object.
#' @export
read_data_dict <- function(path) {
  check_installed("yaml")
  check_string(path)

  raw <- yaml::read_yaml(path)
  if (is.null(raw)) {
    raw <- list()
  }

  dd <- parse_data_dict(raw)

  if (is.null(dd$name)) {
    stem <- tools::file_path_sans_ext(basename(path))
    dd$name <- stem
  }

  dd
}

# Internal helpers -------------------------------------------------------------

#' @noRd
parse_data_dict <- function(raw) {
  tables <- list()
  if (!is.null(raw[["tables"]])) {
    tables <- lapply(raw[["tables"]], parse_table_spec)
  }

  relationships <- list()
  if (!is.null(raw[["relationships"]])) {
    relationships <- lapply(raw[["relationships"]], parse_relationship_spec)
  }

  glossary <- raw[["glossary"]] %||% list()

  data_dict(
    name = raw[["name"]],
    description = raw[["description"]],
    tables = tables,
    relationships = relationships,
    glossary = as.list(glossary)
  )
}

#' @noRd
parse_table_spec <- function(raw) {
  columns <- list()
  if (!is.null(raw[["columns"]])) {
    columns <- lapply(raw[["columns"]], parse_column_spec)
  }

  table_spec(
    description = raw[["description"]],
    details = raw[["details"]],
    columns = columns
  )
}

#' @noRd
parse_column_spec <- function(raw) {
  range_val <- NULL
  if (!is.null(raw[["range"]])) {
    range_val <- column_range(
      min = raw[["range"]][["min"]],
      max = raw[["range"]][["max"]]
    )
  }

  values_val <- raw[["values"]]
  if (!is.null(values_val)) {
    values_val <- as.character(values_val)
  }

  examples_val <- raw[["examples"]]

  constraints_val <- raw[["constraints"]] %||% character()
  if (!is.character(constraints_val)) {
    constraints_val <- as.character(constraints_val)
  }

  column_spec(
    name = raw[["name"]],
    type = raw[["type"]],
    constraints = constraints_val,
    description = raw[["description"]],
    details = raw[["details"]],
    units = raw[["units"]],
    values = values_val,
    range = range_val,
    examples = examples_val
  )
}

#' @noRd
parse_relationship_spec <- function(raw) {
  relationship_spec(
    join = raw[["join"]],
    description = raw[["description"]],
    cardinality = raw[["cardinality"]]
  )
}

#' Convert a data_dict to a filtered list for system prompt rendering.
#'
#' Keeps table descriptions (for LLM context), strips per-column details.
#' Relationships and glossary are passed through as-is (NULL fields dropped).
#'
#' @param dd A `querychat_data_dict` object.
#' @return A named list suitable for inclusion in the system prompt template.
#' @noRd
data_dict_to_prompt_list <- function(dd) {
  result <- list()

  if (!is.null(dd$name)) {
    result[["name"]] <- dd$name
  }
  if (!is.null(dd$description)) {
    result[["description"]] <- dd$description
  }
  if (length(dd$tables) > 0) {
    result[["tables"]] <- lapply(dd$tables, function(ts) {
      if (is.null(ts$description)) NULL else list(description = ts$description)
    })
  }
  if (length(dd$relationships) > 0) {
    result[["relationships"]] <- lapply(dd$relationships, function(rs) {
      compact(
        list(
          join = rs$join,
          description = rs$description,
          cardinality = rs$cardinality
        )
      )
    })
  }
  if (length(dd$glossary) > 0) {
    result[["glossary"]] <- dd$glossary
  }

  result
}

#' @noRd
compact <- function(x) {
  x[!vapply(x, is.null, logical(1))]
}
