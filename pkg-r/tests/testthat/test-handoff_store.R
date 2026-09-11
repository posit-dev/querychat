new_store_handoff_state <- function(handoff_id, source = handoff_id) {
  HandoffState(
    handoff_id = handoff_id,
    handoff_type = resolve_handoff_type("quarto-dashboard", "r"),
    system_prompt = "System prompt",
    source = source
  )
}

describe("HandoffStore$remember()", {
  it("evicts the least-recently-used state past the item limit", {
    store <- HandoffStore$new(max_items = 2L)
    state_a <- new_store_handoff_state("a")
    state_b <- new_store_handoff_state("b")
    state_c <- new_store_handoff_state("c")

    expect_length(store$remember(state_a), 0L)
    expect_length(store$remember(state_b), 0L)
    removed <- store$remember(state_c)

    expect_identical(removed, list(state_a))
    expect_identical(store$values(), list(state_b, state_c))
  })

  it("returns a replaced state and keeps the replacement most recent", {
    store <- HandoffStore$new(max_items = 2L)
    old <- new_store_handoff_state("a", "old")
    replacement <- new_store_handoff_state("a", "new")
    state_b <- new_store_handoff_state("b")
    store$remember(old)
    store$remember(state_b)

    removed <- store$remember(replacement)

    expect_identical(removed, list(old))
    expect_identical(store$values(), list(state_b, replacement))
  })
})

describe("HandoffStore$get()", {
  it("refreshes recency before the next eviction", {
    store <- HandoffStore$new(max_items = 2L)
    state_a <- new_store_handoff_state("a")
    state_b <- new_store_handoff_state("b")
    state_c <- new_store_handoff_state("c")
    store$remember(state_a)
    store$remember(state_b)

    expect_identical(store$get("a"), state_a)
    expect_identical(store$remember(state_c), list(state_b))
    expect_identical(store$values(), list(state_a, state_c))
  })

  it("returns NULL for missing and empty IDs", {
    store <- HandoffStore$new()

    expect_null(store$get("missing"))
    expect_null(store$get(NULL))
    expect_null(store$get(""))
  })
})

describe("HandoffStore$replace()", {
  it("returns old states and preserves supplied LRU order", {
    store <- HandoffStore$new(max_items = 3L)
    old_a <- new_store_handoff_state("old-a")
    old_b <- new_store_handoff_state("old-b")
    state_c <- new_store_handoff_state("c")
    state_a <- new_store_handoff_state("a")
    state_b <- new_store_handoff_state("b")
    store$remember(old_a)
    store$remember(old_b)

    removed <- store$replace(list(state_c, state_a, state_b))

    expect_identical(removed, list(old_a, old_b))
    expect_identical(store$values(), list(state_c, state_a, state_b))
    expect_identical(
      store$remember(new_store_handoff_state("d")),
      list(state_c)
    )
  })

  it("leaves the old states and order intact when validation fails", {
    store <- HandoffStore$new(max_items = 3L)
    old_states <- lapply(c("old-a", "old-b"), new_store_handoff_state)
    invisible(lapply(old_states, store$remember))

    expect_snapshot(
      error = TRUE,
      store$replace(list(new_store_handoff_state("new"), "invalid"))
    )

    expect_identical(store$snapshot(), old_states)
  })
})

describe("HandoffStore read operations", {
  it("does not mutate LRU order through has, values, or snapshot", {
    store <- HandoffStore$new(max_items = 3L)
    states <- lapply(c("a", "b", "c"), new_store_handoff_state)
    invisible(lapply(states, store$remember))

    expect_identical(store$has("a"), TRUE)
    expect_identical(store$values(), states)
    expect_identical(store$snapshot(), states)
    expect_identical(store$values(), states)
  })

  it("discards a state without changing the remaining order", {
    store <- HandoffStore$new(max_items = 3L)
    states <- lapply(c("a", "b", "c"), new_store_handoff_state)
    invisible(lapply(states, store$remember))

    expect_identical(store$discard("b"), states[[2]])
    expect_identical(store$values(), states[c(1, 3)])
    expect_null(store$discard("missing"))
  })
})

describe("HandoffStore$new()", {
  it("rejects invalid item limits", {
    expect_snapshot(error = TRUE, HandoffStore$new(max_items = 0L))
  })
})

