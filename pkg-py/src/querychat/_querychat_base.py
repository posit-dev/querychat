"""Core base class shared across all framework-specific QueryChat implementations."""

from __future__ import annotations

import copy
import os
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Literal, Optional

import chatlas
import narwhals.stable.v1 as nw
import sqlalchemy
from narwhals.stable.v1.typing import IntoFrameT

from ._datasource import (
    DataFrameSource,
    DataSource,
    IbisSource,
    PolarsLazySource,
    SQLAlchemySource,
)
from ._pin_source import PinSource, is_pins_board
from ._query_executor import (
    DataSourceExecutor,
    DuckDBExecutor,
    PolarsSQLExecutor,
    QueryExecutor,
    check_source_compatibility,
    validate_source_group_compatibility,
)
from ._querychat_core import GREETING_PROMPT
from ._system_prompt import QueryChatSystemPrompt
from ._table_accessor import TableAccessor
from ._utils import MISSING, MISSING_TYPE, is_ibis_table
from ._viz_utils import has_viz_deps, has_viz_tool
from .tools import (
    ResetDashboardCallback,
    UpdateDashboardData,
    tool_get_schema,
    tool_query,
    tool_reset_dashboard,
    tool_update_dashboard,
    tool_visualize,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from narwhals.stable.v1.typing import IntoFrame
    from pins.boards import BaseBoard

    from ._data_dict import DataDict
    from ._viz_tools import VisualizeData

TOOL_GROUPS = Literal["filter", "update", "query", "visualize"]
DEFAULT_TOOLS: tuple[TOOL_GROUPS, ...] = ("filter", "query")

class QueryChatBase(Generic[IntoFrameT]):
    """
    Base class for all QueryChat implementations.

    This class handles:
    - Data source normalization
    - System prompt assembly
    - Chat client configuration
    - Shared methods (client, console, generate_greeting, cleanup)

    Framework-specific subclasses add their own UI methods.
    """

    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine | BaseBoard | None,
        table_name: str | None = None,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_description: Optional[str | Path] = None,
        data_dict: DataDict | str | Path | None = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ):
        if data_description is not None:
            warnings.warn(
                "data_description is deprecated. Use data_dict with per-table "
                "descriptions in the YAML instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Resolve data_dict from path/string or use as-is
        if isinstance(data_dict, (str, Path)):
            from ._data_dict import DataDict as _DataDict

            self._data_dict: DataDict | None = _DataDict.from_yaml(data_dict)
        else:
            self._data_dict = data_dict

        if table_name is None:
            if isinstance(data_source, DataSource):
                table_name = data_source.table_name
            elif data_source is not None:
                raise ValueError(
                    "table_name is required when data_source is not a DataSource"
                )

        # Store table_name for later normalization
        self._table_name = table_name

        if (
            table_name is not None
            and not is_pins_board(data_source)
            and not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name)
        ):
            raise ValueError(
                "Table name must begin with a letter and contain only letters, numbers, and underscores",
            )

        # Multi-table storage: dict of data sources keyed by table name
        self._data_sources: dict[str, DataSource] = {}
        self._query_executor: QueryExecutor | None = None

        # Track server initialization state for add/remove table validation
        self._server_initialized = False

        self.tools = normalize_tools(tools, default=DEFAULT_TOOLS)
        self.greeting = greeting.read_text() if isinstance(greeting, Path) else greeting

        # Store init parameters for deferred system prompt building
        self._prompt_template = prompt_template
        self._data_description = data_description
        self._data_description_mode: Literal["supplied", "inferred", "empty"] = (
            "supplied" if data_description is not None else "empty"
        )
        self._extra_instructions = extra_instructions
        self._categorical_threshold = categorical_threshold

        self._client_spec: str | chatlas.Chat | None = client
        self._client_console = None

        self._system_prompt: QueryChatSystemPrompt | None = None

        # Initialize data source (may be None for deferred pattern)
        if data_source is not None:
            if table_name is None:
                raise ValueError("table_name is required when data_source is provided")
            normalized = normalize_data_source(data_source, table_name)
            self._table_name = normalized.table_name
            self._data_sources[table_name] = normalized
            self._validate_table_in_data_dict(table_name)
            self._auto_fill_data_description()
            self._build_system_prompt()

    def _validate_table_in_data_dict(self, table_name: str) -> None:
        """Raise ValueError if data_dict is set but table_name is not listed in it."""
        if self._data_dict is None:
            return
        if table_name not in self._data_dict.tables:
            available = ", ".join(self._data_dict.tables.keys())
            raise ValueError(
                f"Table '{table_name}' not found in data_dict. "
                f"Available tables: {available}"
            )

    def _auto_fill_data_description(self) -> None:
        """Auto-populate data_description from data source metadata if not user-supplied."""
        if self._data_description_mode == "inferred":
            self._data_description = None
            self._data_description_mode = "empty"
        if self._data_description_mode == "empty" and self._data_sources:
            first_source = next(iter(self._data_sources.values()))
            desc = first_source.get_data_description()
            if desc:
                self._data_description = desc
                self._data_description_mode = "inferred"

    def _build_system_prompt(
        self,
        *,
        data_sources: dict[str, DataSource] | None = None,
    ) -> None:
        """Build/rebuild the system prompt from current or staged data sources."""
        next_data_sources = self._data_sources if data_sources is None else data_sources

        if not next_data_sources:
            raise RuntimeError("Cannot build system prompt without data_source")

        prompt_template = self._prompt_template

        replacement_prompt = QueryChatSystemPrompt(
            prompt_template=prompt_template,
            data_sources=next_data_sources,
            data_description=self._data_description,
            extra_instructions=self._extra_instructions,
            categorical_threshold=self._categorical_threshold,
            data_dict=self._data_dict,
        )
        replacement_executor = self._build_query_executor(data_sources=next_data_sources)
        previous_executor = self._query_executor

        self._system_prompt = replacement_prompt
        self._query_executor = replacement_executor

        if previous_executor is not None:
            try:
                previous_executor.cleanup()
            except Exception:
                pass

    def _build_query_executor(
        self, *, data_sources: dict[str, DataSource] | None = None
    ) -> QueryExecutor:
        """Build a query executor from current or staged data sources."""
        sources = self._data_sources if data_sources is None else data_sources

        validate_source_group_compatibility(sources)

        if len(sources) == 1:
            return DataSourceExecutor(dict(sources))

        first_source = next(iter(sources.values()))

        if isinstance(first_source, DataFrameSource):
            return DuckDBExecutor(
                {n: s for n, s in sources.items() if isinstance(s, DataFrameSource)}
            )
        if isinstance(first_source, PolarsLazySource):
            return PolarsSQLExecutor(
                {n: s for n, s in sources.items() if isinstance(s, PolarsLazySource)}
            )

        return DataSourceExecutor(dict(sources))

    def _require_initialized(self, method_name: str) -> None:
        """Raise if no data sources have been registered."""
        if not self._data_sources:
            raise RuntimeError(
                f"At least one data source must be set before calling {method_name}(). "
                "Either pass data_source to __init__() or call add_table()."
            )

    def _require_query_executor(self, method_name: str) -> QueryExecutor:
        """Raise if query executor is not initialized, otherwise return it."""
        if self._query_executor is None:
            raise RuntimeError(
                f"query executor must be set before calling {method_name}(). "
                "Set the data_source first so querychat can build an executor."
            )
        return self._query_executor

    def _create_session_client(
        self,
        *,
        client_spec: str | chatlas.Chat | None | MISSING_TYPE = MISSING,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None | MISSING_TYPE = MISSING,
        update_dashboard: Callable[[UpdateDashboardData], None] | None = None,
        reset_dashboard: ResetDashboardCallback | None = None,
        visualize: Callable[[VisualizeData], None] | None = None,
    ) -> chatlas.Chat:
        """Create a fresh, fully-configured Chat."""
        spec = self._client_spec if isinstance(client_spec, MISSING_TYPE) else client_spec
        chat = create_client(spec)

        resolved_tools = normalize_tools(tools, default=self.tools)

        if self._system_prompt is not None:
            chat.system_prompt = self._system_prompt.render(resolved_tools)

        executor = self._require_query_executor("_create_session_client")

        # Always register the schema tool regardless of resolved_tools
        chat.register_tool(
            tool_get_schema(
                self._data_dict,
                executor,
                list(self._data_sources.keys()),
                self._categorical_threshold,
            )
        )

        if resolved_tools is None:
            return chat

        if "update" in resolved_tools:
            update_fn = update_dashboard or (lambda _: None)
            user_reset = reset_dashboard or (lambda _table: None)

            chat.register_tool(
                tool_update_dashboard(
                    executor,
                    list(self._data_sources.keys()),
                    update_fn,
                )
            )
            chat.register_tool(
                tool_reset_dashboard(user_reset, list(self._data_sources.keys()))
            )

        if "query" in resolved_tools:
            chat.register_tool(tool_query(executor))

        if "visualize" in resolved_tools:
            viz_fn = visualize or (lambda _: None)
            chat.register_tool(tool_visualize(executor, viz_fn))

        return chat

    def client(
        self,
        *,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None | MISSING_TYPE = MISSING,
        update_dashboard: Callable[[UpdateDashboardData], None] | None = None,
        reset_dashboard: ResetDashboardCallback | None = None,
        visualize: Callable[[VisualizeData], None] | None = None,
    ) -> chatlas.Chat:
        """
        Create a chat client with registered tools.

        Parameters
        ----------
        tools
            Which tools to include: `"filter"`, `"query"`, `"visualize"`,
            or a combination. The legacy name `"update"` is still accepted
            as an alias for `"filter"`.
        update_dashboard
            Callback when update_dashboard tool succeeds.
        reset_dashboard
            Callback when reset_dashboard tool is invoked.
        visualize
            Callback when visualize tool succeeds.

        Returns
        -------
        chatlas.Chat
            A configured chat client.

        """
        self._require_initialized("client")
        return self._create_session_client(
            tools=tools,
            update_dashboard=update_dashboard,
            reset_dashboard=reset_dashboard,
            visualize=visualize,
        )

    def generate_greeting(self, *, echo: Literal["none", "output"] = "none") -> str:
        """Generate a welcome greeting for the chat."""
        self._require_initialized("generate_greeting")
        chat = create_client(self._client_spec)
        if self._system_prompt is not None:
            chat.system_prompt = self._system_prompt.render(self.tools)
        return str(chat.chat(GREETING_PROMPT, echo=echo))

    def console(
        self,
        *,
        new: bool = False,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = "query",
        **kwargs,
    ) -> None:
        """Launch an interactive console chat with the data."""
        self._require_initialized("console")
        if new or self._client_console is None:
            self._client_console = self.client(tools=tools, **kwargs)

        self._client_console.console()

    @property
    def system_prompt(self) -> str:
        """Get the system prompt."""
        self._require_initialized("system_prompt")
        if self._system_prompt is None:
            raise RuntimeError("System prompt not initialized")
        return self._system_prompt.render(self.tools)

    @property
    def data_source(self) -> DataSource:
        """Removed. Use ``qc.table('name').data_source`` instead."""
        raise AttributeError(
            "The .data_source property has been removed. "
            "Use qc.table('name').data_source to access a table's data source, "
            "or qc.add_table(df, 'name') / qc.add_table(df, 'name', replace=True) "
            "to add or replace a table."
        )

    @data_source.setter
    def data_source(self, _value: object) -> None:
        raise AttributeError(
            "The .data_source setter has been removed. "
            "Use qc.add_table(df, 'name') to add a new table, "
            "or qc.add_table(df, 'name', replace=True) to replace an existing one."
        )

    def table_names(self) -> list[str]:
        """
        Return the names of all registered tables.

        Returns
        -------
        list[str]
            List of table names in the order they were added.

        """
        return list(self._data_sources.keys())

    def table(self, name: str) -> TableAccessor:
        """
        Get an accessor for a specific table.

        Parameters
        ----------
        name
            The name of the table to access.

        Returns
        -------
        TableAccessor
            An accessor object with df(), sql(), title() methods.

        Raises
        ------
        ValueError
            If the table doesn't exist.

        """
        if name not in self._data_sources:
            available = ", ".join(self._data_sources.keys())
            raise ValueError(f"Table '{name}' not found. Available: {available}")

        return TableAccessor(self, name)

    def add_table(
        self,
        data_source: IntoFrame | sqlalchemy.Engine,
        table_name: str,
        *,
        replace: bool = False,
    ) -> None:
        """
        Add or replace a table in the QueryChat instance.

        Parameters
        ----------
        data_source
            The data source (DataFrame, LazyFrame, or database connection).
        table_name
            Name for the table.
        replace
            If True, replace an existing table with the same name.
            If False (default), raise ValueError if the table already exists.

        Raises
        ------
        ValueError
            If table_name already exists (and replace=False), is invalid,
            or is not in data_dict.
        RuntimeError
            If called after server() has been invoked.

        """
        if self._server_initialized:
            raise RuntimeError(
                "Cannot add tables after server initialization. "
                "Add all tables before calling .server() or .app()."
            )

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
            raise ValueError(
                "Table name must begin with a letter and contain only "
                "letters, numbers, and underscores"
            )

        if table_name in self._data_sources and not replace:
            raise ValueError(f"Table '{table_name}' already exists")

        self._validate_table_in_data_dict(table_name)

        normalized = normalize_data_source(data_source, table_name)
        try:
            other_sources = {
                name: source
                for name, source in self._data_sources.items()
                if name != table_name
            }
            check_source_compatibility(other_sources, normalized, table_name)
            next_data_sources = dict(self._data_sources)
            next_data_sources[table_name] = normalized

            if replace and self._data_description_mode == "inferred":
                self._data_description = None
                self._data_description_mode = "empty"

            self._build_system_prompt(data_sources=next_data_sources)
        except Exception:
            cleanup_failed_staged_source(data_source, normalized)
            raise

        old_source = self._data_sources.get(table_name)
        self._data_sources = next_data_sources
        if old_source is not None and old_source is not normalized:
            old_source.cleanup()

    def remove_table(self, table_name: str) -> None:
        """
        Remove a table from the QueryChat instance.

        Parameters
        ----------
        table_name
            Name of the table to remove.

        Raises
        ------
        ValueError
            If table doesn't exist or is the last remaining table.
        RuntimeError
            If called after server() has been invoked.

        """
        if self._server_initialized:
            raise RuntimeError(
                "Cannot remove tables after server initialization. "
                "Configure all tables before calling .server() or .app()."
            )

        if table_name not in self._data_sources:
            available = ", ".join(self._data_sources.keys())
            raise ValueError(f"Table '{table_name}' not found. Available: {available}")

        if len(self._data_sources) == 1:
            raise ValueError(
                "Cannot remove last table. At least one table is required."
            )

        removed_source = self._data_sources[table_name]
        next_data_sources = dict(self._data_sources)
        del next_data_sources[table_name]

        # Rebuild system prompt without removed table
        self._build_system_prompt(
            data_sources=next_data_sources,
        )
        self._data_sources = next_data_sources
        removed_source.cleanup()

    def _mark_server_initialized(self) -> None:
        """Mark that the server has been initialized. Prevents add/remove_table."""
        self._server_initialized = True

    def cleanup(self) -> None:
        """Clean up resources associated with all data sources."""
        if self._query_executor is not None:
            self._query_executor.cleanup()
        for source in self._data_sources.values():
            source.cleanup()


