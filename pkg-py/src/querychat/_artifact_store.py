"""
Per-session LRU store of artifacts.

`ArtifactStore` is a plain container: it holds the session's `ArtifactState`
objects in least-recently-used order and serializes them for bookmarking. It
knows nothing about the data source, chat client, or reactivity — orchestration
(including bookmark *restore*, which regenerates data from the source) lives in
`_artifact_orchestrator.py`.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._artifact_state import ArtifactState


# Cap the per-session artifact store so a long session that generates many
# artifacts can't grow memory without bound (each entry holds the source, chat
# turns, and any bundled CSV). The least-recently-used artifact is evicted past
# this; reopening an evicted artifact's chat pill simply no-ops.
MAX_STORED_ARTIFACTS = 25


class ArtifactStore:
    def __init__(self) -> None:
        self._items: OrderedDict[str, ArtifactState] = OrderedDict()

    def has(self, artifact_id: str | None) -> bool:
        return bool(artifact_id) and artifact_id in self._items

    def remember(self, state: ArtifactState) -> None:
        """Store an artifact, evicting the least-recently-used past the cap."""
        self._items[state.artifact_id] = state
        self._items.move_to_end(state.artifact_id)
        while len(self._items) > MAX_STORED_ARTIFACTS:
            self._items.popitem(last=False)

    def get(self, artifact_id: str | None) -> ArtifactState | None:
        """Look up an artifact and mark it most-recently-used."""
        if not artifact_id or artifact_id not in self._items:
            return None
        self._items.move_to_end(artifact_id)
        return self._items[artifact_id]

    def discard(self, artifact_id: str) -> None:
        """Remove an artifact if present, without touching LRU order."""
        self._items.pop(artifact_id, None)

    def keys(self) -> list[str]:
        """Artifact ids in least-recently-used order."""
        return list(self._items.keys())

    def bookmark_values(self) -> list[dict]:
        """Serialize the store (LRU order) for a Shiny bookmark."""
        return [state.model_dump(mode="json") for state in self._items.values()]
