"""Helpers for ggsql integration."""

from __future__ import annotations

import weakref
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


# One CachingReader per executor: the memo only pays off across viz calls
# within a chat session, so the reader (and its cache) must outlive any
# single execute_ggsql() call. Weak keys let finished sessions' executors —
# and their caches — be garbage collected.
_readers: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _caching_reader(executor: QueryExecutor) -> ggsql.CachingReader:
    from ggsql import CachingReader

    reader = _readers.get(executor)
    if reader is None:
        reader = CachingReader(ExecutorReader(executor))
        _readers[executor] = reader
    return reader


def execute_ggsql(executor: QueryExecutor, query: str) -> ggsql.Spec:
    """
    Execute a ggsql query against an executor, returning a Spec.

    The whole query (SQL + VISUALISE) executes through a
    ``ggsql.CachingReader`` wrapping the executor: base reads go to the
    executor (preserving database pushdown) and are memoized for the cache
    TTL, while ggsql-generated derived tables live in the reader's private
    in-memory cache. Layer-level sources (``DRAW ... FROM <table>``) work
    because every layer source is staged through that cache.

    Callers that want validation feedback should run ``ggsql.validate()``
    first themselves; the raw query string is what gets executed (a
    ``Validated`` splits ``VISUALISE ... FROM <t>`` into overlapping SQL
    and visual parts that cannot be concatenated back into a valid query).

    Parameters
    ----------
    executor
        The querychat QueryExecutor (or bare DataSource) to read through.
    query
        The full ggsql query string (SQL + VISUALISE).

    Returns
    -------
    ggsql.Spec
        The writer-independent plot specification.

    """
    return _caching_reader(executor).execute(query)
