"""Core application state and protocols shared across all frameworks."""

from __future__ import annotations

__all__ = [
    "GREETING_PROMPT",
    "AppState",
    "AppStateDict",
    "ClientFactory",
    "create_app_state",
    "stream_response",
    "stream_response_async",
]

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypedDict, Union

from chatlas import Chat, ContentToolRequest, ContentToolResult
from chatlas.types import Content
from typing_extensions import NotRequired

from .tools import UpdateDashboardData

GREETING_PROMPT: str = (
    "Please give me a friendly greeting. "
    "Include a few sample suggestions grouped under ##### headings, "
    "using the suggestion card format from your instructions."
)
"""Prompt used to generate the initial greeting message."""

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from narwhals.stable.v1.typing import IntoFrame

    from ._datasource import DataSource
    from ._query_executor import QueryExecutor


ClientFactory = Callable[
    [Callable[[UpdateDashboardData], None], Callable[[str], None]],
    Chat,
]
"""Factory that creates a Chat client with update_dashboard and reset_dashboard callbacks."""


def warn_multi_table_flat_accessor(
    accessor_name: str, primary_table: str, table_list: str, stacklevel: int = 3
) -> None:
    """Emit a FutureWarning when a flat accessor is used with multiple tables registered."""
    warnings.warn(
        f".{accessor_name}() called without a table name, but multiple tables are registered "
        f"({table_list}). Defaulting to primary table '{primary_table}'. "
        f"Use .table('{primary_table}').{accessor_name}() to suppress this warning. "
        f"In a future version of querychat, this will raise an error.",
        FutureWarning,
        stacklevel=stacklevel,
    )


class TableStateData(TypedDict):
    """Per-table state for serialization."""

    sql: str | None
    title: str | None
    error: str | None


class AppStateDict(TypedDict):
    """Serialized AppState for framework state stores."""

    table: NotRequired[str | None]
    sql: str | None
    title: str | None
    error: str | None
    table_states: NotRequired[dict[str, TableStateData]]
    turns: list[dict]  # Serialized chatlas Turns via model_dump()


class DisplayMessage(TypedDict):
    """A message formatted for UI display."""

    role: str
    content: str


def format_chunk(chunk: Union[str, Content]) -> str:
    """Extract displayable text from a chat chunk."""
    if isinstance(chunk, ContentToolRequest):
        # The result contains the SQL display
        return ""
    elif isinstance(chunk, ContentToolResult):
        return "\n\n" + format_tool_result(chunk) + "\n\n"
    elif isinstance(chunk, (str, Content)):
        return str(chunk)
    raise ValueError(f"Unknown chunk type: {type(chunk)}")


def format_tool_result(result: ContentToolResult) -> str:
    """Extract displayable text from a tool result."""
    display_info = result.extra.get("display") if result.extra else None
    if display_info and hasattr(display_info, "markdown"):
        return display_info.markdown
    if result.value is not None:
        return str(result.value)
    return ""




def format_query_error(e: Exception) -> str:
    """Format a query error with helpful guidance."""
    error_msg = str(e).lower()
    error_str = str(e)

    if "column" in error_msg and ("not exist" in error_msg or "unknown" in error_msg):
        return (
            f"Column not found: {error_str}\n\n"
            "Try asking about available columns or rephrase your query."
        )
    elif "syntax" in error_msg:
        return (
            f"Query syntax error: {error_str}\n\n"
            "Try rephrasing your question in simpler terms."
        )
    elif "type" in error_msg or "cast" in error_msg:
        return (
            f"Data type mismatch: {error_str}\n\n"
            "The query may be comparing incompatible values."
        )
    else:
        return (
            f"Query failed: {error_str}\n\n"
            "Try a different question or click Reset to start over."
        )


