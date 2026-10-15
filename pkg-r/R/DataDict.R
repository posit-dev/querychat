#' Read a Data Dictionary from YAML
#'
#' @description
#' Loads a data dictionary from a YAML file conforming to the
#' [data-dict spec](https://data-dict.tidyverse.org/). The dictionary is
#' returned as a plain list and can be passed directly to [QueryChat] via the
#' `data_dict` argument.
#'
#' If `name` is absent from the YAML file, it defaults to the file stem.
#'
#' @param path Path to the YAML file.
#'
#' @return A named list with the structure of the YAML file.
read_data_dict <- function(path) {
  check_installed("yaml")
  check_string(path)

  dd <- yaml::read_yaml(path) %||% list()

  if (is.null(dd[["name"]])) {
    dd[["name"]] <- tools::file_path_sans_ext(basename(path))
  }

  dd
}

#' Key a data dict's table list by table name.
#'
#' In the data-dict spec, `tables` is a list of table entries each with a
#' `name` field. Returns a named list mapping table name to table entry, for
#' lookup-style access. Entries without a `name` are skipped.
#'
#' @param dd A data dict list (from [read_data_dict()]).
#' @return A named list of table entries.
#' @noRd
dd_tables_by_name <- function(dd) {
  tables <- dd[["tables"]] %||% list()
  out <- list()
  for (tbl in tables) {
    nm <- tbl[["name"]]
    if (!is.null(nm) && nzchar(nm)) {
      out[[nm]] <- tbl
    }
  }
  out
}

#' Convert a data dict list to a filtered list for system prompt rendering.
#'
#' Keeps table descriptions (for LLM context), strips per-column details.
#' Relationships and glossary are passed through as-is (NULL fields dropped).
#'
#' @param dd A data dict list (from [read_data_dict()]).
#' @return A named list suitable for inclusion in the system prompt template.
#' @noRd
data_dict_to_prompt_list <- function(dd) {
  result <- list()

  if (!is.null(dd[["name"]])) {
    result[["name"]] <- dd[["name"]]
  }
  if (!is.null(dd[["description"]])) {
    result[["description"]] <- dd[["description"]]
  }
  tables <- dd_tables_by_name(dd)
  if (length(tables) > 0) {
    result[["tables"]] <- lapply(tables, function(ts) {
      entry <- compact(
        list(description = ts[["description"]], label = ts[["label"]])
      )
      if (length(entry) == 0) NULL else entry
    })
  }
  if (length(dd[["relationships"]]) > 0) {
    result[["relationships"]] <- lapply(dd[["relationships"]], function(rs) {
      compact(
        list(
          join = rs[["join"]],
          description = rs[["description"]],
          cardinality = rs[["cardinality"]],
          aliases = rs[["aliases"]],
          conflicts = rs[["conflicts"]]
        )
      )
    })
  }
  if (length(dd[["glossary"]]) > 0) {
    result[["glossary"]] <- dd[["glossary"]]
  }

  result
}

#' @noRd
compact <- function(x) {
  x[!vapply(x, is.null, logical(1))]
}
