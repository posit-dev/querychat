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


as_querychat_client <- function(client = NULL) {
  if (is.null(client)) {
    client <- querychat_client_option()
  }

  if (is.null(client)) {
    # Use OpenAI with ellmer's default model
    return(ellmer::chat_openai())
  }

  if (rlang::is_function(client)) {
    # `client` as a function was the first interface we supported and expected
    # `system_prompt` as an argument. This avoids breaking existing code.
    client <- client(system_prompt = NULL)
  }

  if (rlang::is_string(client)) {
    client <- ellmer::chat(client)
  }

  if (!inherits(client, "Chat")) {
    cli::cli_abort(
      "`client` must be an {ellmer} Chat object or a function that returns one."
    )
  }

  client
}

querychat_client_option <- function() {
  opt <- getOption("querychat.client", NULL)
  if (!is.null(opt)) {
    return(opt)
  }

  env <- Sys.getenv("QUERYCHAT_CLIENT", "")
  if (nzchar(env)) {
    return(env)
  }

  NULL
}
