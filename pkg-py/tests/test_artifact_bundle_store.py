from querychat._artifact_bundle_store import ArtifactBundleStore


def test_put_copies_files_and_get_returns_immutable_bundle():
    store = ArtifactBundleStore()
    files = {"tips.csv": b"total_bill\n10\n"}

    bundle = store.put(files)
    files["tips.csv"] = b"total_bill\n20\n"

    stored = store.get(bundle.bundle_id)

    assert stored is not None
    assert stored.bundled_files["tips.csv"] == b"total_bill\n10\n"


def test_get_marks_bundle_recent_for_lru_eviction(monkeypatch):
    monkeypatch.setattr(
        "querychat._artifact_bundle_store.MAX_STORED_BUNDLE_BYTES",
        4,
    )
    store = ArtifactBundleStore()
    first = store.put({"one.csv": b"aa"})
    second = store.put({"two.csv": b"bb"})

    assert store.get(first.bundle_id) is not None
    third = store.put({"three.csv": b"cc"})

    assert store.get(first.bundle_id) is not None
    assert store.get(second.bundle_id) is None
    assert store.get(third.bundle_id) is not None


def test_discard_removes_bundle():
    store = ArtifactBundleStore()
    first = store.put({"one.csv": b"1"})

    store.discard(first.bundle_id)

    assert store.get(first.bundle_id) is None
