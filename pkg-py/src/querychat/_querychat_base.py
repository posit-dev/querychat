"""Core base class shared across all framework-specific QueryChat implementations."""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional

import chatlas
import narwhals.stable.v1 as nw
import sqlalchemy

from ._datasource import (
    DataFrameSource,
    DataSource,
    PolarsLazySource,
    SQLAlchemySource,
)
from ._shiny_module import GREETING_PROMPT
from ._system_prompt import QueryChatSystemPrompt
from ._utils import MISSING, MISSING_TYPE
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


class QueryChatBase:
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
        data_source: IntoFrame | sqlalchemy.Engine,
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
        self._data_source = normalize_data_source(data_source, table_name)

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
            raise ValueError(
                "Table name must begin with a letter and contain only letters, numbers, and underscores",
            )

        self.tools = normalize_tools(tools, default=("update", "query"))
        self.greeting = greeting.read_text() if isinstance(greeting, Path) else greeting

        if prompt_template is None:
            prompt_template = Path(__file__).parent / "prompts" / "prompt.md"

        self._system_prompt = QueryChatSystemPrompt(
            prompt_template=prompt_template,
            data_source=self._data_source,
            data_description=data_description,
            extra_instructions=extra_instructions,
            categorical_threshold=categorical_threshold,
        )

        client = normalize_client(client)
        self._client = copy.deepcopy(client)
        self._client.set_turns([])
        self._client.system_prompt = self._system_prompt.render(self.tools)

        self._client_console = None

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
        tools = normalize_tools(tools, default=self.tools)

        chat = copy.deepcopy(self._client)
        chat.set_turns([])
        chat.system_prompt = self._system_prompt.render(tools)

        if tools is None:
            return chat

        if "update" in tools:
            update_fn = update_dashboard or (lambda _: None)
            reset_fn = reset_dashboard or (lambda: None)
            chat.register_tool(tool_update_dashboard(self._data_source, update_fn))
            chat.register_tool(tool_reset_dashboard(reset_fn))

        if "query" in tools:
            chat.register_tool(tool_query(self._data_source))

        return chat

    def generate_greeting(self, *, echo: Literal["none", "output"] = "none") -> str:
        """Generate a welcome greeting for the chat."""
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
        tools = normalize_tools(tools, default=("query",))

        if new or self._client_console is None:
            self._client_console = self.client(tools=tools, **kwargs)

        self._client_console.console()

    @property
    def system_prompt(self) -> str:
        """Get the system prompt."""
        return self._system_prompt.render(self.tools)

    @property
    def data_source(self) -> DataSource:
        """Get the current data source."""
        return self._data_source

    def cleanup(self) -> None:
        """Clean up resources associated with the data source."""
        self._data_source.cleanup()


def normalize_data_source(
    data_source: IntoFrame | sqlalchemy.Engine | DataSource,
    table_name: str,
) -> DataSource:
    if isinstance(data_source, DataSource):
        return data_source
    if isinstance(data_source, sqlalchemy.Engine):
        return SQLAlchemySource(data_source, table_name)

    # Check for Ibis Table before narwhals conversion (Ibis Tables are not narwhals-native)
    try:
        import ibis

        if isinstance(data_source, ibis.Table):
            from ._datasource import IbisSource

            return IbisSource(data_source, table_name)
    except ImportError:
        pass

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
