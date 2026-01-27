from __future__ import annotations

import copy
import logging
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Union

import chatlas
import shinychat
from narwhals.stable.v1.typing import IntoFrameT

from shiny import module, reactive, ui

from ._querychat_core import GREETING_PROMPT
from .tools import (
    tool_query,
    tool_reset_dashboard,
    tool_update_dashboard,
    tool_visualize_dashboard,
    tool_visualize_query,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import altair as alt
    from shiny.bookmark import BookmarkState, RestoreState

    from shiny import Inputs, Outputs, Session

    from ._datasource import DataSource
    from .tools import UpdateDashboardData, VisualizeDashboardData, VisualizeQueryData

logger = logging.getLogger(__name__)

ReactiveString = reactive.Value[str]
"""A reactive string value."""
ReactiveStringOrNone = reactive.Value[Union[str, None]]
"""A reactive string (or None) value."""

CHAT_ID = "chat"


@module.ui
def mod_ui(**kwargs):
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
        The session-specific chat client instance. This is a deep copy of the
        base client configured for this specific session, containing the chat
        history and tool registrations for this session only.
    filter_viz_spec
        A reactive Value containing the VISUALISE spec from visualize_dashboard.
        Returns `None` if no visualization has been created.
    filter_viz_title
        A reactive Value containing the title from visualize_dashboard.
        Returns `None` if no visualization has been created.
    filter_viz_chart
        A callable returning the rendered Altair chart from visualize_dashboard.
        Returns `None` if no visualization has been created. The chart is
        re-rendered on each call using `ggsql.render_altair()`.
    query_viz_ggsql
        A reactive Value containing the full ggsql query from visualize_query.
        Returns `None` if no visualization has been created.
    query_viz_title
        A reactive Value containing the title from visualize_query.
        Returns `None` if no visualization has been created.
    query_viz_chart
        A callable returning the rendered Altair chart from visualize_query.
        Returns `None` if no visualization has been created. The chart is
        re-rendered on each call using `ggsql.render_altair()`.

    """

    df: Callable[[], IntoFrameT]
    sql: ReactiveStringOrNone
    title: ReactiveStringOrNone
    client: chatlas.Chat
    # Visualization state
    filter_viz_spec: ReactiveStringOrNone
    filter_viz_title: ReactiveStringOrNone
    filter_viz_chart: Callable[[], alt.TopLevelMixin | None]
    query_viz_ggsql: ReactiveStringOrNone
    query_viz_title: ReactiveStringOrNone
    query_viz_chart: Callable[[], alt.TopLevelMixin | None]


@module.server
def mod_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    data_source: DataSource[IntoFrameT] | None,
    greeting: str | None,
    client: chatlas.Chat | Callable,
    enable_bookmarking: bool,
    tools: tuple[str, ...] | None = None,
) -> ServerValues[IntoFrameT]:
    # Reactive values to store state
    sql = ReactiveStringOrNone(None)
    title = ReactiveStringOrNone(None)
    has_greeted = reactive.value[bool](False)  # noqa: FBT003

    # Visualization state - store only specs, render on demand
    filter_viz_spec: reactive.Value[str | None] = reactive.value(None)
    filter_viz_title: reactive.Value[str | None] = reactive.value(None)
    query_viz_ggsql: reactive.Value[str | None] = reactive.value(None)
    query_viz_title: reactive.Value[str | None] = reactive.value(None)

    # Short-circuit for stub sessions (e.g. 1st run of an Express app)
    # data_source may be None during stub session for deferred pattern
    if session.is_stub_session():
        # Mock the error that would otherwise occur in a real session
        def _stub_df():
            raise RuntimeError("RuntimeError: No current reactive context")

        return ServerValues(
            df=_stub_df,
            sql=sql,
            title=title,
            client=client if isinstance(client, chatlas.Chat) else client(),
            filter_viz_spec=filter_viz_spec,
            filter_viz_title=filter_viz_title,
            filter_viz_chart=lambda: filter_viz_chart.get(),
            query_viz_ggsql=query_viz_ggsql,
            query_viz_title=query_viz_title,
            query_viz_chart=lambda: query_viz_chart.get(),
        )

    # Real session requires data_source
    if data_source is None:
        raise RuntimeError(
            "data_source must be set before the real session. "
            "Set it via the data_source property before users connect."
        )

    def update_dashboard(data: UpdateDashboardData):
        sql.set(data["query"])
        title.set(data["title"])

    def reset_dashboard():
        sql.set(None)
        title.set(None)

    def update_filter_viz(data: VisualizeDashboardData):
        filter_viz_spec.set(data["spec"])
        filter_viz_title.set(data["title"])

    def update_query_viz(data: VisualizeQueryData):
        query_viz_ggsql.set(data["ggsql"])
        query_viz_title.set(data["title"])

    # Set up the chat object for this session
    # Support both a callable that creates a client and legacy instance pattern
    if callable(client) and not isinstance(client, chatlas.Chat):
        chat = client(
            update_dashboard=update_dashboard, reset_dashboard=reset_dashboard
        )
    else:
        # Legacy pattern: client is Chat instance
        chat = copy.deepcopy(client)

        chat.register_tool(tool_update_dashboard(data_source, update_dashboard))
        chat.register_tool(tool_query(data_source))
        chat.register_tool(tool_reset_dashboard(reset_dashboard))

        # Register visualization tools if enabled
        if tools and "visualize_dashboard" in tools:
            chat.register_tool(tool_visualize_dashboard(data_source, update_filter_viz))
        if tools and "visualize_query" in tools:
            chat.register_tool(tool_visualize_query(data_source, update_query_viz))

    # Execute query when SQL changes
    @reactive.calc
    def filtered_df():
        query = sql.get()
        df = data_source.get_data() if not query else data_source.execute_query(query)
        return df

    # Render filter visualization on demand
    @reactive.calc
    def render_filter_viz_chart():
        """Render filter visualization using current filtered data."""
        import ggsql

        spec = filter_viz_spec.get()
        if spec is None:
            return None

        current_df = filtered_df()
        return ggsql.render_altair(current_df, spec)

    # Render query visualization on demand
    @reactive.calc
    def render_query_viz_chart():
        """Render query visualization by re-executing the ggsql query."""
        import ggsql

        ggsql_query = query_viz_ggsql.get()
        if ggsql_query is None:
            return None

        sql_part, viz_spec = ggsql.split_query(ggsql_query)
        df = data_source.execute_query(sql_part)
        return ggsql.render_altair(df, viz_spec)

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

        @session.bookmark.on_restore
        def _on_restore(x: RestoreState) -> None:
            vals = x.values
            if "querychat_sql" in vals:
                sql.set(vals["querychat_sql"])
            if "querychat_title" in vals:
                title.set(vals["querychat_title"])
            if "querychat_has_greeted" in vals:
                has_greeted.set(vals["querychat_has_greeted"])

    return ServerValues(
        df=filtered_df,
        sql=sql,
        title=title,
        client=chat,
        filter_viz_spec=filter_viz_spec,
        filter_viz_title=filter_viz_title,
        filter_viz_chart=render_filter_viz_chart,
        query_viz_ggsql=query_viz_ggsql,
        query_viz_title=query_viz_title,
        query_viz_chart=render_query_viz_chart,
    )


class GreetWarning(Warning):
    """Warning raised when no greeting is provided to QueryChat."""
