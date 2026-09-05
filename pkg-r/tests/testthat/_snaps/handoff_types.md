# HandoffGalleryItem / is abstract

    Code
      HandoffGalleryItem(id = "query-1", title = "Query")
    Condition
      Error in `S7::new_object()`:
      ! Can't construct an object from abstract class <HandoffGalleryItem>

# handoff_state_record() / rejects non-inert values preserved by ellmer records

    Code
      invisible(handoff_state_record(state))
    Condition
      Error in `abort_non_inert_handoff_record()`:
      ! Handoff records may contain only inert JSON values and plain lists.

# handoff_state_record() / requires a HandoffState input

    Code
      handoff_state_record(list())
    Condition
      Error in `handoff_state_record()`:
      ! `state` must be a <HandoffState> object.

# handoff_state_record() / rejects non-inert state metadata and named turns

    Code
      handoff_state_record(attributed_source)
    Condition
      Error in `abort_non_inert_handoff_record()`:
      ! Handoff records may contain only inert JSON values and plain lists.

# handoff_state_from_record() / rejects malformed ContentThinking

    Code
      handoff_state_from_record(malformed_thinking)
    Condition
      Error in `value[[3L]]()`:
      ! Ellmer turn record could not be replayed: <ellmer::ContentThinking> object properties are invalid: - @thinking must be <character>, not <double>

---

    Code
      handoff_state_from_record(nested_record)
    Condition
      Error in `check_handoff_record_data()`:
      ! Handoff ellmer record data must not contain nested recorded objects.

# handoff_state_from_record() / rejects unapproved classes before constructor resolution

    Code
      handoff_state_from_record(record)
    Condition
      Error in `check_handoff_ellmer_record_class()`:
      ! Unsupported handoff ellmer record class: "HandoffReplayProbe".

# handoff_state_from_record() / rejects record-shaped tool arguments before constructor resolution

    Code
      handoff_state_from_record(record)
    Condition
      Error in `check_handoff_record_data()`:
      ! Handoff ellmer record data must not contain nested recorded objects.

# handoff_state_from_record() / rejects non-inert incoming tool values

    Code
      handoff_state_from_record(record)
    Condition
      Error in `abort_non_inert_handoff_record()`:
      ! Handoff records may contain only inert JSON values and plain lists.

---

    Code
      handoff_state_from_record(failed_record)
    Condition
      Error in `abort_non_inert_handoff_record()`:
      ! Handoff records may contain only inert JSON values and plain lists.

# handoff_state_from_record() / rejects non-plain state and turn containers

    Code
      handoff_state_from_record(record)
    Condition
      Error in `check_plain_list()`:
      ! Handoff state record must be a plain list.

# handoff_state_from_record() / rejects unexpected ellmer record fields and props

    Code
      handoff_state_from_record(extra_turn_field)
    Condition
      Error in `check_exact_fields()`:
      ! Ellmer turn record has unexpected field: "extra".

# handoff_state_from_record() / rejects attributed ellmer class metadata

    Code
      handoff_state_from_record(record)
    Condition
      Error in `check_handoff_ellmer_record_class()`:
      ! Handoff ellmer record class must be a single un-attributed string.

# handoff_state_from_record() / rejects malformed ellmer prop values

    Code
      handoff_state_from_record(text)
    Condition
      Error in `value[[3L]]()`:
      ! Ellmer turn record could not be replayed: <ellmer::ContentText> object properties are invalid: - @text must be <character>, not <double>

# handoff_state_from_record() / rejects missing tool result requests

    Code
      handoff_state_from_record(missing_request)
    Condition
      Error in `value[[3L]]()`:
      ! Ellmer turn record could not be replayed: no applicable method for `@` applied to an object of class "NULL"

---

    Code
      handoff_state_from_record(null_request)
    Condition
      Error in `check_plain_list()`:
      ! Ellmer ContentToolResult prop `request` must be a plain list.

# handoff_state_from_record() / validates state and type metadata before turn replay

    Code
      handoff_state_from_record(malformed_source)
    Condition
      Error in `check_scalar_field()`:
      ! `source` must be a single non-missing string

# handoff_state_from_record() / rejects unsupported record versions

    Code
      handoff_state_from_record(record)
    Condition
      Error in `handoff_state_from_record()`:
      ! Handoff state record version must be exactly 1.

# handoff_state_from_record() / rejects malformed records

    Code
      handoff_state_from_record("not a record")
    Condition
      Error in `check_plain_list()`:
      ! Handoff state record must be a plain list.

---

    Code
      handoff_state_from_record(record)
    Condition
      Error in `check_exact_fields()`:
      ! Handoff state record is missing required field: "source".

# handoff_state_from_record() / rejects unknown type metadata

    Code
      handoff_state_from_record(record)
    Condition
      Error in `check_exact_fields()`:
      ! Handoff type record has unexpected field: "renderer".

# handoff_state_from_record() / rejects ellmer record versions before replay

    Code
      handoff_state_from_record(record)
    Condition
      Error in `check_handoff_ellmer_record_version()`:
      ! Ellmer turn record version must be exactly 1.

# load_handoff_registry() / shows a representative root diagnostic

    Code
      load_handoff_registry(local_registry_fixture(list("version")))
    Condition
      Error in `check_mapping()`:
      ! Handoff registry must be a mapping.

# resolve_handoff_target() / rejects unknown formats and unsupported languages without fallback

    Code
      resolve_handoff_target("missing", "python")
    Condition
      Error in `resolve_handoff_target()`:
      ! Unknown handoff format: missing

---

    Code
      resolve_handoff_target("marimo-notebook", "r")
    Condition
      Error in `resolve_handoff_target()`:
      ! Handoff format "Marimo" does not support R.

# parse_handoff_generate_request() / rejects data frames with a representative diagnostic

    Code
      parse_handoff_generate_request(data.frame(type = "shiny-app"),
      "quarto-dashboard")
    Condition
      Error in `check_payload_fields()`:
      ! Handoff generate payload must not be a data frame.

# parse_handoff_recommendation() / rejects unsupported IDs with a representative diagnostic

    Code
      parse_handoff_recommendation(list(selected_ids = "missing", format_id = "quarto-dashboard"),
      allowed_item_ids = "viz-1", allowed_format_ids = "quarto-dashboard")
    Condition
      Error in `check_runtime_values()`:
      ! selected_ids contains unsupported item ID: "missing".

# parse_handoff_result() / rejects unsupported tables with a representative diagnostic

    Code
      parse_handoff_result(list(source = "x", language = "python", referenced_tables = "payments"),
      allowed_table_names = "orders", allowed_languages = "python")
    Condition
      Error in `check_runtime_values()`:
      ! referenced_tables contains unsupported table name: "payments".

# parse_handoff_freeform_metadata() / rejects an unsafe extension with a representative diagnostic

    Code
      parse_handoff_freeform_metadata(list(file_extension = "../handoff.py",
        editor_language = "python"))
    Condition
      Error in `parse_handoff_freeform_metadata()`:
      ! file_extension must be a safe file extension.

# parse_handoff_freeform_metadata() / rejects missing, unexpected, and malformed fields

    Code
      parse_handoff_freeform_metadata(list(file_extension = ".py", editor_language = ""))
    Condition
      Error in `check_scalar_field()`:
      ! `editor_language` must not be empty