@dataclass
class AppState:
    """Framework-agnostic application state for a querychat session."""

    data_sources: dict[str, DataSource]
    client: Chat
    query_executor: QueryExecutor | None = None
    greeting: Optional[str] = None

    active_table: str | None = None
    # sql, title, error are per-table properties backed by _table_states

    def __post_init__(self) -> None:
        if self.active_table is None:
            self.active_table = next(iter(self.data_sources))
        self._table_states: dict[str, dict[str, str | None]] = {
            name: {"sql": None, "title": None, "error": None}
            for name in self.data_sources
        }

    def _get_active_state(self) -> dict[str, str | None]:
        table = self.active_table or next(iter(self.data_sources))
        if table not in self._table_states:
            self._table_states[table] = {"sql": None, "title": None, "error": None}
        return self._table_states[table]

    @property
    def sql(self) -> str | None:
        return self._get_active_state()["sql"]

    @sql.setter
    def sql(self, value: str | None) -> None:
        self._get_active_state()["sql"] = value

    @property
    def title(self) -> str | None:
        return self._get_active_state()["title"]

    @title.setter
    def title(self, value: str | None) -> None:
        self._get_active_state()["title"] = value

    @property
    def error(self) -> str | None:
        return self._get_active_state()["error"]

    @error.setter
    def error(self, value: str | None) -> None:
        self._get_active_state()["error"] = value

    def update_dashboard(self, data: UpdateDashboardData) -> None:
        table_name = data["table"]
        self.active_table = table_name
        if table_name not in self._table_states:
            self._table_states[table_name] = {"sql": None, "title": None, "error": None}
        self._table_states[table_name]["sql"] = data["query"]
        self._table_states[table_name]["title"] = data["title"]
        self._table_states[table_name]["error"] = None

    def reset_dashboard(self, table: str | None = None) -> None:
        if table is not None:
            self.active_table = table
        self.sql = None
        self.title = None
        self.error = None

    def get_active_data_source(self) -> DataSource:
        """Return the current full-data source for the active table."""
        if self.active_table is not None and self.active_table in self.data_sources:
            return self.data_sources[self.active_table]
        return next(iter(self.data_sources.values()))

    def get_current_data(self) -> IntoFrame:
        """Get current data, falling back to default if query fails."""
        data_source = self.get_active_data_source()
        if self.sql:
            try:
                query_runner = self.query_executor or data_source
                result = query_runner.execute_query(self.sql)
                self.error = None  # Clear error on success
                return result
            except Exception as e:
                self.error = format_query_error(e)
                self.sql = None
                self.title = None
                return data_source.get_data()
        return data_source.get_data()

    def get_display_sql(self) -> str:
        table_name = self.active_table or next(iter(self.data_sources))
        return self.sql or f"SELECT * FROM {table_name}"

    def get_display_messages(self) -> list[DisplayMessage]:
        """
        Extract displayable messages from chatlas turns.

        Returns list of DisplayMessage dicts for UI rendering.
        Tool results are included in assistant messages.
        Doesn't include the greeting prompt.
        """
        messages: list[DisplayMessage] = []

        # tool_result_role="assistant" puts tool results in assistant turns
        for turn in self.client.get_turns(tool_result_role="assistant"):
            text_parts = [format_chunk(content) for content in turn.contents]

            if text_parts:
                text = "\n\n".join(text_parts)
                # Skip the greeting prompt - it's an internal message
                if turn.role == "user" and text == GREETING_PROMPT:
                    continue
                messages.append({"role": turn.role, "content": text})

        return messages

    def set_greeting(self, greeting: str) -> None:
        """Set the greeting as the initial assistant message."""
        from chatlas import Turn

        self.client.set_turns([Turn(role="assistant", contents=greeting)])

    def initialize_greeting_if_preset(self) -> bool:
        """
        Initialize greeting if preset or already exists.

        Returns True if initialized, False if streaming is needed.
        """
        if self.get_display_messages():
            return True
        if self.greeting:
            self.set_greeting(self.greeting)
            return True
        return False

    def to_dict(self) -> AppStateDict:
        """Serialize state to dict for framework state stores."""
        return {
            "table": self.active_table,
            "sql": self.sql,
            "title": self.title,
            "error": self.error,
            "table_states": {
                name: {"sql": ts["sql"], "title": ts["title"], "error": ts["error"]}
                for name, ts in self._table_states.items()
            },
            "turns": [turn.model_dump() for turn in self.client.get_turns()],
        }

    def update_from_dict(self, data: AppStateDict) -> None:
        """Restore state from serialized dict."""
        from chatlas import Turn

        self.active_table = data.get("table", next(iter(self.data_sources)))

        per_table = data.get("table_states")
        if per_table:
            for name, ts in per_table.items():
                if name in self._table_states:
                    self._table_states[name]["sql"] = ts.get("sql")
                    self._table_states[name]["title"] = ts.get("title")
                    self._table_states[name]["error"] = ts.get("error")
        else:
            # Backward compat: restore single active-table state from flat fields.
            active = self.active_table or next(iter(self.data_sources))
            if active in self._table_states:
                self._table_states[active]["sql"] = data["sql"]
                self._table_states[active]["title"] = data["title"]
                self._table_states[active]["error"] = data["error"]

        turns_data = data["turns"]
        turns = [Turn.model_validate(t) for t in turns_data]
        self.client.set_turns(turns)


def create_app_state(
    *,
    data_sources: dict[str, DataSource],
    client_factory: ClientFactory,
    greeting: Optional[str] = None,
    query_executor: QueryExecutor | None = None,
) -> AppState:
    """Create AppState with callbacks connected via holder pattern."""
    state_holder: dict[str, AppState | None] = {"state": None}

    def update_callback(data: UpdateDashboardData) -> None:
        state = state_holder["state"]
        if state is None:
            raise RuntimeError("Callback invoked before state initialization")
        state.update_dashboard(data)

    def reset_callback(_table: str) -> None:
        state = state_holder["state"]
        if state is None:
            raise RuntimeError("Callback invoked before state initialization")
        state.reset_dashboard(_table)

    client = client_factory(update_callback, reset_callback)
    state = AppState(
        data_sources=dict(data_sources),
        client=client,
        query_executor=query_executor,
        greeting=greeting,
    )
    state_holder["state"] = state
    return state


def stream_response(client: Chat, prompt: str) -> Iterator[str]:
    """Process a user message and yield text chunks."""
    for chunk in client.stream(prompt, echo="none", content="all"):
        yield format_chunk(chunk)


async def stream_response_async(client: Chat, prompt: str) -> AsyncIterator[str]:
    """Process a user message asynchronously and yield text chunks."""
    stream = await client.stream_async(prompt, echo="none", content="all")
    async for chunk in stream:
        yield format_chunk(chunk)