def normalize_data_source(
    data_source: IntoFrame | sqlalchemy.Engine | BaseBoard | DataSource,
    table_name: str,
) -> DataSource:
    if isinstance(data_source, DataSource):
        return data_source

    if is_pins_board(data_source):
        return PinSource(data_source, table_name)

    if isinstance(data_source, sqlalchemy.Engine):
        return SQLAlchemySource(data_source, table_name)

    if is_ibis_table(data_source):
        return IbisSource(data_source, table_name)

    src = nw.from_native(data_source, pass_through=True)

    if isinstance(src, nw.DataFrame):
        return DataFrameSource(src, table_name)

    if isinstance(src, nw.LazyFrame):
        native = src.to_native()
        try:
            import polars as pl

            if isinstance(native, pl.LazyFrame):
                return PolarsLazySource(src, table_name)
        except ImportError:
            pass
        raise TypeError(
            f"Unsupported LazyFrame backend: {type(native).__name__} from {type(native).__module__}. "
            "Currently only Polars LazyFrames are supported. "
            "If you believe this type should be supported, please open an issue at "
            "https://github.com/posit-dev/querychat/issues"
        )

    raise TypeError(
        f"Unsupported data source type: {type(data_source)}. "
        "If you believe this type should be supported, please open an issue at "
        "https://github.com/posit-dev/querychat/issues"
    )


