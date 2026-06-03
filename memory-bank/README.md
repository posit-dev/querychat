# Memory Bank

Durable, committed context about this project for **both maintainers and AI agents**.
Each entry captures the *why* and the cross-cutting mental model that isn't obvious
from any single file — the things you'd otherwise have to reconstruct by reading the
whole codebase.

This is distinct from a contributor's personal agent memory (e.g. `~/.claude`): the
memory bank is shared, version-controlled, and reviewed like code.

## How to use it

- **Starting work on a feature?** Read its entry here first for the layer map, data
  flow, and known gotchas, then dive into the code.
- **Agents:** treat an entry as the authoritative mental model, but verify specifics
  (names, signatures, line numbers) against the current code before acting — entries
  describe intent and structure, which drift slower than exact details.

## How to maintain it

- **One concern per file**, linked from the index below.
- Keep entries **lean**: explain structure, contracts, and rationale — don't duplicate
  what docstrings or `CLAUDE.md` already say well. Link to the source of truth instead.
- **Update the entry in the same PR** that changes the architecture it describes. A
  stale memory bank is worse than none.
- Prefer stable references (module, class, and function names) over line numbers.

## Index

- [Artifact feature](./artifact-feature.md) — turning a chat session's queries and
  visualizations into a standalone, downloadable artifact (Quarto / Shiny / Marimo /
  Jupyter / freeform). Python-only today.