describe("HandoffBundleStore$stage()", {
  it("copies files and assigns unique bundle IDs without eviction", {
    store <- HandoffBundleStore$new(max_bytes = 4)
    files <- list("a.csv" = charToRaw("aaa"))

    first <- store$stage(files)
    second <- store$stage(list("b.csv" = charToRaw("bbb")))
    files[["a.csv"]][[1]] <- charToRaw("z")

    expect_false(identical(first@bundle_id, second@bundle_id))
    expect_identical(first@bundled_files[["a.csv"]], charToRaw("aaa"))
    expect_identical(store$get(first@bundle_id), first)
    expect_identical(store$get(second@bundle_id), second)
  })

  it("rejects one bundle larger than the byte budget", {
    store <- HandoffBundleStore$new(max_bytes = 2)

    expect_snapshot(
      error = TRUE,
      store$stage(list("large.csv" = charToRaw("abc")))
    )
  })

  it("rejects empty bundles without changing store state", {
    store <- HandoffBundleStore$new(max_bytes = 4)
    existing <- store$stage(list("a.csv" = charToRaw("aa")))
    private <- store$.__enclos_env__$private
    order <- private$order
    total_bytes <- private$total_bytes

    expect_snapshot(error = TRUE, store$stage(list()))
    expect_snapshot(error = TRUE, store$put(list()))
    expect_snapshot(error = TRUE, store$stage(list()))

    expect_identical(private$order, order)
    expect_identical(private$total_bytes, total_bytes)
    expect_identical(store$get(existing@bundle_id), existing)
  })
})

describe("HandoffBundleStore$put()", {
  it("evicts least-recently-used bundles to meet the byte budget", {
    store <- HandoffBundleStore$new(max_bytes = 4)
    first <- store$put(list("a.csv" = charToRaw("aa")))
    second <- store$put(list("b.csv" = charToRaw("bb")))
    third <- store$put(list("c.csv" = charToRaw("cc")))

    expect_null(store$get(first@bundle_id))
    expect_identical(store$get(second@bundle_id), second)
    expect_identical(store$get(third@bundle_id), third)
  })
})

describe("HandoffBundleStore$get()", {
  it("refreshes recency before eviction", {
    store <- HandoffBundleStore$new(max_bytes = 4)
    first <- store$put(list("a.csv" = charToRaw("aa")))
    second <- store$put(list("b.csv" = charToRaw("bb")))

    expect_identical(store$get(first@bundle_id), first)
    third <- store$put(list("c.csv" = charToRaw("cc")))

    expect_identical(store$get(first@bundle_id), first)
    expect_null(store$get(second@bundle_id))
    expect_identical(store$get(third@bundle_id), third)
  })
})

describe("HandoffBundleStore$discard()", {
  it("updates byte accounting", {
    store <- HandoffBundleStore$new(max_bytes = 4)
    first <- store$stage(list("a.csv" = charToRaw("aaa")))
    second <- store$stage(list("b.csv" = charToRaw("bbb")))

    expect_identical(store$discard(first@bundle_id), first)
    expect_length(store$evict(), 0L)
    expect_identical(store$get(second@bundle_id), second)
  })
})

describe("HandoffBundleStore$evict()", {
  it("returns evicted bundles in least-to-most-recent order", {
    store <- HandoffBundleStore$new(max_bytes = 4)
    first <- store$stage(list("a.csv" = charToRaw("aa")))
    second <- store$stage(list("b.csv" = charToRaw("bb")))
    third <- store$stage(list("c.csv" = charToRaw("cc")))
    fourth <- store$stage(list("d.csv" = charToRaw("dd")))

    expect_identical(store$get(second@bundle_id), second)
    expect_identical(store$evict(), list(first, third))
    expect_identical(store$get(second@bundle_id), second)
    expect_identical(store$get(fourth@bundle_id), fourth)
  })

  it("stops without error when the byte total is stale but no bundles remain", {
    store <- HandoffBundleStore$new(max_bytes = 1)
    private <- store$.__enclos_env__$private
    private$total_bytes <- 100

    expect_identical(store$evict(), list())
  })
})

describe("HandoffBundleStore$new()", {
  it("rejects invalid byte limits", {
    expect_snapshot(error = TRUE, HandoffBundleStore$new(max_bytes = 0))
  })
})
