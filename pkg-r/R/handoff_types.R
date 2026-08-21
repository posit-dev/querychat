handoff_registry <- function() {
  load_handoff_registry()
}

load_handoff_registry <- function(
  path = system.file("handoff-formats.yml", package = "querychat")
) {
  check_scalar_character(path, "path")
  if (!file.exists(path)) {
    cli::cli_abort("Handoff registry file does not exist: {.path {path}}")
  }

  raw <- yaml::read_yaml(path)
  check_mapping(raw, "Handoff registry")
  check_exact_fields(raw, c("version", "formats"), "Handoff registry")

  if (!identical(raw$version, 1L)) {
    cli::cli_abort("Handoff registry version must be exactly 1.")
  }

  check_mapping(raw$formats, "Handoff registry formats")
  if (length(raw$formats) == 0L) {
    cli::cli_abort("Handoff registry formats must not be empty.")
  }

  formats <- Map(
    function(format_id, definition) {
      check_handoff_id(format_id, "format ID")
      check_mapping(definition, "Handoff registry format entry")
      check_exact_fields(
        definition,
        c("label", "description", "icon", "targets"),
        "Handoff registry format entry"
      )
      check_mapping(definition$targets, "Handoff registry targets")
      if (length(definition$targets) == 0L) {
        cli::cli_abort("Handoff registry targets must not be empty.")
      }

      targets <- Map(
        function(language, target) {
          check_language(language, "target language")
          check_mapping(target, "Handoff registry target")
          check_exact_fields(
            target,
            c("file_extension", "editor_language", "structure"),
            "Handoff registry target"
          )
          HandoffTarget(
            file_extension = target$file_extension,
            editor_language = target$editor_language,
            structure = target$structure
          )
        },
        names(definition$targets),
        definition$targets
      )
      names(targets) <- names(definition$targets)

      HandoffFormat(
        id = format_id,
        label = definition$label,
        description = definition$description,
        icon = definition$icon,
        targets = targets
      )
    },
    names(raw$formats),
    raw$formats
  )
  names(formats) <- names(raw$formats)
  formats
}

resolve_handoff_target <- function(
  format_id,
  language,
  registry = handoff_registry()
) {
  check_handoff_id(format_id, "format_id")
  check_language(language)

  format <- registry[[format_id]]
  if (is.null(format)) {
    cli::cli_abort("Unknown handoff format: {format_id}")
  }
  if (!S7::S7_inherits(format, HandoffFormat)) {
    cli::cli_abort("Handoff registry entry {.val {format_id}} is invalid.")
  }

  target <- format@targets[[language]]
  if (is.null(target)) {
    language_label <- switch(language, python = "Python", r = "R")
    cli::cli_abort(
      "Handoff format {.val {format@label}} does not support {language_label}."
    )
  }
  target
}

resolve_handoff_type <- function(
  format_id,
  language,
  registry = handoff_registry()
) {
  target <- resolve_handoff_target(format_id, language, registry)
  format <- registry[[format_id]]

  HandoffType(
    id = format@id,
    label = format@label,
    icon = format@icon,
    language = language,
    file_extension = target@file_extension,
    editor_language = target@editor_language,
    structure = target@structure
  )
}

parse_handoff_generate_request <- function(value, default_type_id) {
  check_handoff_id(default_type_id, "default_type_id")

  if (!is.list(value)) {
    return(HandoffGenerateRequest(type_id = default_type_id))
  }

  check_payload_fields(
    value,
    optional = c("selected_ids", "type", "language", "freeform"),
    context = "Handoff generate payload"
  )

  selected_ids <- payload_character_vector(value, "selected_ids")
  type_id <- payload_value(value, "type", "")
  language <- payload_value(value, "language", "")
  freeform <- payload_value(value, "freeform", "")

  check_character_vector_field(selected_ids, "selected_ids")
  check_scalar_field(type_id, "type", allow_empty = TRUE)
  check_scalar_field(language, "language", allow_empty = TRUE)
  check_scalar_field(freeform, "freeform", allow_empty = TRUE)

  if (!nzchar(type_id)) {
    type_id <- default_type_id
  }

  HandoffGenerateRequest(
    selected_ids = selected_ids,
    type_id = type_id,
    language = language,
    freeform = trimws(freeform)
  )
}

parse_handoff_recommendation <- function(
  value,
  allowed_item_ids,
  allowed_format_ids
) {
  check_character_allowlist(allowed_item_ids, "allowed_item_ids")
  check_character_allowlist(allowed_format_ids, "allowed_format_ids")
  check_payload_fields(
    value,
    required = c("selected_ids", "format_id"),
    optional = "directions",
    context = "Handoff recommendation"
  )

  selected_ids <- value$selected_ids
  format_id <- value$format_id
  directions <- optional_payload_value(value, "directions", "")

  check_character_vector_field(selected_ids, "selected_ids")
  check_scalar_field(format_id, "format_id")
  check_scalar_field(directions, "directions", allow_empty = TRUE)
  check_runtime_values(
    selected_ids,
    allowed_item_ids,
    "selected_ids",
    "item ID"
  )
  check_runtime_values(
    format_id,
    allowed_format_ids,
    "format_id",
    "format ID"
  )

  HandoffRecommendation(
    selected_ids = selected_ids[!duplicated(selected_ids)],
    format_id = format_id,
    directions = directions
  )
}

