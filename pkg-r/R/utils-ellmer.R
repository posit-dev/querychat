interpolate_package <- function(path, ..., .envir = parent.frame()) {
  # This helper replicates ellmer::interpolate_package() to work with load_all()
  stopifnot(
    "`path` must be a single string" = is.character(path),
    "`path` must be a single string" = length(path) == 1
  )

  path <- system.file("prompts", path, package = "querychat")
  stopifnot(
    "`path` does not exist" = nzchar(path),
    "`path` does not exist" = file.exists(path)
  )

  ellmer::interpolate_file(path, ..., .envir = .envir)
}
