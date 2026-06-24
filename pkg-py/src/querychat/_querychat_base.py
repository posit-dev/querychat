"""Core base class shared across all framework-specific QueryChat implementations."""

from __future__ import annotations

import contextlib
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
from ._querychat_core import (
    AppState,
    AppStateDict,
    create_app_state,
    warn_multi_table_flat_accessor,
)
from ._querychat_greeter import QueryChatGreeter
from ._system_prompt import QueryChatSystemPrompt
from ._utils import MISSING, MISSING_TYPE, is_ibis_backend, is_ibis_table
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

    from ibis.backends.sql import SQLBackend
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
        data_source: IntoFrame | sqlalchemy.Engine | BaseBoard | None = None,
        table_name: str | None = None,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | list[DataDict | str | Path] | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
    ):
        self._data_dicts: list[DataDict] = _normalize_data_dicts(data_dict)

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
        self._extra_instructions = extra_instructions
        self._categorical_threshold = categorical_threshold

        self._client_spec: str | chatlas.Chat | None = client
        self._client_console = None

        self._system_prompt: QueryChatSystemPrompt | None = None
        self._greeter: QueryChatGreeter | None = None

        if data_source is not None:
            if table_name is None:
                if isinstance(data_source, DataSource):
                    table_name = data_source.table_name
                else:
                    raise ValueError(
                        "table_name is required when data_source is provided"
                    )
            self.add_table(data_source, table_name, include_in_greeting=True)

    def _build_system_prompt(
        self,
        *,
        data_sources: dict[str, DataSource] | None = None,
    ) -> None:
        """Build/rebuild the system prompt from current or staged data sources."""
        next_data_sources = self._data_sources if data_sources is None else data_sources

        if not next_data_sources:
            raise RuntimeError("Cannot build system prompt without data_source")

        client_has_history = (
            isinstance(self._client_spec, chatlas.Chat)
            and bool(self._client_spec.get_turns())
        ) or (
            self._client_console is not None and bool(self._client_console.get_turns())
        )
        if client_has_history:
            warnings.warn(
                "System prompt rebuilt after chat history exists. "
                "This invalidates any prompt caching from prior turns. "
                "Configure all tables before starting a conversation.",
                UserWarning,
                stacklevel=3,
            )

        self._system_prompt = QueryChatSystemPrompt(
            prompt_template=self._prompt_template,
            data_sources=next_data_sources,
            data_description=self._data_description,
            extra_instructions=self._extra_instructions,
            categorical_threshold=self._categorical_threshold,
            data_dicts=self._data_dicts,
        )

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

    def _require_single_table(self, method_name: str) -> None:
        """Raise if multiple tables are registered, directing to per-table API."""
        if len(self._data_sources) > 1:
            table_list = ", ".join(f"'{n}'" for n in self._data_sources)
            raise AttributeError(
                f"Cannot use .{method_name}() with multiple tables ({table_list}). "
                f"Use .table('name').{method_name}() for per-table access."
            )

    def _require_query_executor(self, method_name: str) -> QueryExecutor:
        """Return the cached executor, building it lazily on first use."""
        if self._query_executor is None:
            if not self._data_sources:
                raise RuntimeError(
                    f"query executor must be set before calling {method_name}(). "
                    "Set the data_source first so querychat can build an executor."
                )
            self._query_executor = self._build_query_executor()
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
        spec = (
            self._client_spec if isinstance(client_spec, MISSING_TYPE) else client_spec
        )
        chat = create_client(spec)

        resolved_tools = normalize_tools(tools, default=self.tools)

        if self._system_prompt is not None:
            chat.system_prompt = self._system_prompt.render(resolved_tools)

        if resolved_tools is None:
            return chat

        executor = self._require_query_executor("_create_session_client")

        # Always register the schema tool (for all non-None tool sets)
        chat.register_tool(
            tool_get_schema(
                self._data_dicts,
                executor,
                list(self._data_sources.keys()),
                self._categorical_threshold,
            )
        )

        if "update" in resolved_tools:
            update_fn = update_dashboard or (lambda _: None)
            user_reset = reset_dashboard or (lambda _table: None)

            chat.register_tool(
                tool_update_dashboard(
                    executor,
                    list(self._data_sources.keys()),
                    update_fn,
                    multi_table=len(self._data_sources) > 1,
                )
            )
            chat.register_tool(
                tool_reset_dashboard(user_reset, list(self._data_sources.keys()))
            )

        if "query" in resolved_tools:
            chat.register_tool(
                tool_query(executor, multi_table=len(self._data_sources) > 1)
            )

        if "visualize" in resolved_tools:
            viz_fn = visualize or (lambda _: None)
            chat.register_tool(
                tool_visualize(
                    executor, viz_fn, multi_table=len(self._data_sources) > 1
                )
            )

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
        return self.greeter.generate(echo=echo)

    @property
    def greeter(self) -> QueryChatGreeter:
        """Greeting configuration and generator for this QueryChat instance."""
        if self._greeter is None:
            self._greeter = QueryChatGreeter(self)
        return self._greeter

    def _build_greeting_client(self) -> chatlas.Chat:
        """Build a fresh chat client configured with the greeting system prompt."""
        tbls = [n for n in self.greeter.tables if n in self._data_sources]
        sources = {n: self._data_sources[n] for n in tbls}
        greeting_prompt_obj = QueryChatSystemPrompt(
            prompt_template=self.greeter.prompt,
            data_sources=sources,
            data_description=self._data_description,
            extra_instructions=None,
            categorical_threshold=self._categorical_threshold,
            data_dicts=self._data_dicts,
        )
        chat = create_client(self._client_spec)
        chat.set_turns([])
        chat.system_prompt = greeting_prompt_obj.render(None)
        return chat

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
        """Removed. Use ``add_table()`` and ``remove_table()`` to manage tables."""
        raise AttributeError(
            "The .data_source property has been removed. "
            "Use qc.add_table(df, 'name') to add a new table, "
            "or qc.add_table(df, 'name', replace=True) to replace an existing one."
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

    def add_table(
        self,
        data_source: IntoFrame | sqlalchemy.Engine | BaseBoard,
        table_name: str,
        *,
        replace: bool = False,
        include_in_greeting: bool = False,
    ) -> None:
        """
        Add or replace a table in the QueryChat instance.

        Parameters
        ----------
        data_source
            The data source (DataFrame, LazyFrame, database connection, or pins board).
        table_name
            Name for the table.
        replace
            If True, replace an existing table with the same name.
            If False (default), raise ValueError if the table already exists.
        include_in_greeting
            If True, include this table's schema in the greeting system prompt.

        Raises
        ------
        TypeError
            If include_in_greeting is not a bool.
        ValueError
            If table_name already exists (and replace=False) or is invalid.
        RuntimeError
            If called after server() has been invoked.

        """
        if self._server_initialized:
            raise RuntimeError(
                "Cannot add tables after server initialization. "
                "Add all tables before calling .server() or .app()."
            )

        if not isinstance(include_in_greeting, bool):
            raise TypeError(
                "include_in_greeting must be True or False, got "
                f"{type(include_in_greeting).__name__}."
            )

        if not is_pins_board(data_source) and not re.match(
            r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name
        ):
            raise ValueError(
                "Table name must begin with a letter and contain only "
                "letters, numbers, and underscores"
            )

        if table_name in self._data_sources and not replace:
            raise ValueError(f"Table '{table_name}' already exists")

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

            self._build_system_prompt(data_sources=next_data_sources)
        except Exception:
            cleanup_failed_staged_source(data_source, normalized)
            raise

        old_source = self._data_sources.get(table_name)
        self._data_sources = next_data_sources
        if old_source is not None and old_source is not normalized:
            old_source.cleanup()
        if self._query_executor is not None:
            with contextlib.suppress(Exception):
                self._query_executor.cleanup()
            self._query_executor = None

        if include_in_greeting and table_name not in self.greeter.tables:
            self.greeter.tables = [*self.greeter.tables, table_name]

    def add_tables(  # noqa: PLR0912
        self,
        data_source: sqlalchemy.Engine | SQLBackend,
        tables: list[str] | None = None,
        *,
        replace: bool = False,
        include_in_greeting: bool | str | list[str] = False,
    ) -> None:
        """
        Add multiple tables from a SQLAlchemy engine or Ibis backend in a single call.

        Unlike calling :meth:`add_table` repeatedly, this method builds the
        system prompt exactly once after all tables have been staged, avoiding
        N-1 spurious intermediate rebuilds.

        Parameters
        ----------
        data_source
            A SQLAlchemy engine or Ibis SQL backend. Pass individual DataFrames
            or other sources via :meth:`add_table`.
        tables
            Table names to register. When ``None``, all tables returned by
            the backend's table-discovery method are used.
        replace
            If ``True``, replace any existing table whose name appears in
            ``tables``. If ``False`` (default), raise ``ValueError`` if any
            name already exists.
        include_in_greeting
            ``True`` to include all added tables in the greeting, ``False`` (default)
            for none, or a table name (or list of table names) to include. Any
            other type raises ``TypeError``.

        Raises
        ------
        TypeError
            If ``data_source`` is not a ``sqlalchemy.Engine`` or Ibis SQL backend.
        ValueError
            If the resolved table list is empty, any name is invalid, or any
            name already exists (and ``replace=False``).
        RuntimeError
            If called after :meth:`server` has been invoked.

        Examples
        --------
        Register all tables from a SQLAlchemy engine:

        >>> qc = QueryChat()
        >>> qc.add_tables(engine)

        Register a specific subset:

        >>> qc.add_tables(engine, ["orders", "customers"])

        Register all tables from an Ibis backend:

        >>> import ibis
        >>> backend = ibis.duckdb.connect("mydb.duckdb")
        >>> qc.add_tables(backend)

        """
        if self._server_initialized:
            raise RuntimeError(
                "Cannot add tables after server initialization. "
                "Add all tables before calling .server() or .app()."
            )

        if isinstance(data_source, sqlalchemy.Engine):
            if tables is None:
                tables = sqlalchemy.inspect(data_source).get_table_names()

            def normalized_builder(name: str) -> DataSource:
                return normalize_data_source(data_source, name)
        elif is_ibis_backend(data_source):
            if tables is None:
                tables = data_source.list_tables()

            def normalized_builder(name: str) -> DataSource:
                return normalize_data_source(data_source.table(name), name)
        else:
            raise TypeError(
                f"add_tables() requires a sqlalchemy.Engine or ibis SQLBackend, "
                f"got {type(data_source).__name__}. "
                "Use add_table() for DataFrames and other source types."
            )

        if not tables:
            raise ValueError("No tables found in database")

        for table_name in tables:
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
                raise ValueError(
                    "Table name must begin with a letter and contain only "
                    "letters, numbers, and underscores"
                )
            if table_name in self._data_sources and not replace:
                raise ValueError(f"Table '{table_name}' already exists")

        normalized = {name: normalized_builder(name) for name in tables}

        staged: dict[str, DataSource] = {}
        for name, source in normalized.items():
            other_sources = {n: s for n, s in self._data_sources.items() if n != name}
            check_source_compatibility({**other_sources, **staged}, source, name)
            staged[name] = source

        next_data_sources = {**self._data_sources, **normalized}
        self._build_system_prompt(data_sources=next_data_sources)

        for name, normalized_source in normalized.items():
            old_source = self._data_sources.get(name)
            if old_source is not None and old_source is not normalized_source:
                old_source.cleanup()

        self._data_sources = next_data_sources
        if self._query_executor is not None:
            with contextlib.suppress(Exception):
                self._query_executor.cleanup()
            self._query_executor = None

        if isinstance(include_in_greeting, bool):
            greeting_names = list(tables) if include_in_greeting else []
        elif isinstance(include_in_greeting, str):
            greeting_names = (
                [include_in_greeting] if include_in_greeting in tables else []
            )
        elif isinstance(include_in_greeting, list) and all(
            isinstance(name, str) for name in include_in_greeting
        ):
            greeting_names = [name for name in include_in_greeting if name in tables]
        else:
            raise TypeError(
                "include_in_greeting must be True, False, or a table name "
                "(or list of table names), got "
                f"{type(include_in_greeting).__name__}."
            )

        new_greeting = list(self.greeter.tables)
        for name in greeting_names:
            if name not in new_greeting:
                new_greeting.append(name)
        if new_greeting != self.greeter.tables:
            self.greeter.tables = new_greeting

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

        self._build_system_prompt(data_sources=next_data_sources)
        self._data_sources = next_data_sources
        if self._query_executor is not None:
            with contextlib.suppress(Exception):
                self._query_executor.cleanup()
            self._query_executor = None
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
    original_source: IntoFrame | sqlalchemy.Engine | BaseBoard | DataSource,
    normalized_source: DataSource,
) -> None:
    """
    Clean up transient resources created during a failed staged rebuild.

    DataFrameSource and PinSource both allocate disposable connections during
    normalization. SQLAlchemySource wraps a caller-owned engine, while
    PolarsLazySource and IbisSource do not allocate disposable resources here.
    """
    if isinstance(original_source, (DataSource, sqlalchemy.Engine)):
        return

    if isinstance(normalized_source, (DataFrameSource, PinSource)):
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