parse_handoff_result <- function(
  value,
  allowed_table_names,
  allowed_languages
) {
  check_character_allowlist(allowed_table_names, "allowed_table_names")
  check_character_allowlist(allowed_languages, "allowed_languages")
  if (!all(allowed_languages %in% c("python", "r"))) {
    cli::cli_abort(
      "{.arg allowed_languages} may contain only {.val python} and {.val r}."
    )
  }

  check_payload_fields(
    value,
    required = c("source", "language", "referenced_tables"),
    optional = c(
      "summary",
      "install_instructions",
      "run_instructions"
    ),
    context = "Handoff result"
  )

  source <- value$source
  language <- value$language
  summary <- optional_payload_value(value, "summary", "")
  install_instructions <- optional_payload_value(
    value,
    "install_instructions",
    ""
  )
  run_instructions <- optional_payload_value(value, "run_instructions", "")
  referenced_tables <- value$referenced_tables

  check_scalar_field(source, "source", allow_empty = TRUE)
  check_scalar_field(language, "language")
  check_scalar_field(summary, "summary", allow_empty = TRUE)
  check_scalar_field(
    install_instructions,
    "install_instructions",
    allow_empty = TRUE
  )
  check_scalar_field(
    run_instructions,
    "run_instructions",
    allow_empty = TRUE
  )
  check_character_vector_field(referenced_tables, "referenced_tables")
  check_runtime_values(
    language,
    allowed_languages,
    "language",
    "language"
  )
  check_runtime_values(
    referenced_tables,
    allowed_table_names,
    "referenced_tables",
    "table name"
  )

  HandoffResult(
    source = source,
    language = language,
    summary = summary,
    install_instructions = install_instructions,
    run_instructions = run_instructions,
    referenced_tables = referenced_tables
  )
}

parse_handoff_freeform_metadata <- function(value) {
  check_payload_fields(
    value,
    required = c("file_extension", "editor_language"),
    context = "Handoff freeform metadata"
  )

  file_extension <- value$file_extension
  editor_language <- value$editor_language
  check_scalar_field(file_extension, "file_extension")
  check_scalar_field(editor_language, "editor_language")

  if (!startsWith(file_extension, ".")) {
    file_extension <- paste0(".", file_extension)
  }
  if (!is.null(validate_file_extension(file_extension))) {
    cli::cli_abort(
      "{.field file_extension} must be a safe file extension."
    )
  }

  list(
    file_extension = file_extension,
    editor_language = editor_language
  )
}

handoff_state_record <- function(state) {
  if (!S7::S7_inherits(state, HandoffState)) {
    cli::cli_abort("{.arg state} must be a <HandoffState> object.")
  }

  record <- list(
    version = 1L,
    handoff_id = state@handoff_id,
    handoff_type = handoff_type_record(state@handoff_type),
    system_prompt = state@system_prompt,
    source = state@source,
    turns = lapply(state@turns, handoff_turn_record),
    summary = state@summary,
    install_instructions = state@install_instructions,
    run_instructions = state@run_instructions,
    referenced_tables = state@referenced_tables,
    bundled_tables = state@bundled_tables,
    bundle_id = state@bundle_id,
    data_instructions = state@data_instructions
  )
  check_handoff_state_record_values(record)
  handoff_type_from_record(record$handoff_type)
  check_plain_list(
    record$turns,
    "Handoff state record `turns`",
    named = FALSE
  )
  check_handoff_turn_records(record$turns)
  record
}

handoff_state_from_record <- function(value, tools = list()) {
  check_plain_list(value, "Handoff state record", named = TRUE)
  check_exact_fields(
    value,
    c(
      "version",
      "handoff_id",
      "handoff_type",
      "system_prompt",
      "source",
      "turns",
      "summary",
      "install_instructions",
      "run_instructions",
      "referenced_tables",
      "bundled_tables",
      "bundle_id",
      "data_instructions"
    ),
    "Handoff state record"
  )
  if (!identical(value$version, 1L)) {
    cli::cli_abort("Handoff state record version must be exactly 1.")
  }
  check_handoff_state_record_values(value)
  handoff_type <- handoff_type_from_record(value$handoff_type)
  check_plain_list(
    value$turns,
    "Handoff state record `turns`",
    named = FALSE
  )
  check_handoff_turn_records(value$turns)
  turns <- lapply(
    value$turns,
    ellmer::contents_replay,
    tools = tools
  )

  HandoffState(
    handoff_id = value$handoff_id,
    handoff_type = handoff_type,
    system_prompt = value$system_prompt,
    source = value$source,
    turns = turns,
    summary = value$summary,
    install_instructions = value$install_instructions,
    run_instructions = value$run_instructions,
    referenced_tables = value$referenced_tables,
    bundled_tables = value$bundled_tables,
    bundle_id = value$bundle_id,
    data_instructions = value$data_instructions
  )
}

