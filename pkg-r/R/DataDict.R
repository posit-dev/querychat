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

  dd_check_spec_compat(dd)

  if (is.null(dd[["name"]])) {
    dd[["name"]] <- tools::file_path_sans_ext(basename(path))
  }

  dd
}

# The newest data-dict spec version this version of querychat fully
# understands. Files declaring a newer `$version` are still read, on a
# best-effort basis (unknown fields are ignored), with a warning. Bump this
# opportunistically to keep the warning calibrated — it is not a hard gate.
.dd_known_spec_version <- numeric_version("0.1.0")

#' Warn about data-dict spec compatibility problems.
#'
#' pkg-r intentionally does not fully validate data dictionaries, but a few
#' problems are worth surfacing because they otherwise fail silently: a
#' `$version` newer than the spec version querychat understands, `tables` in
#' the legacy mapping format, and table entries without a `name`.
#'
#' @param dd A data dict list (from [yaml::read_yaml()]).
#' @noRd
dd_check_spec_compat <- function(dd) {
  version <- dd[["$version"]]
  if (!is.null(version)) {
    v <- tryCatch(
      numeric_version(as.character(version)),
      error = function(e) NULL
    )
    if (is.null(v)) {
      cli::cli_warn(c(
        "!" = "Data dictionary has an invalid {.field $version}: {.val {version}}.",
        "i" = "Expected a version like {.val 0.1.0}; see {.url https://data-dict.tidyverse.org/spec.html}."
      ))
    } else if (v > .dd_known_spec_version) {
      cli::cli_warn(c(
        "!" = "Data dictionary declares {.field $version} {.val {version}}, which is newer than the newest data-dict spec version this version of {.pkg querychat} fully understands ({.val {as.character(.dd_known_spec_version)}}).",
        "i" = "The file is read on a best-effort basis — spec fields querychat doesn't know about are ignored.",
        "i" = "If anything looks off, consider upgrading {.pkg querychat} or running {.code data-dict validate-spec <file>}."
      ))
    } else if (v < .dd_known_spec_version) {
      cli::cli_warn(c(
        "!" = "Data dictionary declares {.field $version} {.val {version}}, which predates the first data-dict spec version (0.1.0).",
        "i" = "See {.url https://data-dict.tidyverse.org/spec.html}."
      ))
    }
  }

  tables <- dd[["tables"]]
  if (length(tables) == 0) {
    return(invisible(dd))
  }

  table_names <- names(tables)
  if (!is.null(table_names) && any(nzchar(table_names))) {
    cli::cli_warn(c(
      "!" = "Data dictionary {.field tables} uses an outdated format and will be ignored.",
      "i" = "{.field tables} must be a list of tables, each with a {.field name} field — not a mapping of name to definition.",
      "i" = "Update the file to the current spec ({.url https://data-dict.tidyverse.org/spec.html}); {.code data-dict validate-spec <file>} checks a file against the spec."
    ))
    return(invisible(dd))
  }

  unnamed <- vapply(
    tables,
    function(tbl) {
      nm <- if (is.list(tbl)) tbl[["name"]] else NULL
      is.null(nm) || length(nm) != 1 || !nzchar(nm)
    },
    logical(1)
  )
  if (any(unnamed)) {
    cli::cli_warn(c(
      "!" = "{sum(unnamed)} table entr{?y/ies} in the data dictionary ha{?s/ve} no {.field name} and will be ignored.",
      "i" = "Each entry in {.field tables} needs a {.field name}; see {.url https://data-dict.tidyverse.org/spec.html}."
    ))
  }

  invisible(dd)
}

#' Key a data dict's table list by table name.
#'
#' In the data-dict spec, `tables` is a list of table entries each with a
#' `name` field. Returns a named list mapping table name to table entry, for
#' lookup-style access. Entries without a `name` are skipped. On duplicate
#' names the first entry wins (matching pkg-py's `DataDict.get_table()`).
#'
#' @param dd A data dict list (from [read_data_dict()]).
#' @return A named list of table entries.
#' @noRd
dd_tables_by_name <- function(dd) {
  tables <- dd[["tables"]] %||% list()
  out <- list()
  for (tbl in tables) {
    nm <- tbl[["name"]]
    if (!is.null(nm) && nzchar(nm) && is.null(out[[nm]])) {
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
