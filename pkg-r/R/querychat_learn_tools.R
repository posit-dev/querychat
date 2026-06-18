# File tools for learn mode. These let the learning assistant read and maintain
# the data-description file. All paths are resolved against the current working
# directory and rejected if they escape it, since shinychat has no permission
# system. The one exception is the learn-dataset skill file, which lives in the
# installed package and is explicitly allowed for the `read` tool.

querychat_learn_read <- function(skill_path = NULL) {
  force(skill_path)

  ellmer::tool(
    function(path) {
      target <- learn_resolve_path(path, allow = skill_path)
      if (is_condition(target)) {
        return(ellmer::ContentToolResult(error = conditionMessage(target)))
      }
      if (!file.exists(target)) {
        return(ellmer::ContentToolResult(
          error = sprintf("File does not exist: %s", path)
        ))
      }
      ellmer::ContentToolResult(value = read_utf8(target))
    },
    name = "read",
    description = interpolate_package("learn/tool-read.md"),
    arguments = list(
      path = ellmer::type_string(
        "Path to the file to read, relative to the working directory."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Read File",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-file-earmark-text" viewBox="0 0 16 16"><path d="M5.5 7a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1zM5 9.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5"/><path d="M9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.5zM9 1v2a1 1 0 0 0 1 1h2v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1z"/></svg>'
    )
  )
}

querychat_learn_write <- function() {
  ellmer::tool(
    function(path, content) {
      target <- learn_resolve_path(path)
      if (is_condition(target)) {
        return(ellmer::ContentToolResult(error = conditionMessage(target)))
      }
      dir <- dirname(target)
      if (!dir.exists(dir)) {
        dir.create(dir, recursive = TRUE)
      }
      write_utf8(content, target)
      learn_file_result(
        sprintf("Wrote %s.", path),
        path = path,
        content = content
      )
    },
    name = "write",
    description = interpolate_package("learn/tool-write.md"),
    arguments = list(
      path = ellmer::type_string(
        "Path to the file to write, relative to the working directory. Parent directories are created as needed."
      ),
      content = ellmer::type_string(
        "The full contents to write to the file. Overwrites the file if it already exists."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Write File",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-file-earmark-plus" viewBox="0 0 16 16"><path d="M8 6.5a.5.5 0 0 1 .5.5v1.5H10a.5.5 0 0 1 0 1H8.5V11a.5.5 0 0 1-1 0V9.5H6a.5.5 0 0 1 0-1h1.5V7a.5.5 0 0 1 .5-.5"/><path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5z"/></svg>'
    )
  )
}

querychat_learn_edit <- function() {
  ellmer::tool(
    function(path, old, new) {
      target <- learn_resolve_path(path)
      if (is_condition(target)) {
        return(ellmer::ContentToolResult(error = conditionMessage(target)))
      }
      if (!file.exists(target)) {
        return(ellmer::ContentToolResult(
          error = sprintf("File does not exist: %s", path)
        ))
      }
      content <- read_utf8(target)
      n_matches <- length(gregexpr(old, content, fixed = TRUE)[[1]])
      if (identical(gregexpr(old, content, fixed = TRUE)[[1]][1], -1L)) {
        return(ellmer::ContentToolResult(
          error = sprintf("`old` string not found in %s.", path)
        ))
      }
      if (n_matches > 1) {
        return(ellmer::ContentToolResult(
          error = sprintf(
            "`old` string is not unique in %s (found %d matches). Provide more surrounding context.",
            path,
            n_matches
          )
        ))
      }
      updated <- sub(old, new, content, fixed = TRUE)
      write_utf8(updated, target)
      learn_file_result(
        sprintf("Edited %s.", path),
        path = path,
        content = updated
      )
    },
    name = "edit",
    description = interpolate_package("learn/tool-edit.md"),
    arguments = list(
      path = ellmer::type_string(
        "Path to the file to edit, relative to the working directory."
      ),
      old = ellmer::type_string(
        "The exact text to replace. Must match the file exactly and appear exactly once."
      ),
      new = ellmer::type_string(
        "The text to replace `old` with."
      )
    ),
    annotations = ellmer::tool_annotations(
      title = "Edit File",
      icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-pencil-square" viewBox="0 0 16 16"><path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/><path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5z"/></svg>'
    )
  )
}

# Resolve a user-supplied path against the working directory, rejecting any
# path that escapes it. Returns the absolute path on success, or an error
# condition (not thrown) describing why the path was rejected. Paths listed in
# `allow` (absolute, already-normalized) bypass the working-directory gate.
learn_resolve_path <- function(path, allow = character()) {
  if (!is_string(path) || !nzchar(path)) {
    return(catch_cnd(cli::cli_abort(
      "{.arg path} must be a non-empty string.",
      call = NULL
    )))
  }

  root <- normalize_path_lexical(getwd())
  abs <- if (is_absolute_path(path)) path else file.path(getwd(), path)
  abs <- normalize_path_lexical(abs)

  allow <- vapply(allow, normalize_path_lexical, character(1))
  if (abs %in% allow) {
    return(abs)
  }

  within <- identical(abs, root) || startsWith(abs, paste0(root, "/"))
  if (!within) {
    return(catch_cnd(cli::cli_abort(
      c(
        "Path is outside the working directory: {.path {path}}",
        "i" = "File tools may only access files within {.path {root}}."
      ),
      call = NULL
    )))
  }

  abs
}

is_absolute_path <- function(path) {
  grepl("^(/|[A-Za-z]:[\\\\/])", path)
}

# Lexically normalize a path: collapse "." and ".." segments and "//", without
# touching the filesystem (so it works for files that don't exist yet).
normalize_path_lexical <- function(path) {
  path <- gsub("\\\\", "/", path)
  is_abs <- startsWith(path, "/")
  parts <- strsplit(path, "/", fixed = TRUE)[[1]]
  out <- character()
  for (p in parts) {
    if (p == "" || p == ".") {
      next
    }
    if (p == "..") {
      if (length(out) > 0 && out[length(out)] != "..") {
        out <- out[-length(out)]
      } else if (!is_abs) {
        out <- c(out, p)
      }
    } else {
      out <- c(out, p)
    }
  }
  paste0(if (is_abs) "/" else "", paste(out, collapse = "/"))
}

# Build a tool result that confirms a file write/edit and shows the resulting
# document in the chat, so the analyst can watch it take shape.
learn_file_result <- function(message, path, content) {
  ellmer::ContentToolResult(
    value = message,
    extra = list(
      display = list(
        title = path,
        markdown = content,
        show_request = FALSE,
        open = TRUE
      )
    )
  )
}

write_utf8 <- function(text, file) {
  writeLines(enc2utf8(text), con = file, useBytes = TRUE)
}
