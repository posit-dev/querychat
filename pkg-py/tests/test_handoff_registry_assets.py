from importlib.resources import files
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
CANONICAL = REPO_ROOT / "shared" / "handoff-formats.yml"
PYTHON_COPY = REPO_ROOT / "pkg-py" / "src" / "querychat" / "handoff-formats.yml"
R_COPY = REPO_ROOT / "pkg-r" / "inst" / "handoff-formats.yml"


def test_packaged_handoff_registries_match_canonical():
    expected = CANONICAL.read_bytes()
    assert PYTHON_COPY.read_bytes() == expected
    assert R_COPY.read_bytes() == expected


def test_packaged_handoff_language_icons_are_readable():
    image_dir = files("querychat").joinpath("static", "img")
    icon_names = ("handoff-language-python.svg", "handoff-language-r.svg")
    missing = [name for name in icon_names if not image_dir.joinpath(name).is_file()]

    assert not missing, f"Missing packaged handoff icons: {missing}"

    contents = [
        image_dir.joinpath(name).read_text(encoding="utf-8") for name in icon_names
    ]
    assert all("<svg" in content for content in contents)
