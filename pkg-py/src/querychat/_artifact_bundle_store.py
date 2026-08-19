from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Mapping


# Keep all immutable CSV snapshots for one session within a bounded 25 MB budget.
MAX_STORED_BUNDLE_BYTES = 25 * 1024 * 1024


class ArtifactSnapshotUnavailableError(ValueError):
    """A version's immutable artifact data snapshot is no longer available."""


@dataclass(frozen=True)
class ArtifactBundle:
    bundle_id: str
    bundled_files: Mapping[str, bytes]
    data_instructions: str

    @property
    def byte_size(self) -> int:
        return sum(len(data) for data in self.bundled_files.values())


class ArtifactBundleStore:
    def __init__(self) -> None:
        self._items: OrderedDict[str, ArtifactBundle] = OrderedDict()
        self._total_bytes = 0

    def __len__(self) -> int:
        return len(self._items)

    def put(
        self,
        bundled_files: Mapping[str, bytes],
        data_instructions: str,
    ) -> ArtifactBundle:
        files = MappingProxyType(dict(bundled_files))
        bundle = ArtifactBundle(
            bundle_id=uuid4().hex,
            bundled_files=files,
            data_instructions=data_instructions,
        )
        if bundle.byte_size > MAX_STORED_BUNDLE_BYTES:
            raise ValueError("Artifact data snapshot exceeds session storage limit.")
        self._items[bundle.bundle_id] = bundle
        self._total_bytes += bundle.byte_size
        self.evict()
        return bundle

    def get(self, bundle_id: str | None) -> ArtifactBundle | None:
        if bundle_id is None:
            return None
        bundle = self._items.get(bundle_id)
        if bundle is not None:
            self._items.move_to_end(bundle_id)
        return bundle

    def discard(self, bundle_id: str | None) -> None:
        if bundle_id is None:
            return
        bundle = self._items.pop(bundle_id, None)
        if bundle is not None:
            self._total_bytes -= bundle.byte_size

    def clear(self) -> None:
        self._items.clear()
        self._total_bytes = 0

    def evict(self) -> None:
        while self._total_bytes > MAX_STORED_BUNDLE_BYTES:
            _, bundle = self._items.popitem(last=False)
            self._total_bytes -= bundle.byte_size
