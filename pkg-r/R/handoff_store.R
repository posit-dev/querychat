HandoffStore <- R6::R6Class(
  "HandoffStore",
  public = list(
    initialize = function(max_items = 25L) {
      if (
        !is.numeric(max_items) ||
          length(max_items) != 1L ||
          is.na(max_items) ||
          max_items != as.integer(max_items) ||
          max_items < 1
      ) {
        cli::cli_abort("{.arg max_items} must be a positive whole number.")
      }
      private$max_items <- as.integer(max_items)
      private$items <- new.env(parent = emptyenv())
    },

    has = function(handoff_id) {
      is_handoff_store_id(handoff_id) &&
        exists(handoff_id, envir = private$items, inherits = FALSE)
    },

    remember = function(state) {
      check_handoff_store_state(state)
      handoff_id <- state@handoff_id
      removed <- list()

      if (self$has(handoff_id)) {
        removed[[length(removed) + 1L]] <- get(
          handoff_id,
          envir = private$items,
          inherits = FALSE
        )
        private$order <- private$order[private$order != handoff_id]
      }

      assign(handoff_id, state, envir = private$items)
      private$order <- c(private$order, handoff_id)

      while (length(private$order) > private$max_items) {
        evicted_id <- private$order[[1]]
        private$order <- private$order[-1]
        removed[[length(removed) + 1L]] <- get(
          evicted_id,
          envir = private$items,
          inherits = FALSE
        )
        rm(list = evicted_id, envir = private$items)
      }

      removed
    },

    replace = function(states) {
      if (!is.list(states)) {
        cli::cli_abort("{.arg states} must be a list of handoff states.")
      }
      for (state in states) {
        check_handoff_store_state(state)
      }

      staged_items <- new.env(parent = emptyenv())
      staged_order <- character()
      staged_removed <- list()
      for (state in states) {
        handoff_id <- state@handoff_id
        if (exists(handoff_id, envir = staged_items, inherits = FALSE)) {
          staged_removed[[length(staged_removed) + 1L]] <- get(
            handoff_id,
            envir = staged_items,
            inherits = FALSE
          )
          staged_order <- staged_order[staged_order != handoff_id]
        }
        assign(handoff_id, state, envir = staged_items)
        staged_order <- c(staged_order, handoff_id)
        while (length(staged_order) > private$max_items) {
          evicted_id <- staged_order[[1]]
          staged_order <- staged_order[-1]
          staged_removed[[length(staged_removed) + 1L]] <- get(
            evicted_id,
            envir = staged_items,
            inherits = FALSE
          )
          rm(list = evicted_id, envir = staged_items)
        }
      }

      removed <- c(self$values(), staged_removed)
      private$items <- staged_items
      private$order <- staged_order
      removed
    },

    get = function(handoff_id) {
      if (!self$has(handoff_id)) {
        return(NULL)
      }
      private$order <- c(
        private$order[private$order != handoff_id],
        handoff_id
      )
      get(handoff_id, envir = private$items, inherits = FALSE)
    },

    discard = function(handoff_id) {
      if (!self$has(handoff_id)) {
        return(NULL)
      }
      state <- get(handoff_id, envir = private$items, inherits = FALSE)
      rm(list = handoff_id, envir = private$items)
      private$order <- private$order[private$order != handoff_id]
      state
    },

    values = function() {
      lapply(
        private$order,
        get,
        envir = private$items,
        inherits = FALSE
      )
    },

    snapshot = function() {
      self$values()
    }
  ),
  private = list(
    max_items = NULL,
    items = NULL,
    order = character()
  )
)

