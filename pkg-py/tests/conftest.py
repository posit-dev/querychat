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


ggsql_render_works = pytest.mark.skipif(
    not _ggsql_render_works(),
    reason="ggsql.render_altair() not functional (build environment issue)",
)
