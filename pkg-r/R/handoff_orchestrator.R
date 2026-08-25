HandoffOrchestrator <- R6::R6Class(
  "HandoffOrchestrator",
  public = list(
    initialize = function(
      chat,
      data_sources,
      executor,
      view,
      store = HandoffStore$new(),
      bundle_store = HandoffBundleStore$new(),
      max_bundle_bytes = 5 * 1024^2
    ) {
      private$chat <- if (inherits(chat, "HandoffChat")) {
        chat
      } else {
        HandoffChat$new(chat)
      }
      private$data_sources <- data_sources
      private$executor <- executor
      private$view <- view
      private$store <- store
      private$bundle_store <- bundle_store
      private$max_bundle_bytes <- max_bundle_bytes
      private$registry <- handoff_registry()
    },

    snapshot = function() {
      private$store$snapshot()
    },

    close_panel = function() {
      private$view$set_panel_open(FALSE)
      invisible(NULL)
    },

    restore_snapshot = function(saved) {
      states <- lapply(saved, handoff_state_from_record)
      removed <- private$store$replace(states)
      private$discard_unreferenced_bundles(
        lapply(removed, \(state) state@bundle_id)
      )
      invisible(NULL)
    },

    open_modal = function() {
      items <- extract_handoff_gallery_items(private$chat$history_turns())
      private$gallery_items <- items
      private$view$show_modal(items)
      items
    },

    recommend = function(items) {
      item_ids <- vapply(items, \(item) item@id, character(1))
      format_ids <- names(private$registry)
      prompt <- build_handoff_recommend_prompt(items, private$registry)
      type <- handoff_recommendation_type(item_ids, format_ids)

      promises::then(
        private$chat$ask(prompt, type),
        function(value) {
          parse_handoff_recommendation(value, item_ids, format_ids)
        }
      )
    },

    prepare_generation = function(request, directions) {
      coro::async(function() {
        check_handoff_generation_request(request)
        check_handoff_directions(directions)
        language <- request@language
        if (!nzchar(language)) {
          cli::cli_abort(
            "Select R or Python before generating a handoff."
          )
        }

        if (identical(request@type_id, "other")) {
          freeform <- trimws(request@freeform)
          if (!nzchar(freeform)) {
            cli::cli_abort(
              "Enter a format name for {.val Other} before generating a handoff."
            )
          }
          metadata <- coro::await(private$chat$ask(
            paste0(
              "What file extension and editor language should be used for a '",
              freeform,
              "' handoff?"
            ),
            handoff_freeform_metadata_type()
          ))
          metadata <- parse_handoff_freeform_metadata(metadata)
          handoff_format <- NULL
          handoff_type <- HandoffType(
            id = "other",
            label = freeform,
            icon = "file-earmark-code",
            language = language,
            file_extension = metadata$file_extension,
            editor_language = metadata$editor_language,
            structure = "text"
          )
        } else {
          handoff_format <- private$registry[[request@type_id]]
          if (is.null(handoff_format)) {
            cli::cli_abort(
              "Unknown handoff format: {request@type_id}"
            )
          }
          handoff_type <- resolve_handoff_type(
            handoff_format@id,
            language,
            private$registry
          )
        }

        selected_items <- Filter(
          function(item) item@id %in% request@selected_ids,
          private$gallery_items
        )
        schema <- private$data_source_schemas()
        data_catalog <- prepare_handoff_data(
          private$data_sources,
          language
        )
        format_id <- "other"
        if (!is.null(handoff_format)) {
          format_id <- handoff_format@id
        }
        system_prompt <- build_handoff_system_prompt(
          selected_items = selected_items,
          schema = schema,
          custom_directions = directions,
          format_id = format_id,
          language = language,
          data_instructions = data_catalog$prompt_instructions
        )
        user_prompt <- build_freeform_handoff_user_prompt(
          handoff_type@label,
          language
        )
        if (!is.null(handoff_format)) {
          user_prompt <- build_handoff_user_prompt(
            handoff_format,
            language
          )
        }

        list(
          handoff_format = handoff_format,
          handoff_type = handoff_type,
          system_prompt = system_prompt,
          user_prompt = user_prompt,
          schema = schema,
          data_catalog = data_catalog,
          result_type = handoff_result_type(
            names(private$data_sources),
            language,
            require_run_instructions = TRUE
          )
        )
      })()
    },

    generate = function(request, directions, handoff_id) {
      coro::async(function() {
        check_handoff_id(handoff_id, "handoff_id")
        plan <- coro::await(self$prepare_generation(request, directions))
        private$view$remove_modal()
        private$view$clear_source(plan$handoff_type@editor_language)
        committed <- FALSE
        staged_bundle_id <- NULL

        tryCatch(
          {
            generated <- coro::await(private$stream_validated(
              prompt = plan$user_prompt,
              turns = list(),
              system_prompt = plan$system_prompt,
              result_type = plan$result_type,
              handoff_type = plan$handoff_type
            ))
            materialized <- coro::await(private$materialize_generated(
              generated,
              data_catalog = plan$data_catalog,
              schema_provider = function() plan$schema,
              result_type = plan$result_type
            ))
            generated <- materialized$generated
            data_context <- materialized$data_context
            if (length(data_context$bundled_files) > 0L) {
              staged_bundle_id <- private$bundle_store$stage(
                data_context$bundled_files
              )@bundle_id
            }
            result <- generated$result
            state <- HandoffState(
              handoff_id = handoff_id,
              handoff_type = generated$handoff_type,
              system_prompt = plan$system_prompt,
              source = result@source,
              turns = generated$turns,
              summary = result@summary,
              install_instructions = result@install_instructions,
              run_instructions = result@run_instructions,
              referenced_tables = result@referenced_tables,
              bundled_tables = data_context$bundled_tables,
              bundle_id = staged_bundle_id,
              data_instructions = data_context$data_instructions
            )
            private$view$show_handoff(
              state,
              download_available = FALSE
            )
            removed <- private$store$remember(state)
            committed <- TRUE
            # Append the chat pill only after the commit succeeds so a
            # failure cannot leave an orphaned, permanently dead pill.
            private$view$append_pill(
              handoff_id,
              generated$handoff_type,
              result@summary
            )
            private$discard_unreferenced_bundles(
              lapply(removed, \(removed_state) removed_state@bundle_id)
            )
            private$bundle_store$evict()
            tryCatch(
              private$view$show_handoff(
                state,
                download_available = private$download_available(state)
              ),
              error = function(error) NULL
            )
          },
          error = function(error) {
            if (committed) {
              # The handoff is committed: post-commit cleanup or view
              # failures must not be reported as a failed generation.
              cli::cli_warn(c(
                "!" = "The handoff was saved, but a post-commit step failed:",
                "x" = conditionMessage(error)
              ))
              return(invisible(NULL))
            }
            tryCatch(
              private$bundle_store$discard(staged_bundle_id),
              error = function(discard_error) NULL
            )
            tryCatch(
              private$view$clear_source("plain"),
              error = function(clear_error) NULL
            )
            stop(error)
          }
        )
        invisible(NULL)
      })()
    },

    revise = function(handoff_id, instructions) {
      coro::async(function() {
        if (!private$store$has(handoff_id)) {
          return(FALSE)
        }
        # Mirror Python's `if not instructions: return`: the revise textarea
        # can report NULL before it is bound client-side, and blank
        # instructions are a quiet no-op rather than an error.
        if (
          !is.character(instructions) ||
            length(instructions) != 1L ||
            is.na(instructions) ||
            !nzchar(trimws(instructions))
        ) {
          return(FALSE)
        }
        state <- private$store$get(handoff_id)

        language <- state@handoff_type@language
        result_type <- handoff_result_type(
          names(private$data_sources),
          language,
          require_run_instructions = TRUE
        )
        data_catalog <- prepare_handoff_data(private$data_sources, language)
        staged_bundle_id <- NULL
        replacement_saved <- FALSE

        tryCatch(
          {
            generated <- coro::await(private$stream_validated(
              prompt = instructions,
              turns = state@turns,
              system_prompt = state@system_prompt,
              result_type = result_type,
              handoff_type = state@handoff_type
            ))
            result <- generated$result
            if (!identical(result@language, language)) {
              cli::cli_abort("Revised handoff changed its language.")
            }
            materialized <- coro::await(private$materialize_generated(
              generated,
              data_catalog = data_catalog,
              schema_provider = function() private$data_source_schemas(),
              result_type = result_type
            ))
            generated <- materialized$generated
            data_context <- materialized$data_context
            if (length(data_context$bundled_files) > 0L) {
              staged_bundle_id <- private$bundle_store$stage(
                data_context$bundled_files
              )@bundle_id
            }
            result <- generated$result
            replacement <- HandoffState(
              handoff_id = state@handoff_id,
              handoff_type = state@handoff_type,
              system_prompt = state@system_prompt,
              source = result@source,
              turns = generated$turns,
              summary = result@summary,
              install_instructions = result@install_instructions,
              run_instructions = result@run_instructions,
              referenced_tables = result@referenced_tables,
              bundled_tables = data_context$bundled_tables,
              bundle_id = staged_bundle_id,
              data_instructions = data_context$data_instructions
            )
            private$view$show_handoff(
              replacement,
              download_available = private$download_available(replacement)
            )
            removed <- private$store$remember(replacement)
            replacement_saved <- TRUE
            private$discard_unreferenced_bundles(
              lapply(removed, \(removed_state) removed_state@bundle_id)
            )
            private$bundle_store$evict()
          },
          error = function(error) {
            if (replacement_saved) {
              # The replacement is committed: post-commit cleanup failures
              # must not revert the view to the pre-revision state or be
              # reported as a failed revision.
              cli::cli_warn(c(
                "!" = paste(
                  "The revised handoff was saved,",
                  "but a post-commit step failed:"
                ),
                "x" = conditionMessage(error)
              ))
              return(invisible(NULL))
            }
            tryCatch(
              private$bundle_store$discard(staged_bundle_id),
              error = function(discard_error) NULL
            )
            tryCatch(
              private$view$show_handoff(
                state,
                download_available = private$download_available(state)
              ),
              error = function(view_error) NULL
            )
            stop(error)
          }
        )
        TRUE
      })()
    },

    show = function(handoff_id) {
      state <- private$store$get(handoff_id)
      if (is.null(state)) {
        return(FALSE)
      }
      private$view$show_handoff(
        state,
        download_available = private$download_available(state)
      )
      TRUE
    },

    build_download = function(handoff_id) {
      state <- private$store$get(handoff_id)
      if (is.null(state)) {
        return(NULL)
      }

      bundled_files <- list()
      if (is.null(state@bundle_id)) {
        if (length(state@bundled_tables) > 0L) {
          abort_handoff_snapshot_unavailable()
        }
      } else {
        bundle <- private$bundle_store$get(state@bundle_id)
        if (is.null(bundle)) {
          abort_handoff_snapshot_unavailable()
        }
        bundled_files <- bundle@bundled_files
      }

      source_filename <- paste0("handoff", state@handoff_type@file_extension)
      readme <- build_handoff_readme(
        handoff_type = state@handoff_type,
        source_filename = source_filename,
        summary = state@summary,
        install_instructions = state@install_instructions,
        run_instructions = state@run_instructions,
        data_instructions = state@data_instructions,
        bundled_files = names(bundled_files)
      )
      build_handoff_zip(
        source = state@source,
        source_filename = source_filename,
        readme = readme,
        bundled_files = bundled_files
      )
    }
  ),
  private = list(
    chat = NULL,
    data_sources = NULL,
    executor = NULL,
    view = NULL,
    store = NULL,
    bundle_store = NULL,
    max_bundle_bytes = NULL,
    registry = NULL,
    gallery_items = list(),

    data_source_schemas = function() {
      schemas <- vapply(
        names(private$data_sources),
        function(table_name) {
          private$executor$get_schema(
            table_name,
            categorical_threshold = 20
          )
        },
        character(1)
      )
      paste(schemas, collapse = "\n\n")
    },

    stream_validated = function(
      prompt,
      turns,
      system_prompt,
      result_type,
      handoff_type
    ) {
      coro::async(function() {
        generated <- coro::await(private$chat$stream(
          prompt,
          turns = turns,
          system_prompt = system_prompt,
          type = result_type,
          view = private$view
        ))
        validation_error <- tryCatch(
          {
            validate_handoff_source(
              generated$result@source,
              handoff_type
            )
            NULL
          },
          error = function(error) error
        )
        if (!is.null(validation_error)) {
          generated <- coro::await(private$chat$stream(
            build_handoff_repair_prompt(
              validation_error,
              handoff_type
            ),
            turns = generated$turns,
            system_prompt = system_prompt,
            type = handoff_result_type(
              names(private$data_sources),
              handoff_type@language,
              require_run_instructions = TRUE
            ),
            view = private$view
          ))
          if (
            !identical(
              generated$result@language,
              handoff_type@language
            )
          ) {
            cli::cli_abort("Repaired handoff changed its language.")
          }
          validate_handoff_source(
            generated$result@source,
            handoff_type
          )
        }
        list(
          result = generated$result,
          turns = generated$turns,
          handoff_type = handoff_type
        )
      })()
    },

    materialize_generated = function(
      generated,
      data_catalog,
      schema_provider,
      result_type
    ) {
      coro::async(function() {
        data_context <- materialize_handoff_data(
          data_catalog,
          private$data_sources,
          generated$result@referenced_tables,
          max_bytes = private$max_bundle_bytes
        )
        if (length(data_context$externalized_dataframe_tables) == 0L) {
          return(list(generated = generated, data_context = data_context))
        }

        expected_tables <- sort(unique(generated$result@referenced_tables))
        repair_system_prompt <- build_external_data_repair_system_prompt(
          handoff_type = generated$handoff_type,
          schema = schema_provider(),
          data_instructions = data_context$data_instructions,
          referenced_tables = generated$result@referenced_tables
        )
        repaired <- coro::await(private$chat$stream(
          "Return the complete corrected handoff now.",
          turns = generated$turns,
          system_prompt = repair_system_prompt,
          type = result_type,
          view = private$view
        ))
        repaired_result <- repaired$result
        if (
          !identical(
            repaired_result@language,
            generated$handoff_type@language
          )
        ) {
          cli::cli_abort("Corrected handoff changed its language.")
        }
        if (
          !identical(
            sort(unique(repaired_result@referenced_tables)),
            expected_tables
          )
        ) {
          cli::cli_abort("Corrected handoff changed its referenced-table set.")
        }
        validate_handoff_source(
          repaired_result@source,
          generated$handoff_type
        )

        list(
          generated = list(
            result = repaired_result,
            turns = repaired$turns,
            handoff_type = generated$handoff_type
          ),
          data_context = data_context
        )
      })()
    },

    discard_unreferenced_bundles = function(bundle_ids) {
      retained <- vapply(
        Filter(
          \(state) !is.null(state@bundle_id),
          private$store$values()
        ),
        \(state) state@bundle_id,
        character(1)
      )
      candidates <- unique(unlist(bundle_ids, use.names = FALSE))
      for (bundle_id in setdiff(candidates, retained)) {
        private$bundle_store$discard(bundle_id)
      }
      invisible(NULL)
    },

    download_available = function(state) {
      if (is.null(state@bundle_id)) {
        return(length(state@bundled_tables) == 0L)
      }
      !is.null(private$bundle_store$get(state@bundle_id))
    }
  )
)

check_handoff_generation_request <- function(request) {
  if (!S7::S7_inherits(request, HandoffGenerateRequest)) {
    cli::cli_abort(
      "{.arg request} must be a {.cls HandoffGenerateRequest}."
    )
  }
}

abort_handoff_snapshot_unavailable <- function() {
  cli::cli_abort(
    "This handoff data snapshot is unavailable.",
    class = "querychat_handoff_snapshot_unavailable"
  )
}

check_handoff_directions <- function(directions) {
  if (
    !is.character(directions) ||
      length(directions) != 1L ||
      is.na(directions)
  ) {
    cli::cli_abort("{.arg directions} must be a single string.")
  }
}
