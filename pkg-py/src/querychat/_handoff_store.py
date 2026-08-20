"""
Per-session LRU store of handoffs.

`HandoffStore` is a plain container: it holds the session's `HandoffState`
objects in least-recently-used order and serializes them for bookmarking. It
knows nothing about the data source, chat client, or reactivity — orchestration
lives in `_handoff_orchestrator.py`.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._handoff_state import HandoffState


# Cap the per-session handoff store so a long session that generates many
# handoffs can't grow memory without bound. The least-recently-used handoff is
# evicted past this; reopening an evicted handoff's chat pill simply no-ops.
MAX_STORED_HANDOFFS = 25


class HandoffStore:
    def __init__(self) -> None:
        self._items: OrderedDict[str, HandoffState] = OrderedDict()

    def has(self, handoff_id: str | None) -> bool:
        return bool(handoff_id) and handoff_id in self._items

    def remember(self, state: HandoffState) -> list[HandoffState]:
        """Store a handoff, evicting the least-recently-used past the cap."""
        removed: list[HandoffState] = []
        replaced = self._items.pop(state.handoff_id, None)
        if replaced is not None:
            removed.append(replaced)
        self._items[state.handoff_id] = state
        self._items.move_to_end(state.handoff_id)
        while len(self._items) > MAX_STORED_HANDOFFS:
            _, evicted = self._items.popitem(last=False)
            removed.append(evicted)
        return removed

    def replace(self, states: list[HandoffState]) -> list[HandoffState]:
        """Replace all handoffs while preserving the supplied LRU order."""
        removed = list(self._items.values())
        self._items.clear()
        for state in states:
            removed.extend(self.remember(state))
        return removed

    def get(self, handoff_id: str | None) -> HandoffState | None:
        """Look up a handoff and mark it most-recently-used."""
        if not handoff_id or handoff_id not in self._items:
            return None
        self._items.move_to_end(handoff_id)
        return self._items[handoff_id]

    def discard(self, handoff_id: str) -> None:
        """Remove a handoff if present, without touching LRU order."""
        self._items.pop(handoff_id, None)

    def values(self) -> list[HandoffState]:
        """Handoff states in least-recently-used order."""
        return list(self._items.values())

    def bookmark_values(self) -> list[dict]:
        """Serialize the store (LRU order) for a Shiny bookmark."""
        return [state.model_dump(mode="json") for state in self._items.values()]
