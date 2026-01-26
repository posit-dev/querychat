"""
Snowflake-specific DataSource implementations.

This module provides DataSource classes for Snowflake connections with
semantic view support. Both SQLAlchemy and Ibis backends are supported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._datasource import IbisSource, SQLAlchemySource
from ._snowflake import (
    IbisExecutor,
    SemanticViewInfo,
    SemanticViewMixin,
    SQLAlchemyExecutor,
    discover_semantic_views,
)

if TYPE_CHECKING:
    import ibis
    from sqlalchemy.engine import Engine

__all__ = ["SnowflakeIbisSource", "SnowflakeSource"]


class SnowflakeSource(SQLAlchemySource, SemanticViewMixin):
    """
    SQLAlchemy-based Snowflake source with semantic view support.

    Extends SQLAlchemySource to automatically detect and provide context about
    Snowflake Semantic Views when available.
    """

    _semantic_views: list[SemanticViewInfo]

    def __init__(
        self,
        engine: Engine,
        table_name: str,
        *,
        discover_semantic_views_flag: bool = True,
    ):
        """
        Initialize with a SQLAlchemy engine connected to Snowflake.

        Parameters
        ----------
        engine
            SQLAlchemy engine connected to Snowflake
        table_name
            Name of the table to query
        discover_semantic_views_flag
            If True (default), automatically discover semantic views at
            initialization. Set to False to skip discovery (e.g., for
            performance or if not needed).

        """
        super().__init__(engine, table_name)

        if discover_semantic_views_flag:
            executor = SQLAlchemyExecutor(engine)
            self._semantic_views = discover_semantic_views(executor)
        else:
            self._semantic_views = []

    def get_schema(self, *, categorical_threshold: int) -> str:
        """
        Generate schema information including semantic view context.

        Parameters
        ----------
        categorical_threshold
            Maximum number of unique values for a text column to be considered
            categorical

        Returns
        -------
        str
            String describing the schema, including semantic view information
            if available

        """
        base_schema = super().get_schema(categorical_threshold=categorical_threshold)
        return self._get_schema_with_semantic_views(base_schema)


class SnowflakeIbisSource(IbisSource, SemanticViewMixin):
    """
    Ibis-based Snowflake source with semantic view support.

    Extends IbisSource to automatically detect and provide context about
    Snowflake Semantic Views when available.
    """

    _semantic_views: list[SemanticViewInfo]

    def __init__(
        self,
        table: ibis.Table,
        table_name: str,
        *,
        discover_semantic_views_flag: bool = True,
    ):
        """
        Initialize with an Ibis Table connected to Snowflake.

        Parameters
        ----------
        table
            Ibis Table from a Snowflake backend
        table_name
            Name of the table to query
        discover_semantic_views_flag
            If True (default), automatically discover semantic views at
            initialization. Set to False to skip discovery (e.g., for
            performance or if not needed).

        """
        super().__init__(table, table_name)

        if discover_semantic_views_flag and self._backend.name.lower() == "snowflake":
            executor = IbisExecutor(self._backend)
            self._semantic_views = discover_semantic_views(executor)
        else:
            self._semantic_views = []

    def get_schema(self, *, categorical_threshold: int) -> str:
        """
        Generate schema information including semantic view context.

        Parameters
        ----------
        categorical_threshold
            Maximum number of unique values for a text column to be considered
            categorical

        Returns
        -------
        str
            String describing the schema, including semantic view information
            if available

        """
        base_schema = super().get_schema(categorical_threshold=categorical_threshold)
        return self._get_schema_with_semantic_views(base_schema)