HandoffTarget <- S7::new_class(
  "HandoffTarget",
  properties = list(
    file_extension = S7::class_character,
    editor_language = S7::class_character,
    structure = S7::class_character
  ),
  validator = function(self) validate_handoff_target(self)
)

HandoffFormat <- S7::new_class(
  "HandoffFormat",
  properties = list(
    id = S7::class_character,
    label = S7::class_character,
    description = S7::class_character,
    icon = S7::class_character,
    targets = S7::class_list
  ),
  validator = function(self) validate_handoff_format(self)
)

HandoffType <- S7::new_class(
  "HandoffType",
  properties = list(
    id = S7::class_character,
    label = S7::class_character,
    icon = S7::class_character,
    language = S7::class_character,
    file_extension = S7::class_character,
    editor_language = S7::class_character,
    structure = S7::class_character
  ),
  validator = function(self) validate_handoff_type(self)
)

HandoffGalleryItem <- S7::new_class(
  "HandoffGalleryItem",
  abstract = TRUE,
  properties = list(
    id = S7::class_character,
    title = S7::class_character
  ),
  validator = function(self) validate_handoff_gallery_item(self)
)

HandoffQueryItem <- S7::new_class(
  "HandoffQueryItem",
  parent = HandoffGalleryItem,
  properties = list(
    sql = S7::class_character,
    preview_html = S7::new_property(S7::class_any, default = NULL)
  ),
  validator = function(self) validate_handoff_query_item(self)
)

HandoffVizItem <- S7::new_class(
  "HandoffVizItem",
  parent = HandoffGalleryItem,
  properties = list(
    thumbnail = S7::new_property(S7::class_any, default = NULL),
    ggsql = S7::class_character
  ),
  validator = function(self) validate_handoff_viz_item(self)
)

HandoffGenerateRequest <- S7::new_class(
  "HandoffGenerateRequest",
  properties = list(
    selected_ids = S7::new_property(
      S7::class_character,
      default = character()
    ),
    type_id = S7::new_property(S7::class_character, default = ""),
    language = S7::new_property(S7::class_character, default = ""),
    freeform = S7::new_property(S7::class_character, default = "")
  ),
  validator = function(self) validate_handoff_generate_request(self)
)

HandoffRecommendation <- S7::new_class(
  "HandoffRecommendation",
  properties = list(
    selected_ids = S7::class_character,
    format_id = S7::class_character,
    directions = S7::new_property(S7::class_character, default = "")
  ),
  validator = function(self) validate_handoff_recommendation(self)
)

HandoffResult <- S7::new_class(
  "HandoffResult",
  properties = list(
    source = S7::class_character,
    language = S7::class_character,
    summary = S7::new_property(S7::class_character, default = ""),
    install_instructions = S7::new_property(
      S7::class_character,
      default = ""
    ),
    run_instructions = S7::new_property(S7::class_character, default = ""),
    referenced_tables = S7::new_property(
      S7::class_character,
      default = character()
    )
  ),
  validator = function(self) validate_handoff_result(self)
)

HandoffState <- S7::new_class(
  "HandoffState",
  properties = list(
    handoff_id = S7::class_character,
    handoff_type = HandoffType,
    system_prompt = S7::class_character,
    source = S7::class_character,
    turns = S7::new_property(S7::class_list, default = list()),
    summary = S7::new_property(S7::class_character, default = ""),
    install_instructions = S7::new_property(
      S7::class_character,
      default = ""
    ),
    run_instructions = S7::new_property(S7::class_character, default = ""),
    referenced_tables = S7::new_property(
      S7::class_character,
      default = character()
    ),
    bundled_tables = S7::new_property(
      S7::class_character,
      default = character()
    ),
    bundle_id = S7::new_property(S7::class_any, default = NULL),
    data_instructions = S7::new_property(S7::class_character, default = "")
  ),
  validator = function(self) validate_handoff_state(self)
)

HandoffBundle <- S7::new_class(
  "HandoffBundle",
  properties = list(
    bundle_id = S7::class_character,
    bundled_files = S7::class_list
  ),
  validator = function(self) validate_handoff_bundle(self)
)

validate_handoff_target <- function(self) {
  c(
    validate_file_extension(self@file_extension),
    validate_scalar_character(self@editor_language, "@editor_language"),
    validate_structure(self@structure)
  )
}

