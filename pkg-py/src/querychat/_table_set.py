"""Immutable bundle of the tables a chat can query."""

from __future__ import annotations

from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING, Generic

from narwhals.stable.v1.typing import IntoFrameT

from ._query_executor import QueryExecutor, build_query_executor

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ._datasource import DataSource
    from ._system_prompt import QueryChatSystemPrompt


class TableSet(Generic[IntoFrameT]):
    """
    The tables a chat can query, plus the prompt and executor built from them.

    A ``TableSet`` is never mutated after construction. ``QueryChatBase``
    holds one built from ``add_table()`` calls; ``QueryChat.server()`` derives
    a second one when a session registers its own table, so a running session
    never observes changes made after it started.
    """

    def __init__(
        self,
        data_sources: Mapping[str, DataSource[IntoFrameT]],
        system_prompt: QueryChatSystemPrompt,
    ) -> None:
        if not data_sources:
            raise ValueError("TableSet requires at least one data source")
        self._data_sources: Mapping[str, DataSource[IntoFrameT]] = MappingProxyType(
            dict(data_sources)
        )
        self._system_prompt = system_prompt

    @property
    def data_sources(self) -> Mapping[str, DataSource[IntoFrameT]]:
        return self._data_sources

    @property
    def system_prompt(self) -> QueryChatSystemPrompt:
        return self._system_prompt

    @cached_property
    def executor(self) -> QueryExecutor:
        return build_query_executor(self.data_sources)

    @property
    def executor_built(self) -> bool:
        return "executor" in self.__dict__

    @property
    def table_names(self) -> list[str]:
        return list(self.data_sources)

    def cleanup_executor(self) -> None:
        """
        Close the executor if it was ever built. Never touches data sources.

        The cached executor is reset (matching R's ``TableSet``), so a later
        access rebuilds it.
        """
        if self.executor_built:
            try:
                self.executor.cleanup()
            finally:
                del self.__dict__["executor"]