HandoffBundleStore <- R6::R6Class(
  "HandoffBundleStore",
  public = list(
    initialize = function(max_bytes = 25 * 1024^2) {
      if (
        !is.numeric(max_bytes) ||
          length(max_bytes) != 1L ||
          is.na(max_bytes) ||
          !is.finite(max_bytes) ||
          max_bytes < 1
      ) {
        cli::cli_abort("{.arg max_bytes} must be a positive number.")
      }
      private$max_bytes <- max_bytes
      private$items <- new.env(parent = emptyenv())
    },

    stage = function(bundled_files) {
      files <- copy_handoff_bundle_files(bundled_files)
      byte_size <- handoff_bundle_byte_size(files)
      if (byte_size > private$max_bytes) {
        cli::cli_abort(
          "Handoff data snapshot exceeds the session storage limit."
        )
      }

      bundle_id <- private$new_bundle_id()
      bundle <- HandoffBundle(
        bundle_id = bundle_id,
        bundled_files = files
      )
      assign(bundle_id, bundle, envir = private$items)
      private$order <- c(private$order, bundle_id)
      private$total_bytes <- private$total_bytes + byte_size
      bundle
    },

    put = function(bundled_files) {
      bundle <- self$stage(bundled_files)
      self$evict()
      bundle
    },

    get = function(bundle_id) {
      if (
        !is_handoff_store_id(bundle_id) ||
          !exists(bundle_id, envir = private$items, inherits = FALSE)
      ) {
        return(NULL)
      }
      private$order <- c(
        private$order[private$order != bundle_id],
        bundle_id
      )
      get(bundle_id, envir = private$items, inherits = FALSE)
    },

    discard = function(bundle_id) {
      if (
        !is_handoff_store_id(bundle_id) ||
          !exists(bundle_id, envir = private$items, inherits = FALSE)
      ) {
        return(NULL)
      }
      bundle <- get(bundle_id, envir = private$items, inherits = FALSE)
      rm(list = bundle_id, envir = private$items)
      private$order <- private$order[private$order != bundle_id]
      private$total_bytes <- private$total_bytes -
        handoff_bundle_byte_size(bundle@bundled_files)
      bundle
    },

    evict = function() {
      removed <- list()
      while (private$total_bytes > private$max_bytes) {
        bundle_id <- private$order[[1]]
        removed[[length(removed) + 1L]] <- self$discard(bundle_id)
      }
      removed
    }
  ),
  private = list(
    max_bytes = NULL,
    total_bytes = 0,
    items = NULL,
    order = character(),

    new_bundle_id = function() {
      repeat {
        bundle_id <- paste0(
          sample(c(0:9, letters[1:6]), 32L, replace = TRUE),
          collapse = ""
        )
        if (!exists(bundle_id, envir = private$items, inherits = FALSE)) {
          return(bundle_id)
        }
      }
    }
  )
)

is_handoff_store_id <- function(value) {
  is.character(value) &&
    length(value) == 1L &&
    !is.na(value) &&
    nzchar(value)
}

check_handoff_store_state <- function(state) {
  if (!S7::S7_inherits(state, HandoffState)) {
    cli::cli_abort("{.arg state} must be a {.cls HandoffState}.")
  }
}

copy_handoff_bundle_files <- function(bundled_files) {
  if (!is.list(bundled_files)) {
    cli::cli_abort("{.arg bundled_files} must be a named list of raw vectors.")
  }
  if (length(bundled_files) == 0L) {
    cli::cli_abort(
      "Handoff data snapshot must contain at least one file."
    )
  }
  file_names <- names(bundled_files)
  if (
    length(bundled_files) > 0L &&
      (is.null(file_names) ||
        anyNA(file_names) ||
        any(!nzchar(file_names)) ||
        anyDuplicated(file_names))
  ) {
    cli::cli_abort(
      "{.arg bundled_files} must have unique, nonempty file names."
    )
  }
  if (!all(vapply(bundled_files, is.raw, logical(1)))) {
    cli::cli_abort("{.arg bundled_files} values must be raw vectors.")
  }
  lapply(bundled_files, \(value) value[])
}

handoff_bundle_byte_size <- function(bundled_files) {
  sum(vapply(bundled_files, length, numeric(1)))
}
