from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypedDict, Union

import chatlas
import shinychat
from narwhals.stable.v1.typing import IntoFrameT

from shiny import module, reactive, ui

from ._querychat_core import GREETING_PROMPT
from ._viz_altair_widget import AltairWidget
from ._viz_ggsql import execute_ggsql
from ._viz_utils import has_viz_tool, preload_viz_deps_server, preload_viz_deps_ui

if TYPE_CHECKING:
    from collections.abc import Callable

    from shiny.bookmark import BookmarkState, RestoreState

    from shiny import Inputs, Outputs, Session

    from ._datasource import DataSource
    from ._querychat_base import TOOL_GROUPS
    from ._viz_tools import VisualizeQueryData
    from .types import UpdateDashboardData

ReactiveString = reactive.Value[str]
"""A reactive string value."""
ReactiveStringOrNone = reactive.Value[Union[str, None]]
"""A reactive string (or None) value."""


class VizWidgetEntry(TypedDict):
    """A bookmarked visualization widget: enough state to re-register on restore."""

    widget_id: str
    ggsql: str


CHAT_ID = "chat"


class _DeferredStubChatClient:
    """Placeholder chat client for deferred stub sessions."""

    def __getattr__(self, _name: str):
        raise RuntimeError(
            "Chat client is unavailable during stub session before data_source is set."
        )


ServerClient = chatlas.Chat | _DeferredStubChatClient


@module.ui
def mod_ui(*, preload_viz: bool = False, **kwargs):
    css_path = Path(__file__).parent / "static" / "css" / "styles.css"
    js_path = Path(__file__).parent / "static" / "js" / "querychat.js"

    tag = shinychat.chat_ui(CHAT_ID, **kwargs)
    tag.add_class("querychat")

    return ui.TagList(
        ui.head_content(
            ui.include_css(css_path),
            ui.include_js(js_path),
        ),
        tag,
        preload_viz_deps_ui() if preload_viz else None,
    )


@dataclass
class ServerValues(Generic[IntoFrameT]):
    """
    Session-specific reactive values and client returned by QueryChat.server().

    This dataclass contains all the session-specific reactive state for a QueryChat
    instance. Each session gets its own ServerValues to ensure proper isolation
    between concurrent sessions.

    Attributes
    ----------
    df
        A reactive Calc that returns the current filtered data frame or lazy frame.
        If the data source is lazy, returns a LazyFrame. If no SQL query has been
        set, this returns the unfiltered data from the data source.
        Call it like `.df()` to reactively read the current data.
    sql
        A reactive Value containing the current SQL query string. Access the value
        by calling `.sql()`, or set it with `.sql.set("SELECT ...")`.
        Returns `None` if no query has been set.
    title
        A reactive Value containing the current title for the query. The LLM
        provides this title when generating a new SQL query. Access it with
        `.title()`, or set it with `.title.set("...")`. Returns
        `None` if no title has been set.
    client
        Session chat client value.
        For real sessions this is a `chatlas.Chat` created by the client
        factory. For deferred stub sessions (where `data_source` is not set
        yet), this is a placeholder client that raises when accessed.

    """

    df: Callable[[], IntoFrameT]
    sql: ReactiveStringOrNone
    title: ReactiveStringOrNone
    client: ServerClient


