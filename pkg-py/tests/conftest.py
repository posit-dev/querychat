"""Shared pytest fixtures for querychat unit tests."""

import polars as pl
import pytest


def _ggsql_render_works() -> bool:
    """Check if ggsql.render_altair() is functional (build can be broken in some envs)."""
    try:
        import ggsql

        df = pl.DataFrame({"x": [1, 2], "y": [3, 4]})
        result = ggsql.render_altair(df, "VISUALISE x, y DRAW point")
        spec = result.to_dict()
        return "$schema" in spec
    except (ValueError, ImportError):
        return False


_ggsql_available = _ggsql_render_works()


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests marked with @pytest.mark.ggsql when ggsql is broken."""
    if _ggsql_available:
        return
    skip = pytest.mark.skip(
        reason="ggsql.render_altair() not functional (build environment issue)"
    )
    for item in items:
        if "ggsql" in item.keywords:
            item.add_marker(skip)


def long_enough_source(marker: str = "placeholder") -> str:
    """
    Return a placeholder that clears HANDOFF_MIN_SOURCE_LENGTH.

    The filler pads past the length floor regardless of `marker`'s own length,
    for tests that only care about a short marker value appearing in the source.
    """
    return f"{marker}\n\n" + "# filler\n" * 40
