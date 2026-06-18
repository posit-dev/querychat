# Artifact feature

Turns the work a user did during a querychat session — the SQL queries and ggsql
visualizations they produced by asking questions — into a **standalone, runnable,
downloadable artifact**: a Quarto dashboard, Shiny app, Marimo or Jupyter notebook,
or a freeform "other" format the LLM describes on demand.

Python-only today (`pkg-py/src/querychat/`). There is no R counterpart yet; the clean
layering below is a reasonable template if/when parity is pursued.

---

## 1. What the user sees

1. They open the **Create Artifact** modal — either by typing `/artifact` or because the
   LLM decided to (see [§4 Entry paths](#4-two-entry-paths)).
2. The modal shows a **gallery** of the session's queries/visualizations, an **output
   format** picker, a **language** picker (R/Python), and a **directions** box. While it
   opens, an LLM **recommendation** pre-selects sensible items, format, and directions.
3. They hit **Generate**. A side **panel** opens and the artifact source **streams** into
   a read-only code editor. A **pill** is appended to the chat linking back to it.
4. From the panel they can **revise** with AI (push a new version), step through
   **versions**, and **download** a zip (source + `README.md` + any bundled data).
5. State survives **bookmarking** (server/url), so a restored session re-shows artifacts.

---

## 2. Design principles (read this first)

These constraints explain why the code is split the way it is. Honor them when changing it.

- **The orchestrator holds no reactive state.** `ArtifactOrchestrator`
  (`_artifact_orchestrator.py`) is plain async logic: it reads no `reactive.Value`, defines
  no effects, and never touches `input.*`. That's what lets it be tested with plain fakes
  (`tests/test_artifact_orchestrator.py`). **All** reactivity lives in `artifact_server`
  (`_artifact_server.py`).
- **One owner per concern.**
  - `ArtifactView` is the *only* place server→client output happens (custom messages,
    modal, pill).
  - `ArtifactChat` is the *only* place chatlas is touched.
  - `ArtifactStore` is the *only* place artifacts are held/serialized.
  - `active_artifact_id` (a reactive value in `artifact_server`) is the *single source of
    truth* for panel visibility — the panel opens/closes purely as a function of it via
    the `sync_panel_visibility` effect. The orchestrator never opens the panel itself.
- **Generation is isolated from the main conversation.** `ArtifactChat` deep-copies the
  live chat before every call, so generate/revise/recommend exchanges never pollute the
  user's visible chat history.
- **Tool names are a shared contract.** The names the LLM's tools register under and the
  names the gallery matches when reading chat turns both come from `_tool_names.py`. Never
  re-hardcode a `"querychat_*"` literal at a call site.

---

## 3. Module map

| Module | Responsibility | Reactive? |
|---|---|---|
| `_artifact_server.py` | `artifact_server()` — all reactive wiring: inputs, effects, `active_artifact_id`, extended task for recommend, bookmark hooks. Drives the orchestrator. | **Yes** |
| `_artifact_orchestrator.py` | `ArtifactOrchestrator` — non-reactive business logic for every flow (open, recommend, generate, revise, version nav, download). Plus `GenerateRequest`, `parse_generate_payload`, zip building. | No |
| `_artifact_chat.py` | `ArtifactChat` — chatlas transport: fork an isolated chat, one-shot structured `ask()`, and `stream()` a structured `ArtifactResult` into a sink (driving partial JSON). | No |
| `_artifact_view.py` | `ArtifactView` — server→client output: `querychat-artifact-*` custom messages, modal show/remove, chat pill. Owns the wire contract with the JS. | No |
| `_artifact_store.py` | `ArtifactStore` — per-session LRU container of `ArtifactState`; serializes for bookmarks. | No |
| `_artifact_state.py` | `ArtifactState`, `ArtifactVersion` (pydantic) — the artifact and its version history; bookmark (de)serialization. | No |
| `_artifact_types.py` | `ArtifactType`, `LanguageVariant`, `ARTIFACT_TYPES`, `LANGUAGES`, `resolve_for_language`. | No |
| `_artifact_prompt.py` | Structured-output models (`Recommendation`, `ArtifactResult`, `FreeformMetadata`), dynamic `recommendation_model`, and the Mustache prompt builders. | No |
| `_artifact_gallery.py` | `GalleryItem` (`VizGalleryItem` \| `QueryGalleryItem`) + `extract_gallery_items` — mines chat turns for queries/viz (matches tool names from `_tool_names.py`). | No |
| `_artifact_data.py` | `ArtifactDataContext` + `get_artifact_data_context` — decides how the artifact reaches the data (bundle CSV, point at DB, or TODO placeholder). | No |
| `_artifact_readme.py` | `build_readme` — the `README.md` packaged in the download. | No |
| `_artifact_panel.py` | `artifact_panel_ui()` (the side panel + CSS/JS includes) and `render_pill_html`. | No |
| `_artifact_modal.py` | `build_modal_ui()` and its sub-builders (gallery, type/language pills, directions). | No |
| `_tool_names.py` | Canonical `TOOL_*` name constants shared by tool registration and gallery extraction. | No |
| `prompts/artifact-system.md`, `artifact-recommend.md`, `tool-request-artifact.md` | Prompt templates. | — |
| `js/src/artifact-core.ts` (+ `artifact.ts` entry) | Browser runtime: modal interactions, panel, streaming editor, version nav. Built to `static/js/artifact.js`. | — |

```
                    ┌──────────────────────────────┐
                    │  Browser — artifact-core.ts   │
                    └──────────────────────────────┘
      inputs / setInputValue │          ▲  querychat-artifact-* messages
                             ▼          │  (emitted by ArtifactView)
                    ┌──────────────────────────────┐
                    │  artifact_server()            │  ← all reactivity
                    │  effects · active_artifact_id │
                    └───────────────┬──────────────┘
                                    │ drives
                                    ▼
                    ┌──────────────────────────────┐
                    │  ArtifactOrchestrator         │  ← no reactive state
                    └──┬───────────┬──────────┬─────┴──┐
                       ▼           ▼          ▼        ▼
             ┌────────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐
             │ArtifactChat│ │ArtifactVw│ │Artifact│ │ pure helpers │
             │chatlas fork│ │srv→client│ │ Store  │ │ data·prompt· │
             │+ streaming │ │modal·pill│ │ (LRU)  │ │ gallery·rdme │
             └────────────┘ └────┬─────┘ └────────┘ └──────────────┘
                                 └──► emits querychat-artifact-* to Browser
```

---

## 4. Two entry paths

Both ways of starting an artifact **converge on the `/artifact` slash command**, so there
is exactly one modal-opening path.

1. **User types `/artifact`** → `chat_ui.slash_command("artifact")` handler
   `open_artifact_modal` runs → `orch.open_modal()` + kicks off the recommend task.
2. **LLM calls the `querychat_request_artifact` tool** (registered always-on in
   `_querychat_base.py`; impl in `tools.py`). The tool fires **mid-stream**, where no
   reactive context exists, so it can't open the modal directly. Instead:
   - `on_request_artifact` (in `_shiny_module.py`) sets a boolean `artifact_requested`.
   - `_open_artifact_when_ready`, an effect gated on
     `chat_ui.latest_message_stream.status`, waits for the turn to settle, then — on
     success — calls `chat_ui.update_user_input("/artifact", submit=True)`, re-entering
     path 1. On error/cancel it consumes the flag without opening (`artifact_action_for_status`).

> **Why the relay?** A tool result can't open a modal while the chat input is disabled
> mid-stream. The flag + status-event effect defers the open until the turn finishes and
> dedupes (multiple tool calls in one turn → one modal). See `_shiny_module.py`.

---

## 5. Core flows

### Open + recommend
`open_modal()` calls `extract_gallery_items(chat history)` → stashes them on the
orchestrator → `view.show_modal(items)`. In parallel, `recommend_task` (a
`reactive.extended_task`) forks the chat and asks for a structured `Recommendation`
(items, format, directions) constrained to the real item/format IDs via a dynamically
built `recommendation_model`. On success, `view.show_recommendation` sends the picks to
the JS, which pre-selects gallery cards, activates the format pill, and fills the
directions box. The prior recommend is **cancelled** before re-invoking (extended tasks
queue rather than replace).

### Generate
1. JS gathers modal state into one event input `artifact_generate`
   `{selected_ids, type, language, freeform}`.
2. `on_generate` → `parse_generate_payload` → mints `artifact_id`, sets
   `active_artifact_id` (panel opens via `sync_panel_visibility`), resets it on failure.
3. `orch.generate(req, directions, artifact_id)`:
   - `prepare_generation` → `resolve_artifact_type` (for "other", asks the LLM for
     `FreeformMetadata`), builds the system + user prompts and the data context.
   - `view.remove_modal()`, `view.clear_editor(language)`.
   - `chat.stream(...)` forks the chat and streams a structured `ArtifactResult`,
     pushing partial `source` into the editor as it arrives.
   - Build `ArtifactState`, `store.remember`, `view.show_version`, `view.append_pill`.
   - On any exception: `store.discard(artifact_id)` and re-raise (surfaced as a
     `NotifyException`).

### Revise
`input.artifact_revise_text` → `orch.revise(active_artifact_id, instructions)` →
`chat.stream` seeded with the current version's `turns` and the artifact's
`system_prompt` → `state.push_version(...)` → `view.show_version`. Because a revision
streams into the editor without appending a chat message, the server **re-triggers
`session.bookmark()`** so the new version is captured.

### Version navigation
`artifact_version_prev/next` → `orch.step_version(id, ±1)` → `state.step` → `show_version`.

### Download
`render.download` → `orch.build_download(id)` → `build_readme(...)` +
`build_artifact_zip(...)` → `artifact.<ext>` + `README.md` + bundled data files.

```
JS ──► input.artifact_generate {selected_ids, type, language, freeform}
artifact_server : mint id ─► active_artifact_id.set(id)        ⇒ panel opens (sync effect)
artifact_server ──► ArtifactOrchestrator.generate(req, directions, id)
   ├─ prepare_generation  (resolve type · build prompts · data context)
   ├─ ArtifactView        : remove_modal, clear_editor
   ├─ ArtifactChat.stream (user + system prompt)
   │     └─ loop: update_source ─► ArtifactView ─► JS  (querychat-artifact-source-update)
   ├─ ArtifactStore.remember(state)
   └─ ArtifactView        : show_version + append_pill ─► JS  (version-update, chat pill)
```

---

## 6. The Python → JS wire contract

`ArtifactView._send(action, payload)` sends `f"querychat-artifact-{action}"` custom
messages; `artifact-core.ts` registers a handler per name. **This contract is duplicated
by hand on both sides — there is no shared schema — so a rename or payload change in one
language silently no-ops in the other. Change both together.** (This duplication is a
known maintenance hazard; centralizing the names is a tracked future cleanup.)

| Message (`querychat-artifact-…`) | Payload | Effect |
|---|---|---|
| `panel-toggle` | `{open}` | Show/hide the side panel + backdrop. |
| `source-update` | `{id, value, language?}` | Set the code editor value (bypasses Shiny's flush queue for smooth streaming). |
| `streaming` | `{active}` | Toggle the header spinner. |
| `version-update` | `{label, total, prev_disabled, next_disabled}` | Update the version stepper. |
| `recommend` | `{selected_ids, format_id, directions, directions_id}` | Pre-select gallery, activate format pill, fill directions. |
| `recommend-error` | `{error}` | Show inline failure; modal stays usable for manual selection. |

**JS → Python** (via `Shiny.setInputValue` / standard bindings):

| Input | Origin | Notes |
|---|---|---|
| `artifact_generate` | Generate button | One event payload `{selected_ids, type, language, freeform}`. Namespaced id; JS uses `[id$='artifact_generate']`. |
| `artifact_open` | Chat pill click | Carries the artifact id; pill reads its target input id from `data-input-id`. |
| `artifact_directions` | Directions textarea | Read in `on_generate`. |
| `artifact_close`, `artifact_version_prev`, `artifact_version_next`, `artifact_revise_text`, `artifact_download` | Panel controls | Standard Shiny module inputs / download. |

---

## 7. Data access & bundling (`_artifact_data.py`)

`get_artifact_data_context(data_source)` decides how the generated artifact reaches its
data, and returns `data_instructions` (injected into the system prompt) plus optional
`bundled_files`:

- **DataFrameSource ≤ 5 MB as CSV** → bundle `"<table>.csv"`; instruct the artifact to
  load it (and register it in DuckDB for SQL). Runnable as-is.
- **DataFrameSource > 5 MB** → no bundle; instruct a clearly-marked "DATA SETUP" TODO.
- **DB-backed source** → no bundle; instruct a connection-string TODO using env vars.
- **No data source** → TODO placeholder.

---

## 8. State model & bookmarking

- `ArtifactState` (pydantic) holds `artifact_id`, `artifact_type`, `system_prompt`, a list
  of `ArtifactVersion`s, and `current_index`. `versions[]` each carry `source`, chatlas
  `turns`, `kind` (`generated`/`revised`), `summary`, `install_instructions`.
- `bundled_files` and `data_instructions` are **`exclude=True`** — they are **not**
  bookmarked. On restore, `restore_from_bookmark` **regenerates** them from the current
  data source (mirroring how viz widgets re-execute ggsql on restore). This keeps bookmarks
  small and tolerant of changed data.
- `ArtifactStore` is an LRU capped at `MAX_STORED_ARTIFACTS` (25). Reopening an evicted
  artifact's pill simply no-ops.
- Bookmark hooks live in `artifact_server` under `enable_bookmarking`, keyed
  `querychat_artifacts` (separate from the core querychat bookmark keys in `_shiny_module.py`).

---

## 9. Artifact types & languages (`_artifact_types.py`)

`ARTIFACT_TYPES` is an ordered dict (the first key is the default). Each `ArtifactType`
carries file extension, editor language, icon, generation notes, run instructions, and
`supported_languages`. `language_variants` lets one type swap fields per language (e.g. the
Shiny type becomes `app.R` in R); `resolve_for_language` applies the variant. The **"other"**
type is synthesized at request time from LLM-supplied `FreeformMetadata`.

---

## 10. Known hazards & gotchas

- **Wire contract is hand-duplicated Py↔JS** (see §6). Highest-friction maintenance risk.
- **Generated assets are committed.** `static/js/artifact.js` and `static/css/artifact.css`
  are build outputs of `js/src/artifact.ts` / `artifact.css` (see `js/build.mjs`). **Edit
  the TS/CSS source and rebuild — never the generated files.**
- **The feature is always-on.** The `querychat_request_artifact` tool and `/artifact`
  command are registered regardless of the `tools=` config; the panel UI is always injected.
  There is currently no opt-out (a deliberate-by-omission product decision worth revisiting).
- **Unreleased dependencies.** The feature relies on `shinychat` slash commands +
  `input_submit_textarea`/`input_code_editor` and recent `shiny`; `pyproject.toml` currently
  pins git refs for these. They must move to released versions before any release.
- **Partial-JSON streaming**: `ArtifactChat._drive` parses the in-flight stream with
  `from_json(..., allow_partial=...)` and pushes only the `source` field to the editor;
  the spinner clears in a `finally` so a failed stream still resets the UI.
- **Recommend cancellation**: always `recommend_task.cancel()` before re-invoking, or a
  stale recommendation can populate a freshly-opened modal with IDs that no longer exist.

---

## 11. Integration points (where the rest of querychat plugs in)

- `_querychat_base.py` → `_create_session_client` registers `tool_request_artifact` and
  threads a `request_artifact` callback.
- `_shiny_module.py` → `mod_ui` injects `artifact_panel_ui()`; `mod_server` constructs the
  chat UI, calls `artifact_server(...)`, and hosts the tool-request relay
  (`on_request_artifact`, `_open_artifact_when_ready`, `artifact_action_for_status`).

## 12. Tests

- `tests/test_artifact_*.py` — unit tests per module; the orchestrator suite uses plain
  fakes (`FakeSession`, `FakeChat`, `FakeChatUI`, `FakeDataSource`) thanks to the
  no-reactive-state rule.
- `tests/playwright/test_13_artifact*.py`, `test_14_artifact_bookmark.py` — browser
  integration (need a running app + a live LLM; not part of the fast unit run).