def _normalize_data_dicts(
    data_dict: DataDict | str | Path | list[DataDict | str | Path] | None,
) -> list[DataDict]:
    from ._data_dict import DataDict as _DataDict

    if data_dict is None:
        return []
    if isinstance(data_dict, list):
        return [
            _DataDict.from_yaml(item) if isinstance(item, (str, Path)) else item
            for item in data_dict
        ]
    if isinstance(data_dict, (str, Path)):
        return [_DataDict.from_yaml(data_dict)]
    return [data_dict]


def _get_table_sql(state: AppStateDict | None, table: str) -> str | None:
    """Extract the SQL for a specific table from a serialized state dict."""
    if state is None:
        return None
    per_table = state.get("table_states")
    if per_table and table in per_table:
        return per_table[table].get("sql")
    # Backward compat: if table matches the active table and no table_states key exists
    if state.get("table") == table:
        return state.get("sql")
    return None


class StateDictQueryChat(QueryChatBase[IntoFrameT]):
    """Base for Dash and Gradio adapters that pass serialized state dicts per request."""

    def _client_factory(
        self,
        update_cb: Callable[[UpdateDashboardData], None],
        reset_cb: Callable[[str], None],
    ) -> chatlas.Chat:
        """Create a chat client with dashboard callbacks."""
        return self.client(update_dashboard=update_cb, reset_dashboard=reset_cb)

    def _df_for_source(
        self, data_source: DataSource[IntoFrameT], sql: str | None
    ) -> IntoFrameT:
        if sql:
            with contextlib.suppress(Exception):
                return self._require_query_executor("df").execute_query(sql)
        return data_source.get_data()

    def df(self, state: AppStateDict | None, *, table: str | None = None) -> IntoFrameT:
        """
        Get the current DataFrame from state.

        Parameters
        ----------
        state
            The state dictionary from a framework callback.
        table
            Table name to read. Defaults to the active table when None.

        Returns
        -------
        :
            The filtered data if a SQL query is active, otherwise the full dataset.
            Returns a LazyFrame if the data source is lazy.

        """
        if table is not None:
            return self._df_for_source(
                self._data_sources[table], _get_table_sql(state, table)
            )
        if len(self._data_sources) > 1:
            primary_name = next(iter(self._data_sources))
            table_list = ", ".join(f"'{n}'" for n in self._data_sources)
            warn_multi_table_flat_accessor("df", primary_name, table_list)
            return self._df_for_source(
                self._data_sources[primary_name], _get_table_sql(state, primary_name)
            )
        data_source = self._get_state_data_source(state)
        return self._df_for_source(data_source, state.get("sql") if state else None)

    def _get_state_data_source(
        self, state: AppStateDict | None
    ) -> DataSource[IntoFrameT]:
        """Resolve the full-data source for a serialized state payload."""
        self._require_initialized("_get_state_data_source")
        first_source: DataSource[IntoFrameT] = next(iter(self._data_sources.values()))
        if not state:
            return first_source
        table_name = state.get("table")
        if table_name is not None and table_name in self._data_sources:
            return self._data_sources[table_name]
        return first_source

    def sql(
        self, state: AppStateDict | None, *, table: str | None = None
    ) -> str | None:
        """
        Get the current SQL query from state.

        Parameters
        ----------
        state
            The state dictionary from a framework callback.
        table
            Table name. Defaults to the active table when None.

        Returns
        -------
        :
            The current SQL query, or None if showing full dataset.

        """
        if table is not None:
            return _get_table_sql(state, table)
        if len(self._data_sources) > 1:
            primary_name = next(iter(self._data_sources))
            table_list = ", ".join(f"'{n}'" for n in self._data_sources)
            warn_multi_table_flat_accessor("sql", primary_name, table_list)
            return _get_table_sql(state, primary_name)
        return state.get("sql") if state else None

    def _title_for_table(self, state: AppStateDict | None, table: str) -> str | None:
        if state is None:
            return None
        per_table = state.get("table_states")
        if per_table and table in per_table:
            return per_table[table].get("title")
        if state.get("table") == table:
            return state.get("title")
        return None

    def title(
        self, state: AppStateDict | None, *, table: str | None = None
    ) -> str | None:
        """
        Get the current query title from state.

        Parameters
        ----------
        state
            The state dictionary from a framework callback.
        table
            Table name. Defaults to the active table when None.

        Returns
        -------
        :
            A short description of the current filter, or None if showing full dataset.

        """
        if table is not None:
            return self._title_for_table(state, table)
        if len(self._data_sources) > 1:
            primary_name = next(iter(self._data_sources))
            table_list = ", ".join(f"'{n}'" for n in self._data_sources)
            warn_multi_table_flat_accessor("title", primary_name, table_list)
            return self._title_for_table(state, primary_name)
        return state.get("title") if state else None

    def _deserialize_state(self, state_data: AppStateDict | None) -> AppState:
        """Reconstruct AppState from a serialized state dict."""
        self._require_initialized("_deserialize_state")
        state = create_app_state(
            data_sources=dict(self._data_sources),
            client_factory=self._client_factory,
            greeting=self.greeting,
            query_executor=self._require_query_executor("_deserialize_state"),
            greeting_client_factory=self._build_greeting_client,
        )
        if state_data:
            state.update_from_dict(state_data)
        return state
