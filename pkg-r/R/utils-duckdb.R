# Only extension preparation errors trigger the JSON pin fallback; errors from
# reading the pin or materializing its table must still propagate.
duckdb_try_load_json <- function(con) {
  json <- DBI::dbGetQuery(
    con,
    "SELECT installed, loaded FROM duckdb_extensions() WHERE extension_name = 'json'"
  )
  if (isTRUE(json$loaded)) {
    return(TRUE)
  }

  # Older DuckDB drivers do not expose this slot. In that case, try loading
  # the extension as before, without overriding the driver's policy.
  driver <- con@driver
  has_extension_policy <- "allow_extensions" %in% methods::slotNames(driver)
  if (has_extension_policy && identical(driver@allow_extensions, FALSE)) {
    return(FALSE)
  }

  tryCatch(
    {
      if (!isTRUE(json$installed)) {
        DBI::dbExecute(con, "INSTALL json")
      }
      DBI::dbExecute(con, "LOAD json")
      TRUE
    },
    error = function(e) FALSE
  )
}

duckdb_lock_down <- function(con) {
  DBI::dbExecute(
    con,
    r"(
SET allow_community_extensions = false;
SET allow_unsigned_extensions = false;
SET autoinstall_known_extensions = false;
SET autoload_known_extensions = false;
SET enable_external_access = false;
SET disabled_filesystems = 'LocalFileSystem';
SET lock_configuration = true;
    )"
  )
}
