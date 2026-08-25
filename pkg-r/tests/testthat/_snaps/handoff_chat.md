# HandoffChat$stream() / propagates native structured-stream rejection without fallback

    Code
      sync_promise(HandoffChat$new(chat)$stream("generate", type = type, view = view))
    Condition
      Error:
      ! Streaming structured output requires native provider support for the supplied model.

# HandoffChat$stream() / rejects chats without structured streaming before changing the view

    Code
      HandoffChat$new(chat)$stream("generate", type = type, view = view)
    Condition
      Error in `check_structured_streaming()`:
      ! Structured handoff streaming requires an ellmer `Chat$stream_async()` method with a `type` argument.

# HandoffChat$stream() / clears streaming after an error

    Code
      sync_promise(HandoffChat$new(chat)$stream("generate", type = type, view = view))
    Condition
      Error:
      ! stream failed

# HandoffChat$stream() / clears streaming after synchronous stream setup rejection

    Code
      sync_promise(HandoffChat$new(chat)$stream("generate", type = type, view = view))
    Condition
      Error:
      ! stream setup failed

# HandoffChat$stream() / clears streaming after cancellation

    Code
      sync_promise(HandoffChat$new(chat)$stream("generate", type = type, view = view))
    Condition
      Error:
      ! generation cancelled

# HandoffChat$stream() / rejects normally exhausted partial-turn cancellation

    Code
      sync_promise(HandoffChat$new(chat)$stream("generate", type = type, view = view))
    Condition
      Error in `completed_json_content()`:
      ! Structured stream did not produce completed JSON content.

# completed_json_content() / does not use completed content from an earlier assistant turn

    Code
      completed_json_content(turns)
    Condition
      Error in `completed_json_content()`:
      ! Structured stream did not produce completed JSON content.

# sync_promise() / fails with a diagnostic when a promise does not settle

    Code
      sync_promise(pending, timeout = 0.01)
    Condition
      Error in `sync_promise()`:
      ! Promise did not settle within 0.01 seconds.

