# handoff_message_type() / rejects noncanonical and malformed actions

    Code
      handoff_message_type("unknown")
    Condition
      Error in `handoff_message_type()`:
      ! `action` must be one of "recommend", "recommend-error", "source-update", "streaming", and "panel-toggle".

---

    Code
      handoff_message_type(c("streaming", "panel-toggle"))
    Condition
      Error in `check_handoff_protocol_string()`:
      ! `action` must be a nonempty string.

---

    Code
      handoff_message_type(NA_character_)
    Condition
      Error in `check_handoff_protocol_string()`:
      ! `action` must be a nonempty string.

# handoff_source_update_message() / rejects malformed scalars and extra fields

    Code
      handoff_source_update_message(c("root-a", "root-b"), "editor", "print(1)")
    Condition
      Error in `check_handoff_protocol_string()`:
      ! `root_id` must be a nonempty string.

---

    Code
      handoff_source_update_message("root", "editor", "print(1)", append = 1)
    Condition
      Error in `check_handoff_protocol_logical()`:
      ! `append` must be a single logical value.

---

    Code
      do.call(handoff_source_update_message, list(root_id = "root", id = "editor",
        value = "print(1)", extra = TRUE))
    Condition
      Error:
      ! unused argument (extra = TRUE)

