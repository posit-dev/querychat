import io
import zipfile

from querychat._handoff_orchestrator import build_handoff_zip
from querychat._handoff_readme import build_readme
from querychat._handoff_types import resolve_handoff_type


def read_zip(data: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {n: zf.read(n).decode() for n in zf.namelist()}


def test_zip_contains_source_readme_and_bundled():
    data = build_handoff_zip(
        source="print('hi')",
        source_filename="handoff.py",
        readme="# Readme",
        bundled_files={"titanic.csv": b"a,b\n1,2\n"},
    )
    contents = read_zip(data)
    assert contents["handoff.py"] == "print('hi')"
    assert contents["README.md"] == "# Readme"
    assert contents["titanic.csv"] == "a,b\n1,2\n"


def test_zip_without_bundled_files():
    data = build_handoff_zip(
        source="x",
        source_filename="handoff.qmd",
        readme="# R",
        bundled_files={},
    )
    contents = read_zip(data)
    assert set(contents.keys()) == {"handoff.qmd", "README.md"}


def test_readme_describes_bundled_csv_as_fixed_snapshot():
    readme = build_readme(
        handoff_type=resolve_handoff_type("quarto-dashboard", "python"),
        source_filename="handoff.qmd",
        summary="",
        install_instructions="",
        run_instructions="",
        data_instructions="Load `tips.csv` before running.",
        bundled_files=["tips.csv"],
    )

    assert "fixed CSV snapshot captured when this handoff was generated" in readme


def test_readme_describes_unbundled_data_as_live_access():
    readme = build_readme(
        handoff_type=resolve_handoff_type("quarto-dashboard", "python"),
        source_filename="handoff.qmd",
        summary="",
        install_instructions="",
        run_instructions="",
        data_instructions="Connect to the configured database.",
        bundled_files=[],
    )

    assert "live data access and credentials" in readme