validate_handoff_format <- function(self) {
  problems <- c(
    validate_id(self@id, "@id"),
    validate_scalar_character(self@label, "@label"),
    validate_scalar_character(self@description, "@description"),
    validate_icon(self@icon)
  )

  if (length(self@targets) == 0L) {
    problems <- c(problems, "@targets must not be empty")
  } else {
    target_names <- names(self@targets)
    if (
      is.null(target_names) ||
        anyNA(target_names) ||
        any(!nzchar(target_names)) ||
        anyDuplicated(target_names)
    ) {
      problems <- c(
        problems,
        "@targets must be a uniquely named list of languages"
      )
    } else if (!all(target_names %in% c("python", "r"))) {
      problems <- c(problems, "@targets names must be `python` or `r`")
    }

    valid_targets <- vapply(
      self@targets,
      S7::S7_inherits,
      logical(1),
      class = HandoffTarget
    )
    if (!all(valid_targets)) {
      problems <- c(problems, "@targets values must be <HandoffTarget> objects")
    }
  }

  problems
}

validate_handoff_type <- function(self) {
  c(
    validate_id(self@id, "@id"),
    validate_scalar_character(self@label, "@label"),
    validate_icon(self@icon),
    validate_language(self@language),
    validate_file_extension(self@file_extension),
    validate_scalar_character(self@editor_language, "@editor_language"),
    validate_structure(self@structure)
  )
}

validate_handoff_gallery_item <- function(self) {
  c(
    validate_id(self@id, "@id"),
    validate_scalar_character(self@title, "@title")
  )
}

validate_handoff_query_item <- function(self) {
  c(
    validate_scalar_character(self@sql, "@sql"),
    validate_nullable_character(self@preview_html, "@preview_html")
  )
}

validate_handoff_viz_item <- function(self) {
  c(
    validate_nullable_character(self@thumbnail, "@thumbnail"),
    validate_scalar_character(self@ggsql, "@ggsql")
  )
}

validate_handoff_generate_request <- function(self) {
  c(
    validate_character_vector(self@selected_ids, "@selected_ids"),
    if (identical(self@type_id, "")) {
      NULL
    } else {
      validate_id(self@type_id, "@type_id")
    },
    if (identical(self@language, "")) {
      NULL
    } else {
      validate_language(self@language)
    },
    validate_scalar_character(self@freeform, "@freeform", allow_empty = TRUE)
  )
}

validate_handoff_recommendation <- function(self) {
  c(
    validate_character_vector(self@selected_ids, "@selected_ids"),
    validate_id(self@format_id, "@format_id"),
    validate_scalar_character(
      self@directions,
      "@directions",
      allow_empty = TRUE
    )
  )
}

validate_handoff_result <- function(self) {
  c(
    validate_scalar_character(self@source, "@source", allow_empty = TRUE),
    validate_language(self@language),
    validate_scalar_character(self@summary, "@summary", allow_empty = TRUE),
    validate_scalar_character(
      self@install_instructions,
      "@install_instructions",
      allow_empty = TRUE
    ),
    validate_scalar_character(
      self@run_instructions,
      "@run_instructions",
      allow_empty = TRUE
    ),
    validate_character_vector(self@referenced_tables, "@referenced_tables")
  )
}

validate_handoff_state <- function(self) {
  problems <- c(
    validate_id(self@handoff_id, "@handoff_id"),
    validate_scalar_character(
      self@system_prompt,
      "@system_prompt",
      allow_empty = TRUE
    ),
    validate_scalar_character(self@source, "@source", allow_empty = TRUE),
    validate_scalar_character(self@summary, "@summary", allow_empty = TRUE),
    validate_scalar_character(
      self@install_instructions,
      "@install_instructions",
      allow_empty = TRUE
    ),
    validate_scalar_character(
      self@run_instructions,
      "@run_instructions",
      allow_empty = TRUE
    ),
    validate_character_vector(self@referenced_tables, "@referenced_tables"),
    validate_character_vector(self@bundled_tables, "@bundled_tables"),
    validate_nullable_id(self@bundle_id, "@bundle_id"),
    validate_scalar_character(
      self@data_instructions,
      "@data_instructions",
      allow_empty = TRUE
    )
  )

  valid_turns <- vapply(
    self@turns,
    S7::S7_inherits,
    logical(1),
    class = ellmer::Turn
  )
  if (!all(valid_turns)) {
    problems <- c(problems, "@turns values must be <ellmer::Turn> objects")
  }

  problems
}

validate_handoff_bundle <- function(self) {
  problems <- validate_id(self@bundle_id, "@bundle_id")
  if (length(self@bundled_files) == 0L) {
    return(problems)
  }

  file_names <- names(self@bundled_files)
  if (
    is.null(file_names) ||
      anyNA(file_names) ||
      any(!nzchar(file_names)) ||
      anyDuplicated(file_names)
  ) {
    problems <- c(
      problems,
      "@bundled_files must be a uniquely named list of files"
    )
  }
  if (!all(vapply(self@bundled_files, is.raw, logical(1)))) {
    problems <- c(problems, "@bundled_files values must be raw vectors")
  }
  problems
}

