# Session handoff: handoff-feature restore work

Context for continuing work on `feat/artifact-feature` in a fresh session.
Written 2026-08-27. (Note: "handoff" below refers to the querychat feature
formerly named "artifact" — renamed in d0217ab1 — not this document.)

## Goals for the next session

1. **Verify handoff downloads in live apps** (unit-tested but never
   exercised live) in BOTH packages against shinychat main. Demo apps are in
   `restore_demo/` (see "Demo apps" below). R first needs shinychat from main
   (`pak::pak("posit-dev/shinychat/pkg-r@main")`); the Python venv already has
   main. In each app: ask a question, create a visualization, run `/handoff`,
   reload the page, reopen the handoff from the pill, and confirm the download
   button is enabled and serves a regenerated zip.
2. **Make the restore logic work against shinychat `main`** instead of the
   pinned experimental branch. The Python A/B experiment (below) suggests main
   already restores faithfully; the R side is unverified. See "Path to
   unpinning" section.
3. **Learn/document how restore actually works** in shinychat (both
   packages), enough to explain the save/restore flow confidently.

## Branch state

- Repo: `/Users/cpsievert/github/querychat`, branch `feat/artifact-feature`
  (4 commits ahead of origin).
- **Uncommitted changes** (the regeneration fallback, this doc's main work):
  - `pkg-py/src/querychat/_handoff_orchestrator.py`
  - `pkg-py/tests/test_handoff_orchestrator.py`
  - `pkg-r/R/handoff_orchestrator.R`
  - `pkg-r/tests/testthat/test-handoff_orchestrator.R`
- shinychat repo: `/Users/cpsievert/github/shinychat`. The pinned dev branch
  lives in worktree `.worktrees/querychat-pr311-history-save`.
- DESCRIPTION pin (pkg-r line 66):
  `posit-dev/shinychat/pkg-r@dev/querychat-pr311-history-save`

## How the handoff feature works (verified by reading code)

### Generation

1. `/handoff` slash command → modal → gallery items extracted from chat
   turns; LLM recommends items/format (`HandoffOrchestrator$open_modal()` /
   `recommend()`).
2. LLM generates complete runnable source + metadata (summary, install/run
   instructions, `referenced_tables`); schema in `_handoff_prompt.py` /
   `handoff_prompt.R`. Source streams to the side panel as deltas.
3. Validation failures trigger repair turns in the same forked conversation.
4. A "pill" (custom HTML) is appended to the chat via
   `Chat.append_message()` / `chat_append()` — a UI-level message, **not**
   part of the ellmer/chatlas turns.

### State and persistence

- `HandoffState`: source, turns, instructions, `referenced_tables`,
  `bundled_tables`, `bundle_id`, `data_instructions`. Stored in
  `HandoffStore` (LRU, 25 items). Revisions are latest-only (source replaced,
  turns accumulate).
- **Bundles are raw, UNFILTERED table exports**: `DataFrameSource.get_data()`
  returns the unfiltered frame (`_datasource.py:495`). Only DataFrameSource
  (in-memory) tables are bundled; database tables never are. 5 MB per handoff,
  else "externalized" (user supplies data).
- `HandoffBundleStore`: in-memory, per-session LRU, 25 MB budget. **Never
  persisted** — this is the root cause of the restore gap.
- Persistence goes through shinychat's history hooks: `history.on_save` /
  `on_restore` (plus Shiny bookmark hooks). Python saves
  `list[HandoffState.model_dump()]` under the `querychat_handoffs` key; R
  serializes a JSON envelope (`version = 1`, strict validation in
  `apply_handoff_snapshot`, handoff_server.R).

### Restore layering (key mental model)

| Layer | Where it lives | Survives restore? |
|---|---|---|
| Handoff payload (source, instructions, turns) | `HandoffState` in history values | Yes — querychat's own hooks |
| Pills / framed tool cards / greeting | shinychat's UI message snapshot | Yes — even on shinychat main (Python verified live) |
| Data bundles (CSVs) | `HandoffBundleStore` (in-memory) | No — session-scoped; now regenerated on demand |

## What we learned about shinychat restore (evidence audit)

Verified directly this session:

- **ellmer round-trips `ContentToolResult@extra`** through
  `contents_record()`/`contents_replay()` — tool-result display metadata
  (framing, frozen HTML, footers) survives in saved turns.
- **shinychat main (Python, 0.6.2.dev40+g909ed8c) already does server-side
  UI message state**: `HistoryController.on_response()` saves
  `chat._messages_for_bookmark()` (the client-rendered `${id}_messages`
  snapshot) alongside turns and replays it. Confirmed live: handoff pills
  restore on main.
- The dev branch adds **correctness hardening**, not the core capability:
  `_chat_transcript.py` (new, 260 lines), transcript rebasing, greeting
  snapshot fidelity, bookmark-mode restore, explicit save transactions.
  ~9k-line diff vs main (88 files).
- **No positional message-insertion API** exists in shinychat (checked R,
  Python, and JS on main and dev).
- A page reload always creates a new Shiny **session**; per-session state
  (bundle store) is always lost, same process or not.

Caveat: the A/B experiment was Python-only. The R restore path may differ —
`querychat_module.R:152` calls `chat_restore(restore_ui = FALSE)` in
non-bookmark modes (hooks only), and R main's history machinery
(`chat_history.R`, `chat_enable_history()`) exists but is less characterized.

## Regeneration fallback implemented (uncommitted)

Since bundles are pure functions of the session's static dataframes, missing
bundles are regenerated lazily on download — no schema change needed
(`bundled_tables` was already persisted).

Both packages, same design:

- `build_download()`: cache path untouched (existing bundle served as-is);
  missing bundle → regenerate via `export_csv()` / `export_handoff_csv()` →
  re-cache via `put()` (serve without caching if over budget).
- `_download_available()` / `download_available()`: TRUE when no bundled
  tables, bundle present, OR bundle regenerable → button enabled after
  restore.
- Non-regenerable (missing/non-dataframe source, export failure) → same
  "snapshot unavailable" error as before (distinct "could not be regenerated"
  message, same error class).
- R-specific: S7 is copy-on-modify, so the state with the new `bundle_id` is
  explicitly re-`remember()`ed (Python mutates the shared pydantic object).

**This inverted a deliberate, tested invariant** ("never calls live data
sources to reconstruct a missing snapshot" / `..._never_exports_live_dataframe`).
The invariant now holds only when a snapshot exists; regeneration is the
fallback when it's genuinely gone. If the original motivation was data
governance (fresh session may load different data), that concern still
applies — flag for the team before merging.

Tests: pkg-py orchestrator 61/61; pkg-r orchestrator 190/190; all handoff
unit files green in both packages. Pre-existing failures (NOT from this
work): pkg-py full `-k handoff` suite has nondeterministic pollution (~70
failures, passes per-file); pkg-r `test-handoff-browser.R` fails identically
with/without the change (modal DOM never renders — likely needs the pinned
shinychat JS; environmental).

## Path to unpinning shinychat (goal 2)

Questions to answer, in order:

1. What does pkg-r actually use from the pin? Known touchpoints:
   `chat_server(history=)` returning `$history` with `on_save`/`on_restore`,
   `chat_enable_history()`, `history_options(restore_mode=)`,
   `chat_greeting(persistent=)`, `chat_restore()`. Check each against R main.
   Note `helper-fixtures.R:570`: "the pinned shinychat branch's history object
   exposes only `on_save` and `on_restore` — no `save()`" — verify against main.
2. Try dropping the pin (install main pkg-r shinychat), run
   `testthat::test_dir(..., filter = "handoff")` and the module tests, and
   exercise `pkg-r/tests/testthat/apps/handoff/app.R` live: pills, framed viz
   cards, greeting, restore across reload in each restore_mode.
3. The dev branch's R-side diff adds `chat_transcript.R` (304 lines),
   bookmark-mode history restore, greeting snapshot fixes — determine which
   of these matter for querychat's usage and whether main's equivalents
   suffice.
4. pkg-py appears to need nothing from the pin (works on main) — confirm by
   checking querychat's Python imports against main's shinychat API.

## Environment cheat sheet

- Python: repo `.venv`; querychat installed editable (pkg-py/src); shinychat
  0.6.2.dev40+g909ed8c (main) in site-packages. Run dev-branch shinychat
  without installing:
  `PYTHONPATH=/Users/cpsievert/github/shinychat/.worktrees/querychat-pr311-history-save/pkg-py/src`
- Demo apps live in `restore_demo/` (self-contained, smoke-tested):
  - `restore_demo/app.py` — Python, titanic, `history=True`
  - `restore_demo/app.R` — R, mtcars, `history = TRUE`
  - Both use `restore_mode = "browser"` (localStorage): reloading the page
    restores the conversation automatically.
- Serve Python against installed (main) shinychat:
  `cd /Users/cpsievert/github/querychat && (nohup .venv/bin/shiny run restore_demo/app.py --port 8080 > /tmp/qc_py_8080.log 2>&1 < /dev/null & disown)`
- Serve Python against the dev-branch shinychat (PYTHONPATH shadow, no install):
  same command with `--port 8081` and
  `PYTHONPATH=/Users/cpsievert/github/shinychat/.worktrees/querychat-pr311-history-save/pkg-py/src`
  prepended.
- Serve R (pkg-r is not installed as a package, so load the branch first):
  ```r
  callr::r_bg(function() {
    devtools::load_all("/Users/cpsievert/github/querychat/pkg-r", quiet = TRUE)
    shiny::runApp(
      "/Users/cpsievert/github/querychat/restore_demo/app.R",
      port = 8082, host = "127.0.0.1", launch.browser = FALSE
    )
  })
  ```
  or `pak::pak("local::/Users/cpsievert/github/querychat/pkg-r")` once, then
  plain `shiny::runApp("restore_demo/app.R", port = 8082)`.
- Still running from the previous session (check before restarting):
  http://127.0.0.1:8080 (Py main), http://127.0.0.1:8081 (Py dev),
  http://127.0.0.1:8082 (R, branch loaded via load_all).
- Python tests: `cd pkg-py && ../.venv/bin/python -m pytest tests/test_handoff_orchestrator.py -q`
  (run per-file; full suite has pre-existing pollution)
- R tests: `devtools::load_all("/Users/cpsievert/github/querychat/pkg-r")`
  then `testthat::test_file(".../test-handoff_orchestrator.R", package = "querychat")`
  or `testthat::test_dir(".../testthat", filter = "handoff", package = "querychat", reporter = "summary")`.
  (`devtools::test()` errored in the console; test_file/test_dir worked.)
- LLM API keys are in the environment (ANTHROPIC/OPENAI/etc).
- `scipy_demo/app.py` and `scipy_demo/demo.py` are open in the editor but
  **deleted from disk** (untracked; buffers only). app.py was an exoplanets
  QueryChat demo (`tools = ("visualize", "filter", "query")`); demo.py
  defined `planets` — content unknown, needs recreation if wanted.
- `querychat.data` has `tips()` and `titanic()` for demos.
