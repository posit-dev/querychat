"""Core application state and protocols shared across all frameworks."""

from __future__ import annotations

__all__ = [
    "AppState",
    "AppStateDict",
    "ClientFactory",
    "create_app_state",
    "create_app_state_from_dict",
    "stream_response",
    "stream_response_async",
]

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypedDict, Union

from chatlas import Chat, ContentToolRequest, ContentToolResult
from chatlas.types import Content

from ._shiny_module import GREETING_PROMPT
from .tools import UpdateDashboardData

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    import narwhals.stable.v1 as nw

    from ._datasource import DataSource


# -----------------------------------------------------------------------------
# Type definitions
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# Chunk formatting
# -----------------------------------------------------------------------------


def get_tool_result_text(result: ContentToolResult) -> str | None:
    """Extract displayable text from a tool result."""
    display_info = result.extra.get("display") if result.extra else None
    if display_info and hasattr(display_info, "markdown"):
        return display_info.markdown
    return None


def format_chunk(chunk: Union[str, Content]) -> str:
    """Extract displayable text from a chat chunk."""
    if isinstance(chunk, ContentToolRequest):
        return ""
    elif isinstance(chunk, ContentToolResult):
        text = get_tool_result_text(chunk)
        if text:
            return "\n\n" + text + "\n\n"
        else:
            return "\n\n" + str(chunk) + "\n\n"
    elif isinstance(chunk, (str, Content)):
        return str(chunk)
    raise ValueError(f"Unknown chunk type: {type(chunk)}")


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


# -----------------------------------------------------------------------------
# AppState class
# -----------------------------------------------------------------------------


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

    def get_current_data(self) -> nw.DataFrame:
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
        Hides the greeting prompt.
        """
        messages: list[DisplayMessage] = []

        # tool_result_role="assistant" puts tool results in assistant turns
        for turn in self.client.get_turns(tool_result_role="assistant"):
            text_parts = []

            for content in turn.contents:
                if isinstance(content, ContentToolResult):
                    text = get_tool_result_text(content)
                    if text:
                        text_parts.append(text)
                elif isinstance(content, (str, Content)):
                    text_parts.append(str(content))

            if text_parts:
                text = "\n\n".join(text_parts)
                # Skip the greeting prompt - it's an internal message
                if turn.role == "user" and text == GREETING_PROMPT:
                    continue
                messages.append({"role": turn.role, "content": text})

        return messages

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


# -----------------------------------------------------------------------------
# Factory functions
# -----------------------------------------------------------------------------


def create_app_state(
    data_source: DataSource,
    client_factory: ClientFactory,
    greeting: Optional[str] = None,
) -> AppState:
    """Create AppState with callbacks connected via holder pattern."""
    state_holder: dict[str, AppState | None] = {"state": None}

    def update_callback(data: UpdateDashboardData) -> None:
        if state_holder["state"]:
            state_holder["state"].update_dashboard(data)

    def reset_callback() -> None:
        if state_holder["state"]:
            state_holder["state"].reset_dashboard()

    client = client_factory(update_callback, reset_callback)
    state = AppState(
        data_source=data_source,
        client=client,
        greeting=greeting,
    )
    state_holder["state"] = state
    return state


def create_app_state_from_dict(
    state_dict: AppStateDict,
    data_source: DataSource,
    client_factory: ClientFactory,
    greeting: Optional[str] = None,
) -> AppState:
    """
    Create AppState from a serialized AppStateDict.

    This combines create_app_state() with update_from_dict() for
    deserializing state in framework callbacks.
    """
    state = create_app_state(data_source, client_factory, greeting)
    state.update_from_dict(state_dict)
    return state


# -----------------------------------------------------------------------------
# Streaming functions
# -----------------------------------------------------------------------------


def stream_response(client: Chat, prompt: str) -> Iterator[str]:
    """Process a user message and yield text chunks."""
    for chunk in client.stream(prompt, echo="none", content="all"):
        yield format_chunk(chunk)


async def stream_response_async(client: Chat, prompt: str) -> AsyncIterator[str]:
    """Process a user message asynchronously and yield text chunks."""
    stream = await client.stream_async(prompt, echo="none", content="all")
    async for chunk in stream:
        yield format_chunk(chunk)