validate_scalar_character <- function(value, property, allow_empty = FALSE) {
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    return(paste0(property, " must be a single non-missing string"))
  }
  if (!allow_empty && !nzchar(trimws(value))) {
    return(paste0(property, " must not be empty"))
  }
  NULL
}

validate_nullable_character <- function(value, property) {
  if (is.null(value)) {
    return(NULL)
  }
  validate_scalar_character(value, property, allow_empty = TRUE)
}

validate_character_vector <- function(value, property) {
  if (!is.character(value) || anyNA(value)) {
    return(paste0(
      property,
      " must be a character vector without missing values"
    ))
  }
  if (any(!nzchar(trimws(value)))) {
    return(paste0(property, " values must not be empty"))
  }
  NULL
}

validate_id <- function(value, property) {
  scalar_problem <- validate_scalar_character(value, property)
  if (!is.null(scalar_problem)) {
    return(scalar_problem)
  }
  if (!grepl("^[a-z0-9]+(?:-[a-z0-9]+)*$", value)) {
    return(
      paste0(
        property,
        " must contain lowercase letters, numbers, and single hyphens"
      )
    )
  }
  NULL
}

validate_nullable_id <- function(value, property) {
  if (is.null(value)) {
    return(NULL)
  }
  validate_id(value, property)
}

validate_language <- function(value) {
  scalar_problem <- validate_scalar_character(value, "@language")
  if (!is.null(scalar_problem)) {
    return(scalar_problem)
  }
  if (!value %in% c("python", "r")) {
    return("@language must be `python` or `r`")
  }
  NULL
}

validate_structure <- function(value) {
  scalar_problem <- validate_scalar_character(value, "@structure")
  if (!is.null(scalar_problem)) {
    return(scalar_problem)
  }
  if (!value %in% c("text", "notebook-json")) {
    return("@structure must be `text` or `notebook-json`")
  }
  NULL
}

validate_file_extension <- function(value) {
  scalar_problem <- validate_scalar_character(value, "@file_extension")
  if (!is.null(scalar_problem)) {
    return(scalar_problem)
  }
  if (
    !grepl("^\\.[A-Za-z0-9][A-Za-z0-9._+-]*$", value) ||
      grepl("\\.\\.", value)
  ) {
    return(
      "@file_extension must start with a dot and contain only safe extension characters"
    )
  }
  NULL
}

validate_icon <- function(value) {
  scalar_problem <- validate_scalar_character(value, "@icon")
  if (!is.null(scalar_problem)) {
    return(scalar_problem)
  }

  valid <- tryCatch(
    {
      bsicons::bs_icon(value)
      TRUE
    },
    error = function(error) FALSE
  )
  if (!valid) {
    return("@icon must name a Bootstrap icon")
  }
  NULL
}

check_scalar_character <- function(value, name) {
  problem <- validate_scalar_character(value, paste0("`", name, "`"))
  if (!is.null(problem)) {
    cli::cli_abort(problem)
  }
}

check_handoff_id <- function(value, name) {
  problem <- validate_id(value, paste0("`", name, "`"))
  if (!is.null(problem)) {
    cli::cli_abort(problem)
  }
}

check_language <- function(value, name = "language") {
  problem <- validate_language(value)
  if (!is.null(problem)) {
    cli::cli_abort(
      "{.arg {name}} must be one of {.val python} or {.val r}."
    )
  }
}

check_mapping <- function(value, name) {
  if (!is.list(value) || is.null(names(value))) {
    cli::cli_abort("{name} must be a mapping.")
  }
  field_names <- names(value)
  if (
    anyNA(field_names) ||
      any(!nzchar(field_names)) ||
      anyDuplicated(field_names)
  ) {
    cli::cli_abort("{name} must have unique, nonempty field names.")
  }
}

check_exact_fields <- function(value, expected, name) {
  actual <- names(value)
  missing <- setdiff(expected, actual)
  extra <- setdiff(actual, expected)

  if (length(missing) > 0L) {
    cli::cli_abort(
      "{name} is missing required field{?s}: {.and {.val {missing}}}."
    )
  }
  if (length(extra) > 0L) {
    cli::cli_abort(
      "{name} has unexpected field{?s}: {.and {.val {extra}}}."
    )
  }
}

