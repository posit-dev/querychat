HandoffChat <- R6::R6Class(
  "HandoffChat",
  public = list(
    initialize = function(chat) {
      private$chat <- chat
    },

    history_turns = function() {
      private$chat$get_turns()
    },

    ask = function(prompt, type, turns = list()) {
      chat <- private$fork(turns)
      chat$chat_structured_async(prompt, type = type)
    },

    stream = function(
      prompt,
      turns = list(),
      system_prompt = NULL,
      type,
      view
    ) {
      chat <- private$fork(turns, system_prompt)
      check_structured_streaming(chat)
      view$set_streaming(TRUE)

      promise <- coro::async(function() {
        # Defer lazy stream iteration so synchronous rejection reaches finally.
        coro::await(promises::promise_resolve(NULL))
        stream <- chat$stream_async(prompt, type = type)
        buffer <- ""
        previous_source <- NULL

        for (chunk in stream) {
          if (promises::is.promising(chunk)) {
            chunk <- coro::await(chunk)
          }
          if (coro::is_exhausted(chunk)) {
            break
          }

          buffer <- paste0(buffer, chunk)
          source <- partial_json_string(buffer)
          if (!is.null(source)) {
            previous_source <- update_streamed_source(
              view,
              previous_source,
              source
            )
          }
        }

        completed <- completed_json_content(chat$get_turns())
        parsed <- completed@parsed
        result <- parse_handoff_result(
          parsed,
          allowed_table_names = result_table_names(type),
          allowed_languages = result_languages(type)
        )
        update_streamed_source(view, previous_source, result@source)

        list(result = result, turns = chat$get_turns())
      })()
      promises::finally(
        promise,
        function() view$set_streaming(FALSE)
      )
    }
  ),
  private = list(
    chat = NULL,

    fork = function(turns, system_prompt = NULL) {
      chat <- private$chat$clone()
      chat$set_turns(turns)
      if (!is.null(system_prompt)) {
        chat$set_system_prompt(system_prompt)
      }
      chat
    }
  )
)

partial_json_string <- function(buffer, field = "source") {
  marker <- paste0('"', field, '"')
  marker_position <- regexpr(marker, buffer, fixed = TRUE)[[1]]
  if (marker_position == -1L) {
    return(NULL)
  }

  position <- marker_position + nchar(marker)
  buffer_length <- nchar(buffer)
  while (
    position <= buffer_length &&
      grepl("[[:space:]]", substr(buffer, position, position))
  ) {
    position <- position + 1L
  }
  if (
    position > buffer_length ||
      substr(buffer, position, position) != ":"
  ) {
    return(NULL)
  }

  position <- position + 1L
  while (
    position <= buffer_length &&
      grepl("[[:space:]]", substr(buffer, position, position))
  ) {
    position <- position + 1L
  }
  if (
    position > buffer_length ||
      substr(buffer, position, position) != '"'
  ) {
    return(NULL)
  }

  decode_partial_json_string(substr(buffer, position + 1L, buffer_length))
}

update_streamed_source <- function(view, previous, source) {
  if (identical(source, previous)) {
    return(source)
  }
  if (!is.null(previous) && startsWith(source, previous)) {
    view$append_source(
      substr(source, nchar(previous) + 1L, nchar(source))
    )
  } else {
    view$replace_source(source)
  }
  source
}

completed_json_content <- function(turns) {
  content_json <- asNamespace("ellmer")[["ContentJson"]]
  for (turn in rev(turns)) {
    if (!S7::S7_inherits(turn, ellmer::AssistantTurn)) {
      next
    }
    for (content in rev(turn@contents)) {
      if (S7::S7_inherits(content, content_json)) {
        return(content)
      }
    }
    break
  }
  cli::cli_abort("Structured stream did not produce completed JSON content.")
}

result_table_names <- function(type) {
  type@properties[["referenced_tables"]]@items@values
}

result_languages <- function(type) {
  type@properties[["language"]]@values
}

check_structured_streaming <- function(chat) {
  stream_arguments <- names(formals(chat$stream_async))
  if (!"type" %in% stream_arguments) {
    cli::cli_abort(
      paste(
        "Structured handoff streaming requires an ellmer",
        "{.code Chat$stream_async()} method with a {.arg type} argument."
      )
    )
  }
}

decode_partial_json_string <- function(value) {
  bytes <- charToRaw(enc2utf8(value))
  bytes_length <- length(bytes)
  position <- 1L
  complete_end <- 0L
  quote <- as.raw(34L)
  backslash <- as.raw(92L)
  unicode <- as.raw(117L)
  control_limit <- as.raw(32L)
  simple_escapes <- as.raw(c(34L, 47L, 92L, 98L, 102L, 110L, 114L, 116L))

  while (position <= bytes_length) {
    byte <- bytes[[position]]
    if (identical(byte, quote)) {
      break
    }
    if (!identical(byte, backslash)) {
      if (byte < control_limit) {
        break
      }
      complete_end <- position
      position <- position + 1L
      next
    }

    if (position + 1L > bytes_length) {
      break
    }
    escape <- bytes[[position + 1L]]
    if (escape %in% simple_escapes) {
      complete_end <- position + 1L
      position <- position + 2L
      next
    }

    if (
      !identical(escape, unicode) ||
        position + 5L > bytes_length
    ) {
      break
    }
    code_unit <- json_hex_code_unit(bytes, position + 2L)
    if (is.na(code_unit)) {
      break
    }

    if (code_unit >= 0xD800L && code_unit <= 0xDBFFL) {
      low_position <- position + 6L
      if (
        low_position + 5L > bytes_length ||
          !identical(bytes[[low_position]], backslash) ||
          !identical(bytes[[low_position + 1L]], unicode)
      ) {
        break
      }
      low_unit <- json_hex_code_unit(bytes, low_position + 2L)
      if (
        is.na(low_unit) ||
          low_unit < 0xDC00L ||
          low_unit > 0xDFFFL
      ) {
        break
      }
      complete_end <- low_position + 5L
      position <- low_position + 6L
      next
    }
    if (code_unit >= 0xDC00L && code_unit <= 0xDFFFL) {
      break
    }

    complete_end <- position + 5L
    position <- position + 6L
  }

  encoded <- if (complete_end == 0L) {
    ""
  } else {
    rawToChar(bytes[seq_len(complete_end)])
  }
  jsonlite::parse_json(paste0('"', encoded, '"'))
}

json_hex_code_unit <- function(bytes, start) {
  values <- as.integer(bytes[start:(start + 3L)])
  digits <- ifelse(
    values >= 48L & values <= 57L,
    values - 48L,
    ifelse(
      values >= 65L & values <= 70L,
      values - 55L,
      ifelse(
        values >= 97L & values <= 102L,
        values - 87L,
        NA_integer_
      )
    )
  )
  if (anyNA(digits)) {
    return(NA_integer_)
  }
  sum(digits * c(4096L, 256L, 16L, 1L))
}
