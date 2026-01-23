"""Core application state and protocols shared across all frameworks."""

from __future__ import annotations

__all__ = [
    "GREETING_PROMPT",
    "AppState",
    "AppStateDict",
    "ClientFactory",
    "StateDictAccessorMixin",
    "create_app_state",
    "stream_response",
    "stream_response_async",
]

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Optional, TypedDict, Union

from chatlas import Chat, ContentToolRequest, ContentToolResult
from chatlas.types import Content
from narwhals.stable.v1.typing import IntoFrameT

from .tools import UpdateDashboardData

GREETING_PROMPT: str = (
    "Please give me a friendly greeting. "
    "Include a few sample prompts in a two-level bulleted list."
)
"""Prompt used to generate the initial greeting message."""

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from narwhals.stable.v1.typing import IntoFrame

    from ._datasource import DataSource


ClientFactory = Callable[
    [Callable[[UpdateDashboardData], None], Callable[[], None]],
    Chat,
]
"""Factory that creates a Chat client with update_dashboard and reset_dashboard callbacks."""


class AppStateDict(TypedDict):
    """Serialized AppState for framework state stores."""

    sql: str | None
    title: str | None
    error: str | None
    turns: list[dict]  # Serialized chatlas Turns via model_dump()


class DisplayMessage(TypedDict):
    """A message formatted for UI display."""

    role: str
    content: str


class StateDictAccessorMixin(Generic[IntoFrameT]):
    """Mixin providing df/sql/title accessors for frameworks using serialized state dicts."""

    _data_source: DataSource[IntoFrameT] | None

    def _client_factory(
        self,
        update_cb: Callable[[UpdateDashboardData], None],
        reset_cb: Callable[[], None],
    ) -> Chat:
        """Create a chat client with dashboard callbacks."""
        return self.client(update_dashboard=update_cb, reset_dashboard=reset_cb)  # type: ignore[attr-defined]

    def df(self, state: AppStateDict | None) -> IntoFrameT:
        """
        Get the current DataFrame from state.

        Parameters
        ----------
        state
            The state dictionary from a framework callback.

        Returns
        -------
        :
            The filtered data if a SQL query is active, otherwise the full dataset.
            Returns a LazyFrame if the data source is lazy.

        """
        assert self._data_source is not None
        sql = state.get("sql") if state else None
        if sql:
            try:
                return self._data_source.execute_query(sql)
            except Exception:
                return self._data_source.get_data()
        return self._data_source.get_data()

    def sql(self, state: AppStateDict | None) -> str | None:
        """
        Get the current SQL query from state.

        Parameters
        ----------
        state
            The state dictionary from a framework callback.

        Returns
        -------
        :
            The current SQL query, or None if showing full dataset.

        """
        return state.get("sql") if state else None

    def title(self, state: AppStateDict | None) -> str | None:
        """
        Get the current query title from state.

        Parameters
        ----------
        state
            The state dictionary from a framework callback.

        Returns
        -------
        :
            A short description of the current filter, or None if showing full dataset.

        """
        return state.get("title") if state else None

    def _deserialize_state(self, state_data: AppStateDict | None) -> AppState:
        """Reconstruct AppState from a serialized state dict."""
        assert self._data_source is not None
        state = create_app_state(
            self._data_source,
            self._client_factory,
            self.greeting,  # type: ignore[attr-defined]
        )
        if state_data:
            state.update_from_dict(state_data)
        return state


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
    return str(result)


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

    data_source: DataSource
    client: Chat
    greeting: Optional[str] = None

    sql: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None

    def update_dashboard(self, data: UpdateDashboardData) -> None:
        self.sql = data["query"]
        self.title = data["title"]
        self.error = None  # Clear any previous error on successful update

    def reset_dashboard(self) -> None:
        self.sql = None
        self.title = None
        self.error = None

    def get_current_data(self) -> IntoFrame:
        """Get current data, falling back to default if query fails."""
        if self.sql:
            try:
                result = self.data_source.execute_query(self.sql)
                self.error = None  # Clear error on success
                return result
            except Exception as e:
                self.error = format_query_error(e)
                self.sql = None
                self.title = None
                return self.data_source.get_data()
        self.error = None
        return self.data_source.get_data()

    def get_display_sql(self) -> str:
        return self.sql or f"SELECT * FROM {self.data_source.table_name}"

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
            "sql": self.sql,
            "title": self.title,
            "error": self.error,
            "turns": [turn.model_dump() for turn in self.client.get_turns()],
        }

    def update_from_dict(self, data: AppStateDict) -> None:
        """Restore state from serialized dict."""
        from chatlas import Turn

        self.sql = data["sql"]
        self.title = data["title"]
        self.error = data["error"]

        turns_data = data["turns"]
        turns = [Turn.model_validate(t) for t in turns_data]
        self.client.set_turns(turns)


def create_app_state(
    data_source: DataSource,
    client_factory: ClientFactory,
    greeting: Optional[str] = None,
) -> AppState:
    """Create AppState with callbacks connected via holder pattern."""
    state_holder: dict[str, AppState | None] = {"state": None}

    def update_callback(data: UpdateDashboardData) -> None:
        state = state_holder["state"]
        if state is None:
            raise RuntimeError("Callback invoked before state initialization")
        state.update_dashboard(data)

    def reset_callback() -> None:
        state = state_holder["state"]
        if state is None:
            raise RuntimeError("Callback invoked before state initialization")
        state.reset_dashboard()

    client = client_factory(update_callback, reset_callback)
    state = AppState(
        data_source=data_source,
        client=client,
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