def cleanup_failed_staged_source(
    original_source: IntoFrame | sqlalchemy.Engine | DataSource,
    normalized_source: DataSource,
) -> None:
    """
    Clean up transient resources created during a failed staged rebuild.

    Only DataFrameSource owns a fresh disposable connection created during
    normalization. SQLAlchemySource wraps a caller-owned engine, while
    PolarsLazySource and IbisSource do not allocate disposable resources here.
    """
    if isinstance(original_source, (DataSource, sqlalchemy.Engine)):
        return

    if isinstance(normalized_source, DataFrameSource):
        normalized_source.cleanup()


def create_client(client: str | chatlas.Chat | None) -> chatlas.Chat:
    """Resolve a client spec into a fresh Chat with no conversation history."""
    if client is None:
        client = os.getenv("QUERYCHAT_CLIENT", None)

    if client is None:
        client = "openai"

    if isinstance(client, chatlas.Chat):
        chat = copy.deepcopy(client)
    else:
        chat = chatlas.ChatAuto(provider_model=client)

    chat.set_turns([])
    return chat


def normalize_tools(
    tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None | MISSING_TYPE,
    default: tuple[TOOL_GROUPS, ...] | set[str] | None,
    *,
    check_deps: bool = True,
) -> set[str] | None:
    if tools is None or tools == ():
        resolved = None
    elif isinstance(tools, MISSING_TYPE):
        resolved = set(default) if default is not None else None
    elif isinstance(tools, str):
        resolved = {tools}
    else:
        resolved = set(tools)
    if resolved is not None:
        resolved = {"update" if t == "filter" else t for t in resolved}
    if not check_deps:
        return resolved
    if has_viz_tool(resolved) and not has_viz_deps():
        raise ImportError(
            "Visualization tools require ggsql, altair, shinywidgets, and "
            "vl-convert-python. Install them with: pip install querychat[viz]"
        )
    return resolved
