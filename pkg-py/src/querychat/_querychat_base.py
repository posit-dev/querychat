"""Core base class shared across all framework-specific QueryChat implementations."""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Literal, Optional

import chatlas
import narwhals.stable.v1 as nw
import sqlalchemy

from ._datasource import (
    DataFrameSource,
    DataSource,
    IbisSource,
    IntoFrameT,
    PolarsLazySource,
    SQLAlchemySource,
)
from ._shiny_module import GREETING_PROMPT
from ._system_prompt import QueryChatSystemPrompt
from ._table_accessor import TableAccessor
from ._utils import MISSING, MISSING_TYPE, is_ibis_table
from .tools import (
    UpdateDashboardData,
    tool_query,
    tool_reset_dashboard,
    tool_update_dashboard,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from narwhals.stable.v1.typing import IntoFrame

TOOL_GROUPS = Literal["update", "query"]


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
        data_source: IntoFrame | sqlalchemy.Engine | None,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ):
        # Store table_name for later normalization
        self._table_name = table_name

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
            raise ValueError(
                "Table name must begin with a letter and contain only letters, numbers, and underscores",
            )

        # Multi-table storage: dict of data sources keyed by table name
        self._data_sources: dict[str, DataSource] = {}

        # Track server initialization state for add/remove table validation
        self._server_initialized = False

        # Store metadata for multi-table support
        self._table_relationships: dict[str, dict[str, str]] = {}
        self._table_descriptions: dict[str, str] = {}

        self.tools = normalize_tools(tools, default=("update", "query"))
        self.greeting = greeting.read_text() if isinstance(greeting, Path) else greeting

        # Store init parameters for deferred system prompt building
        self._prompt_template = prompt_template
        self._data_description = data_description
        self._extra_instructions = extra_instructions
        self._categorical_threshold = categorical_threshold

        # Normalize and initialize client (doesn't need data_source)
        client = normalize_client(client)
        self._client = copy.deepcopy(client)
        self._client.set_turns([])

        self._client_console = None

        # Initialize data source (may be None for deferred pattern)
        if data_source is not None:
            self._data_source: DataSource | None = normalize_data_source(
                data_source, table_name
            )
            self._data_sources[table_name] = self._data_source
            self._build_system_prompt()
        else:
            self._data_source = None
            self._system_prompt = None

    def _build_system_prompt(self) -> None:
        """Build/rebuild the system prompt from current data sources."""
        if not self._data_sources:
            raise RuntimeError("Cannot build system prompt without data_source")

        prompt_template = self._prompt_template
        if prompt_template is None:
            prompt_template = Path(__file__).parent / "prompts" / "prompt.md"

        self._system_prompt = QueryChatSystemPrompt(
            prompt_template=prompt_template,
            data_sources=self._data_sources,
            data_description=self._data_description,
            extra_instructions=self._extra_instructions,
            categorical_threshold=self._categorical_threshold,
            relationships=self._table_relationships,
            table_descriptions=self._table_descriptions,
        )
        self._client.system_prompt = self._system_prompt.render(self.tools)

    def _require_data_source(self, method_name: str) -> DataSource[IntoFrameT]:
        """Raise if data_source is not set, otherwise return it for type narrowing."""
        if self._data_source is None:
            raise RuntimeError(
                f"data_source must be set before calling {method_name}(). "
                "Either pass data_source to __init__(), set the data_source property, "
                "or pass data_source to server()."
            )
        return self._data_source

    def client(
        self,
        *,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None | MISSING_TYPE = MISSING,
        update_dashboard: Callable[[UpdateDashboardData], None] | None = None,
        reset_dashboard: Callable[[], None] | None = None,
    ) -> chatlas.Chat:
        """
        Create a chat client with registered tools.

        Parameters
        ----------
        tools
            Which tools to include: `"update"`, `"query"`, or both.
        update_dashboard
            Callback when update_dashboard tool succeeds.
        reset_dashboard
            Callback when reset_dashboard tool is invoked.

        Returns
        -------
        chatlas.Chat
            A configured chat client.

        """
        data_source = self._require_data_source("client")
        if self._system_prompt is None:
            raise RuntimeError("System prompt not initialized")
        tools = normalize_tools(tools, default=self.tools)

        chat = copy.deepcopy(self._client)
        chat.set_turns([])
        chat.system_prompt = self._system_prompt.render(tools)

        if tools is None:
            return chat

        if "update" in tools:
            update_fn = update_dashboard or (lambda _: None)
            # Wrap user callback to accept table name parameter (for multi-table compat)
            user_reset = reset_dashboard or (lambda: None)

            def reset_fn(_table: str) -> None:
                user_reset()

            chat.register_tool(tool_update_dashboard(self._data_sources, update_fn))
            chat.register_tool(tool_reset_dashboard(reset_fn))

        if "query" in tools:
            chat.register_tool(tool_query(self._data_sources))

        return chat

    def generate_greeting(self, *, echo: Literal["none", "output"] = "none") -> str:
        """Generate a welcome greeting for the chat."""
        self._require_data_source("generate_greeting")
        client = copy.deepcopy(self._client)
        client.set_turns([])
        return str(client.chat(GREETING_PROMPT, echo=echo))

    def console(
        self,
        *,
        new: bool = False,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = "query",
        **kwargs,
    ) -> None:
        """Launch an interactive console chat with the data."""
        self._require_data_source("console")
        tools = normalize_tools(tools, default=("query",))

        if new or self._client_console is None:
            self._client_console = self.client(tools=tools, **kwargs)

        self._client_console.console()

    @property
    def system_prompt(self) -> str:
        """Get the system prompt."""
        self._require_data_source("system_prompt")
        if self._system_prompt is None:
            raise RuntimeError("System prompt not initialized")
        return self._system_prompt.render(self.tools)

    @property
    def data_source(self) -> DataSource | None:
        """
        Get the data source (for single-table backwards compatibility).

        Returns None if no data source is set. Raises ValueError if multiple
        tables are present - use .table("name").data_source instead.
        """
        if not self._data_sources:
            return None
        if len(self._data_sources) == 1:
            return next(iter(self._data_sources.values()))
        raise ValueError(
            f"Multiple tables present ({', '.join(self._data_sources.keys())}). "
            "Use qc.table('name').data_source instead."
        )

    @data_source.setter
    def data_source(self, value: IntoFrame | sqlalchemy.Engine) -> None:
        """Set the data source, normalizing and rebuilding system prompt."""
        self._data_source = normalize_data_source(value, self._table_name)
        self._data_sources[self._table_name] = self._data_source
        self._build_system_prompt()

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
        relationships: dict[str, str] | None = None,
        description: str | None = None,
    ) -> None:
        """
        Add an additional table to the QueryChat instance.

        Parameters
        ----------
        data_source
            The data source (DataFrame, LazyFrame, or database connection).
        table_name
            Name for the table (must be unique within this QueryChat).
        relationships
            Optional dict mapping local columns to "other_table.column" for JOINs.
            Example: {"customer_id": "customers.id"}
        description
            Optional free-text description of the table for the LLM.

        Raises
        ------
        ValueError
            If table_name already exists or is invalid.
        RuntimeError
            If called after server() has been invoked.
        """
        # Check if server already initialized
        if self._server_initialized:
            raise RuntimeError(
                "Cannot add tables after server initialization. "
                "Add all tables before calling .server() or .app()."
            )

        # Validate table name format
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
            raise ValueError(
                "Table name must begin with a letter and contain only "
                "letters, numbers, and underscores"
            )

        # Check for duplicates
        if table_name in self._data_sources:
            raise ValueError(f"Table '{table_name}' already exists")

        # Normalize and store the data source
        normalized = normalize_data_source(data_source, table_name)
        self._data_sources[table_name] = normalized

        # Store relationship and description metadata
        if relationships:
            self._table_relationships[table_name] = relationships
        if description:
            self._table_descriptions[table_name] = description

        # Rebuild system prompt with new table
        self._build_system_prompt()

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

        # Clean up the data source
        self._data_sources[table_name].cleanup()
        del self._data_sources[table_name]

        # Remove associated metadata
        self._table_relationships.pop(table_name, None)
        self._table_descriptions.pop(table_name, None)

        # Rebuild system prompt without removed table
        self._build_system_prompt()

    def cleanup(self) -> None:
        """Clean up resources associated with all data sources."""
        for source in self._data_sources.values():
            source.cleanup()


def normalize_data_source(
    data_source: IntoFrame | sqlalchemy.Engine | DataSource,
    table_name: str,
) -> DataSource:
    if isinstance(data_source, DataSource):
        return data_source
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


def normalize_client(client: str | chatlas.Chat | None) -> chatlas.Chat:
    if client is None:
        client = os.getenv("QUERYCHAT_CLIENT", None)

    if client is None:
        client = "openai"

    if isinstance(client, chatlas.Chat):
        return client

    return chatlas.ChatAuto(provider_model=client)


def normalize_tools(
    tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None | MISSING_TYPE,
    default: tuple[TOOL_GROUPS, ...] | None,
) -> tuple[TOOL_GROUPS, ...] | None:
    if tools is None or tools == ():
        return None
    elif isinstance(tools, MISSING_TYPE):
        return default
    elif isinstance(tools, str):
        return (tools,)
    elif isinstance(tools, tuple):
        return tools
    else:
        return tuple(tools)
