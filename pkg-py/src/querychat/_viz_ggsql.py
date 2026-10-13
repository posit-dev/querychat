"""A ggsql reader backed by a querychat executor."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from ._utils import as_narwhals

if TYPE_CHECKING:
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