@module.server
def mod_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    data_source: DataSource[IntoFrameT] | None,
    greeting: str | None,
    client: Callable[..., chatlas.Chat],
    enable_bookmarking: bool,
    tools: tuple[TOOL_GROUPS, ...] | None = None,
) -> ServerValues[IntoFrameT]:
    # Reactive values to store state
    sql = ReactiveStringOrNone(None)
    title = ReactiveStringOrNone(None)
    has_greeted = reactive.value[bool](False)  # noqa: FBT003

    if not callable(client):
        raise TypeError("mod_server() requires a callable client factory.")

    def update_dashboard(data: UpdateDashboardData):
        sql.set(data["query"])
        title.set(data["title"])

    def reset_dashboard():
        sql.set(None)
        title.set(None)

    viz_widgets: list[VizWidgetEntry] = []

    def on_visualize(data: VisualizeQueryData):
        viz_widgets.append({"widget_id": data["widget_id"], "ggsql": data["ggsql"]})

    def build_chat_client() -> chatlas.Chat:
        return client(
            update_dashboard=update_dashboard,
            reset_dashboard=reset_dashboard,
            visualize_query=on_visualize,
            tools=tools,
        )

    # Short-circuit for stub sessions (e.g. 1st run of an Express app)
    # data_source may be None during stub session for deferred pattern
    if session.is_stub_session():
        # Mock the error that would otherwise occur in a real session
        def _stub_df():
            raise RuntimeError("RuntimeError: No current reactive context")

        stub_client = (
            _DeferredStubChatClient() if data_source is None else build_chat_client()
        )

        return ServerValues(
            df=_stub_df,
            sql=sql,
            title=title,
            client=stub_client,
        )

    # Real session requires data_source
    if data_source is None:
        raise RuntimeError(
            "data_source must be set before the real session. "
            "Set it via the data_source property before users connect."
        )

    # Build the session-specific chat client through QueryChat.client(...).
    chat = build_chat_client()

    if has_viz_tool(tools):
        preload_viz_deps_server()

    # Execute query when SQL changes
    @reactive.calc
    def filtered_df():
        query = sql.get()
        df = data_source.get_data() if not query else data_source.execute_query(query)
        return df

    # Chat UI logic
    chat_ui = shinychat.Chat(CHAT_ID)

    # Handle user input
    @chat_ui.on_user_submit
    async def _(user_input: str):
        stream = await chat.stream_async(user_input, echo="none", content="all")
        await chat_ui.append_message_stream(stream)

    @reactive.effect
    async def greet_on_startup():
        if has_greeted():
            return

        if greeting:
            await chat_ui.append_message(greeting)
        elif greeting is None:
            warnings.warn(
                "No greeting provided to `QueryChat()`. Using the LLM `client` to generate one now. "
                "For faster startup, lower cost, and determinism, consider providing a greeting "
                "to `QueryChat()` and `.generate_greeting()` to generate one beforehand.",
                GreetWarning,
                stacklevel=2,
            )
            stream = await chat.stream_async(GREETING_PROMPT, echo="none")
            await chat_ui.append_message_stream(stream)

        has_greeted.set(True)

    # Handle update button clicks
    @reactive.effect
    @reactive.event(input.chat_update)
    def _():
        update = input.chat_update()
        if update is None:
            return
        if not isinstance(update, dict):
            return

        new_query = update.get("query")
        new_title = update.get("title")
        if new_query is not None:
            sql.set(new_query)
        if new_title is not None:
            title.set(new_title)

    if enable_bookmarking:
        chat_ui.enable_bookmarking(chat)

        @session.bookmark.on_bookmark
        def _on_bookmark(x: BookmarkState) -> None:
            vals = x.values
            vals["querychat_sql"] = sql.get()
            vals["querychat_title"] = title.get()
            vals["querychat_has_greeted"] = has_greeted.get()
            if viz_widgets:
                vals["querychat_viz_widgets"] = viz_widgets

        @session.bookmark.on_restore
        def _on_restore(x: RestoreState) -> None:
            vals = x.values
            if "querychat_sql" in vals:
                sql.set(vals["querychat_sql"])
            if "querychat_title" in vals:
                title.set(vals["querychat_title"])
            if "querychat_has_greeted" in vals:
                has_greeted.set(vals["querychat_has_greeted"])
            if "querychat_viz_widgets" in vals:
                restored = restore_viz_widgets(
                    data_source, vals["querychat_viz_widgets"]
                )
                viz_widgets[:] = restored

    return ServerValues(df=filtered_df, sql=sql, title=title, client=chat)


class GreetWarning(Warning):
    """Warning raised when no greeting is provided to QueryChat."""


def restore_viz_widgets(
    data_source: DataSource[IntoFrameT],
    saved_widgets: list[VizWidgetEntry],
) -> list[VizWidgetEntry]:
    """Re-execute ggsql queries, register widgets, and return restored entries."""
    from ggsql import validate
    from shinywidgets import register_widget

    restored: list[VizWidgetEntry] = []

    for entry in saved_widgets:
        widget_id = entry["widget_id"]
        ggsql_str = entry["ggsql"]
        try:
            validated = validate(ggsql_str)
            spec = execute_ggsql(data_source, ggsql_str, validated)
            altair_widget = AltairWidget.from_ggsql(spec, widget_id=widget_id)
            register_widget(widget_id, altair_widget.widget)
            restored.append(entry)
        except Exception:
            # If a query fails on restore (e.g. data changed), skip it.
            # The placeholder will remain empty but the rest of the chat restores.
            warnings.warn(
                f"Failed to restore visualization widget '{widget_id}' on bookmark restore.",
                stacklevel=2,
            )

    return restored
