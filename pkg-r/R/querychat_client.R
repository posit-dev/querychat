querychat_client <- function(client = NULL) {
  if (is.null(client)) {
    client <- querychat_client_option()
  }

  if (is.null(client)) {
    # Use OpenAI with ellmer's default model
    return(ellmer::chat_openai())
  }

  if (rlang::is_function(client)) {
    client <- client(system_prompt = "")
  }

  if (rlang::is_string(client)) {
    client <- ellmer::chat(client)
  }

  if (!inherits(client, "Chat")) {
    rlang::abort(
      "`client` must be an {ellmer} Chat object or a function that returns one.",
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
