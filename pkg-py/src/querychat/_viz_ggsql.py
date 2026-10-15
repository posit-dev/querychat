"""A ggsql reader backed by a querychat executor."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from ._utils import as_narwhals

if TYPE_CHECKING:
    import ggsql
    import pyarrow as pa

    from ._datasource import DataSource
    from ._query_executor import QueryExecutor


class ExecutorReader:
    """
    ggsql reader protocol over a querychat executor (source reads only).

    Designed exclusively for composition with ``ggsql.CachingReader``: the
    caching reader stages every derived table into its own in-memory cache,
    so this object only ever serves base reads of the user's data, executed
    through the querychat executor (preserving database pushdown).

    ``register``/``unregister`` are part of ggsql's reader protocol but are
    never called in this composition — ``CachingReader`` routes all writes
    to its private cache — so they only warn (loudly, in case a future
    ggsql changes that routing, which would otherwise silently drop
    writes).
    """

    def __init__(self, executor: QueryExecutor | DataSource) -> None:
        self._executor = executor

    def execute_sql(self, sql: str) -> pa.Table:
        """Run a base read through the executor, as a pyarrow Table."""
        # Narwhals normalizes every execute_query() result type (pandas,
        # polars, pyarrow, lazy ibis, ...) and to_arrow() converts directly,
        # so this path does not require polars (only pyarrow, which ggsql
        # itself guarantees).
        return as_narwhals(self._executor.execute_query(sql)).to_arrow()

    def register(self, name, table, replace) -> None:
        # Writes belong to CachingReader's cache, never the primary.
        warnings.warn(
            f"ExecutorReader.register({name!r}, table={type(table).__name__}, "
            f"replace={replace}) called: ggsql routed a write to the primary "
            "reader, which is a no-op by design. The registered table will "
            "not be visible to subsequent reads.",
            stacklevel=2,
        )

    def unregister(self, name) -> None:
        warnings.warn(
            f"ExecutorReader.unregister({name!r}) called: ggsql routed a "
            "write to the primary reader, which is a no-op by design.",
            stacklevel=2,
        )


SPATIAL_SMOKE_QUERY = "VISUALISE FROM ggsql:world DRAW spatial FILTER iso_a3 = 'FRA'"


def install_extension(reader: ggsql.CachingReader, name: str) -> None:
    """
    Install and load a DuckDB extension on the reader's cache connection.

    All ggsql-generated derived SQL runs on the cache connection, never on
    the user's (typically locked-down) data source, so extensions must be
    installed here. The first ``INSTALL`` downloads the binary (network
    required); afterwards it is cached on disk.
    """
    reader.execute_sql_cached(f"INSTALL {name}")
    reader.execute_sql_cached(f"LOAD {name}")


def prewarm_icu(reader: ggsql.CachingReader) -> None:
    """
    Set up the DuckDB ICU extension (time zones, locale-aware collations).

    DuckDB's CLI and Python client load ICU by default, so SQL written
    against "DuckDB" — by users or LLMs — assumes it. Failure is
    non-fatal: warns and continues.
    """
    try:
        install_extension(reader, "icu")
    except Exception as e:
        warnings.warn(
            "Could not set up the DuckDB ICU extension on the visualization "
            f"engine ({e}). Continuing without it: time zone operations "
            "(e.g. interval arithmetic on timestamptz columns) and "
            "locale-aware collations will be unavailable in visualizations.",
            stacklevel=2,
        )


def prewarm_spatial(reader: ggsql.CachingReader) -> bool:
    """
    Set up the DuckDB spatial extension for the ``"maps"`` capability.

    The smoke query exercises the full spatial path (extension load,
    builtin ``ggsql:world`` registration, spatial layer execution).
    Failure warns and returns ``False`` so the caller can treat ``"maps"``
    as unavailable.
    """
    try:
        install_extension(reader, "spatial")
        reader.execute(SPATIAL_SMOKE_QUERY)
    except Exception as e:
        warnings.warn(
            "The 'maps' capability could not be enabled (spatial extension "
            f"setup failed: {e}). Continuing without maps.",
            stacklevel=2,
        )
        return False
    return True


def translate_spatial_error(error: Exception) -> str | None:
    """
    Translate ggsql's spatial-extension failure into actionable guidance.

    Only call this when maps was requested but spatial setup failed earlier
    in the session (see ``prewarm_spatial``). Returns the translated
    message, or ``None`` when the error is not a spatial setup failure.

    Matches DuckDB error wording as of DuckDB 1.5.5 — both the
    extension-not-found form and the catalog error from calling an
    ``st_*`` function after a failed LOAD. If a DuckDB upgrade rewords
    these errors, update the patterns and tests together.
    """
    msg = str(error).lower()
    is_extension_missing = "spatial" in msg and "extension" in msg
    is_st_function_missing = (
        "scalar function" in msg and "st_" in msg and "does not exist" in msg
    )
    if not (is_extension_missing or is_st_function_missing):
        return None
    return (
        "This query requires map/spatial support, but spatial extension "
        "setup failed earlier in this session (see the warning shown at "
        "setup time, likely a failed extension download). Do not retry "
        "with DRAW spatial, PROJECT TO <map>, or ggsql:world; suggest a "
        "non-map visualization instead."
    )