check_payload_fields <- function(
  value,
  required = character(),
  optional = character(),
  context
) {
  if (is.data.frame(value)) {
    cli::cli_abort("{context} must not be a data frame.")
  }
  if (!is.list(value)) {
    cli::cli_abort("{context} must be a named list.")
  }

  if (length(value) == 0L) {
    actual <- character()
  } else {
    actual <- names(value)
    if (
      is.null(actual) ||
        anyNA(actual) ||
        any(!nzchar(actual)) ||
        anyDuplicated(actual)
    ) {
      cli::cli_abort(
        "{context} must have unique, nonempty field names."
      )
    }
  }

  missing <- setdiff(required, actual)
  extra <- setdiff(actual, c(required, optional))
  if (length(missing) > 0L) {
    cli::cli_abort(
      "{context} is missing required field{?s}: {.and {.val {missing}}}."
    )
  }
  if (length(extra) > 0L) {
    cli::cli_abort(
      "{context} has unexpected field{?s}: {.and {.val {extra}}}."
    )
  }
}

payload_value <- function(value, name, default) {
  if (!name %in% names(value) || is.null(value[[name]])) {
    return(default)
  }
  value[[name]]
}

# Shiny's browser JSON deserialization keeps array-valued custom-message
# payload fields as plain lists of scalars (never simplified to an atomic
# vector), regardless of length. Flatten that shape before validating.
payload_character_vector <- function(value, name) {
  field <- payload_value(value, name, character())
  if (is.list(field)) {
    field <- unlist(field, use.names = FALSE) %||% character()
  }
  field
}

optional_payload_value <- function(value, name, default) {
  if (!name %in% names(value)) {
    return(default)
  }
  value[[name]]
}

check_scalar_field <- function(value, name, allow_empty = FALSE) {
  problem <- validate_scalar_character(
    value,
    paste0("`", name, "`"),
    allow_empty = allow_empty
  )
  if (!is.null(problem)) {
    cli::cli_abort(problem)
  }
}

check_character_vector_field <- function(value, name) {
  problem <- validate_character_vector(value, paste0("`", name, "`"))
  if (!is.null(problem)) {
    cli::cli_abort(problem)
  }
}

check_character_allowlist <- function(value, name) {
  problem <- validate_character_vector(value, paste0("`", name, "`"))
  if (!is.null(problem)) {
    cli::cli_abort(problem)
  }
  if (anyDuplicated(value)) {
    cli::cli_abort("{.arg {name}} must not contain duplicates.")
  }
}

check_runtime_values <- function(value, allowed, field, value_name) {
  invalid <- unique(value[!value %in% allowed])
  if (length(invalid) > 0L) {
    cli::cli_abort(
      "{.field {field}} contains unsupported {value_name}{?s}: {.and {.val {invalid}}}."
    )
  }
}

handoff_type_record <- function(handoff_type) {
  list(
    id = handoff_type@id,
    label = handoff_type@label,
    icon = handoff_type@icon,
    language = handoff_type@language,
    file_extension = handoff_type@file_extension,
    editor_language = handoff_type@editor_language,
    structure = handoff_type@structure
  )
}

handoff_type_from_record <- function(value) {
  check_plain_list(value, "Handoff type record", named = TRUE)
  check_exact_fields(
    value,
    c(
      "id",
      "label",
      "icon",
      "language",
      "file_extension",
      "editor_language",
      "structure"
    ),
    "Handoff type record"
  )
  lapply(value, check_handoff_record_data)

  HandoffType(
    id = value$id,
    label = value$label,
    icon = value$icon,
    language = value$language,
    file_extension = value$file_extension,
    editor_language = value$editor_language,
    structure = value$structure
  )
}

handoff_turn_record <- function(turn) {
  record <- ellmer::contents_record(turn)
  record$props$contents <- lapply(
    record$props$contents,
    normalize_handoff_content_record
  )
  record
}

normalize_handoff_content_record <- function(record) {
  if (
    identical(record$class, "ellmer::ContentToolResult") &&
      inherits(record$props$error, "condition")
  ) {
    record$props$error <- conditionMessage(record$props$error)
  }
  record
}

check_handoff_state_record_values <- function(value) {
  metadata_names <- c(
    "handoff_id",
    "system_prompt",
    "source",
    "summary",
    "install_instructions",
    "run_instructions",
    "referenced_tables",
    "bundled_tables",
    "bundle_id",
    "data_instructions"
  )
  lapply(value[metadata_names], check_handoff_record_data)

  check_handoff_id(value$handoff_id, "handoff_id")
  check_scalar_field(value$system_prompt, "system_prompt", allow_empty = TRUE)
  check_scalar_field(value$source, "source", allow_empty = TRUE)
  check_scalar_field(value$summary, "summary", allow_empty = TRUE)
  check_scalar_field(
    value$install_instructions,
    "install_instructions",
    allow_empty = TRUE
  )
  check_scalar_field(
    value$run_instructions,
    "run_instructions",
    allow_empty = TRUE
  )
  check_character_vector_field(
    value$referenced_tables,
    "referenced_tables"
  )
  check_character_vector_field(value$bundled_tables, "bundled_tables")
  bundle_id_problem <- validate_nullable_id(value$bundle_id, "`bundle_id`")
  if (!is.null(bundle_id_problem)) {
    cli::cli_abort(bundle_id_problem)
  }
  check_scalar_field(
    value$data_instructions,
    "data_instructions",
    allow_empty = TRUE
  )
  invisible(NULL)
}

