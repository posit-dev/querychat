from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
CANONICAL = REPO_ROOT / "shared" / "artifact-formats.yml"
PYTHON_COPY = REPO_ROOT / "pkg-py" / "src" / "querychat" / "artifact-formats.yml"
R_COPY = REPO_ROOT / "pkg-r" / "inst" / "artifact-formats.yml"


def test_packaged_artifact_registries_match_canonical():
    expected = CANONICAL.read_bytes()
    assert PYTHON_COPY.read_bytes() == expected
    assert R_COPY.read_bytes() == expected
