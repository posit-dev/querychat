"""Helpers for ggsql integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    def register(self, name, table, replace) -> None:  # noqa: ARG002
        # Writes belong to CachingReader's cache, never the primary.
        pass

    def unregister(self, name) -> None:  # noqa: ARG002
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
