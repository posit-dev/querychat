import io
import zipfile

from querychat._artifact_orchestrator import build_artifact_zip


def read_zip(data: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {n: zf.read(n).decode() for n in zf.namelist()}


def test_zip_contains_source_readme_and_bundled():
    data = build_artifact_zip(
        source="print('hi')",
        source_filename="artifact.py",
        readme="# Readme",
        bundled_files={"titanic.csv": b"a,b\n1,2\n"},
    )
    contents = read_zip(data)
    assert contents["artifact.py"] == "print('hi')"
    assert contents["README.md"] == "# Readme"
    assert contents["titanic.csv"] == "a,b\n1,2\n"


def test_zip_without_bundled_files():
    data = build_artifact_zip(
        source="x",
        source_filename="artifact.qmd",
        readme="# R",
        bundled_files={},
    )
    contents = read_zip(data)
    assert set(contents.keys()) == {"artifact.qmd", "README.md"}
