"""Helpers for ggsql integration."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Literal

from ._utils import to_polars

if TYPE_CHECKING:
    import ggsql

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
    to its private cache — so they are no-ops here.
    """

    def __init__(self, executor: QueryExecutor) -> None:
        self._executor = executor

    def execute_sql(self, sql: str):
        """Run a base read through the executor, as a pyarrow Table."""
        return to_polars(self._executor.execute_query(sql)).to_arrow()

    def register(self, name, table, replace) -> None:
        # Writes belong to CachingReader's cache, never the primary.
        pass

    def unregister(self, name) -> None:
        pass


def caching_reader(executor: QueryExecutor) -> ggsql.CachingReader:
    """
    Create a ``ggsql.CachingReader`` serving base reads through ``executor``.

    The reader owns a private in-memory cache that memoizes source reads, so
    its lifetime should match the span over which repeated reads pay off:
    create one per chat client and reuse it across viz calls. When the client
    is dropped, the reader (and its cache) is freed with it. Callers own the
    reader — there is deliberately no shared registry here, since a
    module-level reader keeps its executor (and cache) alive for the life of
    the process.

    .. note::

        Memoized reads assume the underlying data doesn't change: an
        identical query within the cache TTL (5 minutes by default) is
        served from the cache rather than re-read from the source. If the
        data can change mid-session — e.g. update queries are enabled
        (``QUERYCHAT_ENABLE_UPDATE_QUERIES=true``), or a live database is
        written to by another process — charts may lag those changes by up
        to the TTL. Mutations made through querychat's query tool do not
        invalidate the memo. Tune or disable the cache via the
        ``GGSQL_CACHE_TTL``, ``GGSQL_CACHE_MAX_BYTES``, and
        ``GGSQL_CACHE_DISABLED`` environment variables (read when each
        reader is created).

    Parameters
    ----------
    executor
        The querychat QueryExecutor (or bare DataSource) to read through.

    Returns
    -------
    ggsql.CachingReader
        A caching reader wrapping the executor.

    """
    from ggsql import CachingReader

    return CachingReader(ExecutorReader(executor))


SPATIAL_SMOKE_QUERY = (
    "INSTALL spatial; LOAD spatial; "
    "VISUALISE FROM ggsql:world DRAW spatial FILTER iso_a3 = 'FRA'"
)


def prewarm_spatial(reader: ggsql.CachingReader) -> bool:
    """
    Install and load the DuckDB spatial extension for the reader's cache.

    The first ``INSTALL`` downloads the extension binary (network required);
    afterwards it is cached on disk and this is cheap. Returns ``True`` when
    spatial support is ready. On failure, warns and returns ``False`` so the
    caller can treat the ``"maps"`` capability as unavailable.
    """
    try:
        reader.execute(SPATIAL_SMOKE_QUERY)
    except Exception as e:
        warnings.warn(
            "The 'maps' capability could not be enabled (spatial extension "
            f"setup failed: {e}). Continuing without maps.",
            stacklevel=2,
        )
        return False
    return True


def translate_spatial_error(
    error: Exception, *, maps_state: Literal["enabled", "disabled", "setup_failed"]
) -> str | None:
    """
    Translate ggsql's spatial-extension failure into actionable guidance.

    Returns the translated message, or ``None`` when the error is not a
    spatial setup failure (or maps are fully enabled, making the message
    moot). ``maps_state`` is ``"enabled"`` when the pre-warm succeeded,
    ``"setup_failed"`` when it ran but failed, and ``"disabled"`` when the
    session never opted into maps.
    """
    msg = str(error).lower()
    if maps_state == "enabled" or "spatial" not in msg or "extension" not in msg:
        return None
    if maps_state == "setup_failed":
        return (
            "This query requires map/spatial support, but spatial extension "
            "setup failed earlier in this session (see the warning shown at "
            "setup time, likely a failed extension download). Do not retry "
            "with DRAW spatial, PROJECT TO <map>, or ggsql:world; suggest a "
            "non-map visualization instead."
        )
    return (
        "This query requires map/spatial support, which is not enabled in "
        "this session. Do not retry with DRAW spatial, PROJECT TO <map>, or "
        "ggsql:world; suggest a non-map visualization instead. The app "
        'developer can enable maps with tools=("default", "maps").'
    )


def execute_ggsql(reader: ggsql.CachingReader, query: str) -> ggsql.Spec:
    """
    Execute a ggsql query through a caching reader, returning a Spec.

    The whole query (SQL + VISUALISE) executes through the reader: base reads
    go to the underlying executor (preserving database pushdown) and are
    memoized for the cache TTL, while ggsql-generated derived tables live in
    the reader's private in-memory cache. Layer-level sources (``DRAW ...
    FROM <table>``) work because every layer source is staged through that
    cache.

    Callers that want validation feedback should run ``ggsql.validate()``
    first themselves; the raw query string is what gets executed (a
    ``Validated`` splits ``VISUALISE ... FROM <t>`` into overlapping SQL
    and visual parts that cannot be concatenated back into a valid query).

    Parameters
    ----------
    reader
        A ``ggsql.CachingReader`` from ``caching_reader()``. Reuse one reader
        across related viz calls so memoized base reads are shared.
    query
        The full ggsql query string (SQL + VISUALISE).

    Returns
    -------
    ggsql.Spec
        The writer-independent plot specification.

    """
    return reader.execute(query)