check_handoff_turn_records <- function(turns) {
  lapply(turns, check_handoff_turn_record)
  invisible(NULL)
}

check_handoff_turn_record <- function(record) {
  check_plain_list(record, "Ellmer turn record", named = TRUE)
  check_exact_fields(
    record,
    c("version", "class", "props"),
    "Ellmer turn record"
  )
  check_handoff_ellmer_record_version(record$version, "Ellmer turn record")
  check_handoff_ellmer_record_class(
    record$class,
    c("ellmer::UserTurn", "ellmer::AssistantTurn")
  )
  class_name <- sub("ellmer::", "", record$class, fixed = TRUE)
  props_context <- paste("Ellmer", class_name, "props")
  check_plain_list(record$props, props_context, named = TRUE)
  expected_props <- switch(
    record$class,
    "ellmer::UserTurn" = "contents",
    "ellmer::AssistantTurn" = c(
      "contents",
      "json",
      "tokens",
      "cost",
      "duration",
      "finish_reason"
    )
  )
  check_exact_fields(record$props, expected_props, props_context)
  check_plain_list(
    record$props$contents,
    paste0(props_context, " `contents`"),
    named = FALSE
  )
  if (identical(record$class, "ellmer::AssistantTurn")) {
    check_plain_list(
      record$props$json,
      "Ellmer AssistantTurn prop `json`"
    )
    check_handoff_numeric_prop(
      record$props$tokens,
      "Ellmer AssistantTurn prop `tokens`",
      length = 3L
    )
    check_handoff_numeric_prop(
      record$props$cost,
      "Ellmer AssistantTurn prop `cost`",
      length = 1L,
      double_only = TRUE
    )
    check_handoff_numeric_prop(
      record$props$duration,
      "Ellmer AssistantTurn prop `duration`",
      length = 1L,
      double_only = TRUE
    )
    check_handoff_string_prop(
      record$props$finish_reason,
      "Ellmer AssistantTurn prop `finish_reason`",
      allow_na = TRUE
    )
  }
  lapply(record$props$contents, check_handoff_content_record)
  lapply(
    record$props[setdiff(names(record$props), "contents")],
    check_handoff_record_data
  )
  invisible(NULL)
}

check_handoff_content_record <- function(record) {
  check_plain_list(record, "Ellmer content record", named = TRUE)
  check_exact_fields(
    record,
    c("version", "class", "props"),
    "Ellmer content record"
  )
  check_handoff_ellmer_record_version(record$version, "Ellmer content record")
  check_handoff_ellmer_record_class(
    record$class,
    c(
      "ellmer::ContentText",
      "ellmer::ContentJson",
      "ellmer::ContentThinking",
      "ellmer::ContentToolRequest",
      "ellmer::ContentToolResult"
    )
  )
  class_name <- sub("ellmer::", "", record$class, fixed = TRUE)
  props_context <- paste("Ellmer", class_name, "props")
  check_plain_list(record$props, props_context, named = TRUE)
  if (identical(record$class, "ellmer::ContentJson")) {
    check_payload_fields(
      record$props,
      optional = c("data", "string"),
      context = props_context
    )
  } else if (identical(record$class, "ellmer::ContentToolResult")) {
    check_payload_fields(
      record$props,
      required = c("extra", "request"),
      optional = c("value", "error"),
      context = props_context
    )
  } else {
    expected_props <- switch(
      record$class,
      "ellmer::ContentText" = "text",
      "ellmer::ContentThinking" = c("thinking", "extra"),
      "ellmer::ContentToolRequest" = c(
        "id",
        "name",
        "arguments",
        "extra"
      )
    )
    check_exact_fields(record$props, expected_props, props_context)
  }

  if (identical(record$class, "ellmer::ContentText")) {
    check_handoff_string_prop(
      record$props$text,
      "Ellmer ContentText prop `text`"
    )
  } else if (identical(record$class, "ellmer::ContentJson")) {
    if ("string" %in% names(record$props)) {
      check_handoff_string_prop(
        record$props$string,
        "Ellmer ContentJson prop `string`"
      )
    }
  } else if (identical(record$class, "ellmer::ContentThinking")) {
    check_handoff_string_prop(
      record$props$thinking,
      "Ellmer ContentThinking prop `thinking`"
    )
    check_plain_list(
      record$props$extra,
      "Ellmer ContentThinking prop `extra`"
    )
  } else if (identical(record$class, "ellmer::ContentToolRequest")) {
    check_handoff_string_prop(
      record$props$id,
      "Ellmer ContentToolRequest prop `id`"
    )
    check_handoff_string_prop(
      record$props$name,
      "Ellmer ContentToolRequest prop `name`"
    )
    check_plain_list(
      record$props$arguments,
      "Ellmer ContentToolRequest prop `arguments`"
    )
    check_plain_list(
      record$props$extra,
      "Ellmer ContentToolRequest prop `extra`"
    )
  } else {
    check_plain_list(
      record$props$extra,
      "Ellmer ContentToolResult prop `extra`"
    )
    if ("error" %in% names(record$props)) {
      check_handoff_string_prop(
        record$props$error,
        "Ellmer ContentToolResult prop `error`"
      )
    }
  }

  if (
    identical(record$class, "ellmer::ContentToolResult") &&
      "request" %in% names(record$props)
  ) {
    check_plain_list(
      record$props$request,
      "Ellmer ContentToolResult prop `request`",
      named = TRUE
    )
    check_handoff_content_record(record$props$request)
    if (
      !identical(
        record$props$request$class,
        "ellmer::ContentToolRequest"
      )
    ) {
      cli::cli_abort(
        paste(
          "Ellmer ContentToolResult `request` must be",
          "an ellmer::ContentToolRequest record."
        )
      )
    }
  }
  lapply(
    record$props[setdiff(names(record$props), "request")],
    check_handoff_record_data
  )
  invisible(NULL)
}

