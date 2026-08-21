extract_handoff_gallery_items <- function(turns) {
  items <- list()
  item_index <- 0L

  for (turn in turns) {
    if (!S7::S7_inherits(turn, ellmer::Turn)) {
      next
    }

    results <- Filter(is_handoff_gallery_result, turn@contents)
    contents <- expand_handoff_gallery_contents(turn)

    for (result in results) {
      item <- extract_handoff_gallery_result(
        result,
        contents,
        item_index
      )
      if (!is.null(item)) {
        items[[length(items) + 1L]] <- item
        item_index <- item_index + 1L
      }
    }
  }

  items
}

expand_handoff_gallery_contents <- function(turn) {
  turn@contents <- Filter(
    function(content) {
      !S7::S7_inherits(content, ellmer::ContentToolResult) ||
        is_handoff_gallery_result(content)
    },
    turn@contents
  )
  ellmer:::turn_contents_expand(turn)@contents
}

is_handoff_gallery_result <- function(result) {
  if (!S7::S7_inherits(result, ellmer::ContentToolResult)) {
    return(FALSE)
  }

  request <- result@request
  is.null(result@error) &&
    !is.null(request) &&
    is_scalar_nonempty_gallery_string(request@id) &&
    is_scalar_nonempty_gallery_string(request@name) &&
    is.list(request@arguments) &&
    request@name %in%
      c(
        "querychat_query",
        "querychat_update_dashboard",
        "querychat_visualize"
      )
}

extract_handoff_gallery_result <- function(result, contents, item_index) {
  if (!is_handoff_gallery_result(result)) {
    return(NULL)
  }

  request <- result@request
  if (identical(request@name, "querychat_visualize")) {
    return(extract_handoff_viz_item(result, contents, item_index))
  }
  extract_handoff_query_item(result, item_index)
}

extract_handoff_query_item <- function(result, item_index) {
  arguments <- result@request@arguments
  sql <- arguments$query
  if (!is_scalar_nonempty_gallery_string(sql)) {
    return(NULL)
  }

  title <- first_nonempty_gallery_string(
    arguments$title,
    arguments$`_intent`,
    substr(sql, 1L, 60L)
  )

  HandoffQueryItem(
    id = sprintf("query-%d", item_index),
    title = title,
    sql = sql,
    preview_html = build_handoff_query_preview(result@value)
  )
}

extract_handoff_viz_item <- function(result, contents, item_index) {
  arguments <- result@request@arguments
  ggsql <- arguments$ggsql
  if (!is_scalar_nonempty_gallery_string(ggsql)) {
    return(NULL)
  }

  title <- first_nonempty_gallery_string(
    arguments$title,
    substr(ggsql, 1L, 60L)
  )

  HandoffVizItem(
    id = sprintf("viz-%d", item_index),
    title = title,
    thumbnail = find_handoff_thumbnail(
      contents,
      result@request@id
    ),
    ggsql = ggsql
  )
}

build_handoff_query_preview <- function(value) {
  if (!is.data.frame(value) || nrow(value) == 0L || ncol(value) == 0L) {
    return(NULL)
  }

  rows <- seq_len(min(nrow(value), 4L))
  columns <- seq_len(min(ncol(value), 4L))
  header <- paste0(
    "<th>",
    escape_handoff_preview(names(value)[columns]),
    "</th>",
    collapse = ""
  )
  body <- vapply(
    rows,
    function(row) {
      cells <- vapply(
        columns,
        function(column) {
          value <- value[[column]][row]
          paste0(
            "<td>",
            escape_handoff_preview(format_handoff_preview_cell(value)),
            "</td>"
          )
        },
        character(1)
      )
      paste0("<tr>", paste0(cells, collapse = ""), "</tr>")
    },
    character(1)
  )

  paste0(
    '<table class="querychat-preview-table">',
    "<thead><tr>",
    header,
    "</tr></thead>",
    "<tbody>",
    paste0(body, collapse = ""),
    "</tbody>",
    "</table>"
  )
}

find_handoff_thumbnail <- function(contents, request_id) {
  open_marker <- sprintf(
    '<tool-contents call-id="%s">',
    request_id
  )
  marker_index <- which(vapply(
    contents,
    is_handoff_marker,
    logical(1),
    marker = open_marker
  ))
  if (length(marker_index) == 0L) {
    return(NULL)
  }

  block_start <- marker_index[[1]] + 1L
  if (block_start > length(contents)) {
    return(NULL)
  }
  block <- contents[seq.int(block_start, length(contents))]
  close_index <- which(vapply(
    block,
    is_handoff_marker,
    logical(1),
    marker = "</tool-contents>"
  ))
  if (length(close_index) == 0L) {
    return(NULL)
  }
  block <- block[seq_len(close_index[[1]] - 1L)]

  images <- Filter(
    \(content) S7::S7_inherits(content, ellmer::ContentImageInline),
    block
  )
  if (length(images) == 0L) {
    return(NULL)
  }

  image <- images[[1]]
  if (
    !is_scalar_nonempty_gallery_string(image@type) ||
      !is_scalar_nonempty_gallery_string(image@data)
  ) {
    return(NULL)
  }
  sprintf("data:%s;base64,%s", image@type, image@data)
}

format_handoff_preview_cell <- function(value) {
  if (is.list(value) && length(value) == 1L) {
    value <- value[[1]]
  }
  if (is.null(value) || length(value) == 0L) {
    return("")
  }
  if (is.double(value) && length(value) == 1L && is.nan(value)) {
    return("nan")
  }
  if (anyNA(value)) {
    return("")
  }
  if (length(value) > 1L) {
    return(paste(as.character(value), collapse = ", "))
  }
  if (is.double(value)) {
    if (is.infinite(value)) {
      return(if (value > 0) "inf" else "-inf")
    }
    if (value == trunc(value)) {
      return(format(value, scientific = FALSE, trim = TRUE))
    }
    return(sprintf("%.2f", value))
  }
  as.character(value)
}

escape_handoff_preview <- function(value) {
  as.character(htmltools::htmlEscape(value, attribute = TRUE))
}

is_handoff_marker <- function(content, marker) {
  S7::S7_inherits(content, ellmer::ContentText) &&
    identical(content@text, marker)
}

first_nonempty_gallery_string <- function(...) {
  values <- list(...)
  for (value in values) {
    if (is_scalar_nonempty_gallery_string(value)) {
      return(value)
    }
  }
  ""
}

is_scalar_nonempty_gallery_string <- function(value) {
  is.character(value) &&
    length(value) == 1L &&
    !is.na(value) &&
    nzchar(trimws(value))
}
