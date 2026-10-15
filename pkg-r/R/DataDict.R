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
#' Files written for older formats (a mapping-form `tables`, table entries
#' without a `name`, or a `$version` that is invalid or predates the first
#' spec version) fail with a descriptive error. Files declaring a newer spec
#' `$version` warn and are read on a best-effort basis.
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

# The first data-dict spec version ever released. A `$version` below this
# is not a real spec version.
.dd_first_spec_version <- numeric_version("0.1.0")

# The newest data-dict spec version this version of querychat fully
# understands. Files declaring a newer `$version` are still read, on a
# best-effort basis (unknown fields are ignored), with a warning. Bump this
# opportunistically to keep the warning calibrated — it is not a hard gate.
.dd_known_spec_version <- numeric_version("0.1.0")

#' Check a data dict for spec compatibility problems.
#'
#' Old or malformed files fail hard — there is a clear migration path, and
#' reading on would silently produce a degraded dictionary. Files declaring
#' a newer spec `$version` are only warned about: they may use purely
#' additive features, so they are read on a best-effort basis.
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
    if (is.null(v) || v < .dd_first_spec_version) {
      cli::cli_abort(c(
        "Data dictionary declares {.field $version} {.val {version}}, which is not a data-dict spec version this version of {.pkg querychat} can read.",
        "i" = "The first spec version is {.val {as.character(.dd_first_spec_version)}}; update the file to the current spec ({.url https://data-dict.tidyverse.org/spec.html}).",
        "i" = "{.code data-dict validate-spec <file>} checks a file against the spec."
      ))
    }
    if (v > .dd_known_spec_version) {
      cli::cli_warn(c(
        "!" = "Data dictionary declares {.field $version} {.val {version}}, which is newer than the newest data-dict spec version this version of {.pkg querychat} fully understands ({.val {as.character(.dd_known_spec_version)}}).",
        "i" = "The file is read on a best-effort basis — spec fields querychat doesn't know about are ignored.",
        "i" = "If anything looks off, consider upgrading {.pkg querychat} or running {.code data-dict validate-spec <file>}."
      ))
    }
  }

  tables <- dd[["tables"]]
  if (length(tables) == 0) {
    return(invisible(dd))
  }

  table_names <- names(tables)
  if (!is.null(table_names) && any(nzchar(table_names))) {
    cli::cli_abort(c(
      "Data dictionary {.field tables} uses an outdated format.",
      "i" = "{.field tables} must be a list of tables, each with a {.field name} field — not a mapping of name to definition.",
      "i" = "Update the file to the current spec ({.url https://data-dict.tidyverse.org/spec.html}); {.code data-dict validate-spec <file>} checks a file against the spec."
    ))
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
    cli::cli_abort(c(
      "{sum(unnamed)} table entr{?y/ies} in the data dictionary ha{?s/ve} no {.field name}.",
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
      if (is.null(ts[["description"]])) {
        NULL
      } else {
        list(description = ts[["description"]])
      }
    })
  }
  if (length(dd[["relationships"]]) > 0) {
    result[["relationships"]] <- lapply(dd[["relationships"]], function(rs) {
      compact(
        list(
          join = rs[["join"]],
          description = rs[["description"]],
          cardinality = rs[["cardinality"]]
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