check_handoff_ellmer_record_version <- function(value, context) {
  if (!identical(value, 1)) {
    cli::cli_abort("{context} version must be exactly 1.")
  }
}

check_handoff_string_prop <- function(value, context, allow_na = FALSE) {
  if (
    !is.character(value) ||
      length(value) != 1L ||
      !is.null(attributes(value)) ||
      (!allow_na && is.na(value))
  ) {
    qualifier <- if (allow_na) {
      "a single string or NA"
    } else {
      "a single non-missing string"
    }
    cli::cli_abort("{context} must be {qualifier}.")
  }
}

check_handoff_numeric_prop <- function(
  value,
  context,
  length,
  double_only = FALSE
) {
  valid_type <- if (double_only) {
    is.double(value)
  } else {
    is.integer(value) || is.double(value)
  }
  if (
    !valid_type ||
      base::length(value) != length ||
      !is.null(attributes(value)) ||
      any(is.infinite(value))
  ) {
    size <- switch(
      as.character(length),
      "1" = "a scalar numeric value",
      "3" = "a length-three numeric vector"
    )
    cli::cli_abort("{context} must be {size}.")
  }
}

check_handoff_ellmer_record_class <- function(value, allowed) {
  if (
    !is.character(value) ||
      length(value) != 1L ||
      is.na(value) ||
      !is.null(attributes(value))
  ) {
    cli::cli_abort(
      paste(
        "Handoff ellmer record class must be a single",
        "un-attributed string."
      )
    )
  }
  if (!value %in% allowed) {
    cli::cli_abort(
      "Unsupported handoff ellmer record class: {.val {value}}."
    )
  }
}

check_handoff_record_data <- function(value) {
  if (is.null(value)) {
    return(invisible(NULL))
  }

  if (is.list(value)) {
    attribute_names <- names(attributes(value))
    if (
      is.object(value) ||
        (!is.null(attribute_names) &&
          !identical(attribute_names, "names"))
    ) {
      abort_non_inert_handoff_record()
    }
    value_names <- names(value)
    if (
      !is.null(value_names) &&
        (anyNA(value_names) ||
          any(!nzchar(value_names)) ||
          anyDuplicated(value_names))
    ) {
      abort_non_inert_handoff_record()
    }
    if (all(c("version", "class", "props") %in% value_names)) {
      cli::cli_abort(
        "Handoff ellmer record data must not contain nested recorded objects."
      )
    }
    for (item in value) {
      check_handoff_record_data(item)
    }
    return(invisible(NULL))
  }

  if (
    typeof(value) %in%
      c("logical", "integer", "double", "character") &&
      is.null(attributes(value)) &&
      !(is.double(value) &&
        any(is.nan(value) | is.infinite(value)))
  ) {
    return(invisible(NULL))
  }

  abort_non_inert_handoff_record()
}

abort_non_inert_handoff_record <- function() {
  cli::cli_abort(
    paste(
      "Handoff records may contain only inert JSON values",
      "and plain lists."
    )
  )
}

check_plain_list <- function(value, context, named = NULL) {
  attribute_names <- names(attributes(value))
  if (
    !is.list(value) ||
      is.object(value) ||
      (!is.null(attribute_names) &&
        !identical(attribute_names, "names"))
  ) {
    if (identical(named, FALSE)) {
      cli::cli_abort("{context} must be an unnamed plain list.")
    }
    cli::cli_abort("{context} must be a plain list.")
  }
  if (identical(named, FALSE) && !is.null(names(value))) {
    cli::cli_abort("{context} must be an unnamed plain list.")
  }
  if (identical(named, TRUE)) {
    check_mapping(value, context)
  }
  invisible(NULL)
}
