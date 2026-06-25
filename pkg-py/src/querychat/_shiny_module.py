from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypedDict, Union

import chatlas
import shinychat
from narwhals.stable.v1.typing import IntoFrameT
from shinychat import Attachment, attachment_to_content

from shiny import module, reactive, ui

from ._querychat_core import GREETING_PROMPT, warn_multi_table_flat_accessor
from ._table_accessor import TableAccessor
from ._viz_altair_widget import AltairWidget
from ._viz_ggsql import execute_ggsql
from ._viz_utils import has_viz_tool, preload_viz_deps_server, preload_viz_deps_ui

if TYPE_CHECKING:
    from collections.abc import Callable

    from shiny.bookmark import BookmarkState, RestoreState

    from shiny import Inputs, Outputs, Session

    from ._datasource import DataSource
    from ._query_executor import QueryExecutor
    from ._querychat_greeter import QueryChatGreeter
    from ._viz_tools import VisualizeData
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


@dataclass
class TableState(Generic[IntoFrameT]):
    """Per-table reactive state."""

    sql: ReactiveStringOrNone
    title: ReactiveStringOrNone
    df: Callable[[], IntoFrameT]


@module.ui
def mod_ui(*, preload_viz: bool = False, greeting: str | None = None, **kwargs):
    css_path = Path(__file__).parent / "static" / "css" / "styles.css"
    js_path = Path(__file__).parent / "static" / "js" / "querychat.js"

    kwargs.setdefault("enable_cancel", True)
    kwargs.setdefault("allow_attachments", True)
    if greeting:
        kwargs.setdefault(
            "greeting", shinychat.chat_greeting(greeting, dismissible=False)
        )
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


class _MultiTableWarnReactive:
    """Proxy that warns once per session and delegates to the primary table's reactive value."""

    def __init__(
        self,
        primary: ReactiveStringOrNone,
        accessor_name: str,
        primary_table: str,
        table_list: str,
    ) -> None:
        self._primary = primary
        self._accessor_name = accessor_name
        self._primary_table = primary_table
        self._table_list = table_list
        self._warned = False

    def _warn(self) -> None:
        if not self._warned:
            self._warned = True
            warn_multi_table_flat_accessor(
                self._accessor_name, self._primary_table, self._table_list, stacklevel=4
            )

    def __call__(self) -> str | None:
        self._warn()
        return self._primary.get()

    def get(self) -> str | None:
        self._warn()
        return self._primary.get()

    def set(self, value: str | None) -> None:
        self._primary.set(value)


class ServerValues(Generic[IntoFrameT]):
    """
    Session-specific reactive values and client returned by QueryChat.server().

    Each session gets its own ServerValues to ensure proper isolation
    between concurrent sessions.

    Attributes
    ----------
    df
        Reactive Calc returning the current filtered data frame.
        With multiple tables, warns and defaults to the primary table; use ``.table('name').df()``.
    sql
        Reactive Value for the current SQL query string.
        With multiple tables, warns and defaults to the primary table; use ``.table('name').sql``.
    title
        Reactive Value for the current title.
        With multiple tables, warns and defaults to the primary table; use ``.table('name').title``.
    tables
        Per-table reactive state dict. Keys are table names.
    client
        Session chat client.
    current_table
        The name of the most recently queried table, or ``None`` if no query
        has been run yet. Call ``.current_table()`` to read reactively.

    """

    def __init__(
        self,
        *,
        df: Callable[[], IntoFrameT],
        sql: ReactiveStringOrNone,
        title: ReactiveStringOrNone,
        tables: dict[str, TableState[IntoFrameT]],
        client: ServerClient,
        data_sources: dict[str, DataSource[IntoFrameT]],
        current_table: ReactiveStringOrNone,
    ):
        self.df = df
        self.sql = sql
        self.title = title
        self._tables = tables
        self.client = client
        self._data_sources = data_sources
        self._current_table_rv = current_table

    def table(self, name: str) -> TableAccessor:
        """
        Get a per-table accessor with reactive state.

        Parameters
        ----------
        name
            Table name.

        Returns
        -------
        TableAccessor
            Accessor with df(), sql(), title() backed by per-session state.

        """
        if name not in self._tables:
            available = ", ".join(f"'{n}'" for n in self._tables)
            raise ValueError(f"Table '{name}' not found. Available: {available}")
        return TableAccessor(name, self._data_sources[name], state=self._tables[name])

    def table_names(self) -> list[str]:
        """Return the names of all registered tables."""
        return list(self._tables.keys())

    def current_table(self) -> str | None:
        """Return the name of the most recently queried table, or None (reactive)."""
        return self._current_table_rv.get()


@module.server
def mod_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    data_sources: dict[str, DataSource[IntoFrameT]] | None,
    executor: QueryExecutor | None,
    greeting: str | None,
    client: Callable[..., chatlas.Chat],
    enable_bookmarking: bool,
    tools: set[str] | None = None,
    greeter: QueryChatGreeter | None = None,
    greeting_base: str | chatlas.Chat | None = None,
) -> ServerValues[IntoFrameT]:
    # Holds a generated greeting so it can be saved and restored on bookmark.
    # Static greetings live in the UI (chat_ui(greeting=)) and persist already.
    # Workaround for posit-dev/shinychat#253: shinychat does not bookmark
    # greetings or expose their state. If that issue is fixed, this value, the
    # get_last_turn() capture below, and the greeting handling in
    # on_bookmark/on_restore can be dropped (and the shinychat minimum bumped).
    current_greeting = ReactiveStringOrNone(None)

    if not callable(client):
        raise TypeError("mod_server() requires a callable client factory.")

    table_states: dict[str, TableState[IntoFrameT]] = {}
    _current_table: ReactiveStringOrNone = ReactiveStringOrNone(None)

    def _make_table_state(
        source: DataSource[IntoFrameT], exec: QueryExecutor
    ) -> TableState[IntoFrameT]:
        table_sql = ReactiveStringOrNone(None)
        table_title = ReactiveStringOrNone(None)

        @reactive.calc
        def filtered_df() -> IntoFrameT:
            query = table_sql.get()
            if query:
                return exec.execute_query(query)
            return source.get_data()

        return TableState(sql=table_sql, title=table_title, df=filtered_df)

    def update_dashboard(data: UpdateDashboardData):
        table_name = data["table"]
        if table_name in table_states:
            table_states[table_name].sql.set(data["query"])
            table_states[table_name].title.set(data["title"])
            _current_table.set(table_name)

    def reset_dashboard(table_name: str):
        if table_name in table_states:
            table_states[table_name].sql.set(None)
            table_states[table_name].title.set(None)
            _current_table.set(table_name)

    viz_widgets: list[VizWidgetEntry] = []

    def on_visualize(data: VisualizeData):
        viz_widgets.append({"widget_id": data["widget_id"], "ggsql": data["ggsql"]})

    def build_chat_client() -> chatlas.Chat:
        return client(
            update_dashboard=update_dashboard,
            reset_dashboard=reset_dashboard,
            visualize=on_visualize,
            tools=tools,
        )

    # Short-circuit for stub sessions (e.g. 1st run of an Express app)
    # data_sources may be None during stub session for deferred pattern
    if session.is_stub_session():
        # Mock the error that would otherwise occur in a real session
        def _stub_df():
            raise RuntimeError("RuntimeError: No current reactive context")

        stub_client = (
            _DeferredStubChatClient() if data_sources is None else build_chat_client()
        )

        return ServerValues(
            df=_stub_df,
            sql=ReactiveStringOrNone(None),
            title=ReactiveStringOrNone(None),
            tables={},
            client=stub_client,
            data_sources=data_sources or {},
            current_table=ReactiveStringOrNone(None),
        )

    # Real session requires data_sources and executor
    if data_sources is None or executor is None:
        raise RuntimeError(
            "At least one table must be registered before the session starts. "
            "Call add_table() before server(), or pass the data to the QueryChat constructor."
        )

    for name, source in data_sources.items():
        table_states[name] = _make_table_state(source, executor)

    # Build the session-specific chat client through QueryChat.client(...).
    chat = build_chat_client()

    if has_viz_tool(tools):
        preload_viz_deps_server()

    # Chat UI logic
    chat_ui = shinychat.Chat(CHAT_ID)
    ctrl = chatlas.StreamController()

    @chat_ui.on_user_submit
    async def _(user_input: str, attachments: list[Attachment]):
        contents = [attachment_to_content(a) for a in attachments]
        stream = await chat.stream_async(
            user_input, *contents, echo="none", content="all", controller=ctrl
        )
        await chat_ui.append_message_stream(stream)

    @reactive.effect
    @reactive.event(input[f"{CHAT_ID}_cancel"])
    def _handle_cancel():
        ctrl.cancel()

    if greeting is None:

        @reactive.effect
        @reactive.event(input[f"{CHAT_ID}_greeting_requested"])
        async def _handle_greeting_requested():
            # Re-display a restored greeting rather than generating a new one.
            # On empty-chat restore both this and on_restore set the greeting
            # (harmless, identical content); on non-empty restore this never
            # fires, so on_restore is the only path that re-displays.
            existing = current_greeting.get()
            if existing is not None:
                await chat_ui.set_greeting(
                    shinychat.chat_greeting(existing, dismissible=False)
                )
                return
            warnings.warn(
                "No greeting provided to `QueryChat()`. Using the LLM `client` to generate one now. "
                "For faster startup, lower cost, and determinism, consider providing a greeting "
                "to `QueryChat()` and `.generate_greeting()` to generate one beforehand.",
                GreetWarning,
                stacklevel=2,
            )
            if greeter is not None:
                await greeter.generate_stream(
                    chat_ui=chat_ui,
                    current_greeting=current_greeting,
                    base=greeting_base,
                )
            else:
                fallback_client = client(tools=None)
                stream = await fallback_client.stream_async(
                    GREETING_PROMPT, echo="none"
                )
                await chat_ui.set_greeting(
                    shinychat.chat_greeting(stream, dismissible=False)
                )
                last_turn = fallback_client.get_last_turn(role="assistant")
                if last_turn is not None:
                    current_greeting.set(last_turn.text)

    # Handle update button clicks
    @reactive.effect
    @reactive.event(input.chat_update)
    def _():
        update = input.chat_update()
        if update is None or not isinstance(update, dict):
            return
        table_name = update.get("table", "")
        new_query = update.get("query") or None  # "" → None (reset)
        new_title = update.get("title") or None
        if table_name and table_name in table_states:
            table_states[table_name].sql.set(new_query)
            table_states[table_name].title.set(new_title)
            _current_table.set(table_name)

    if enable_bookmarking:
        chat_ui.enable_bookmarking(chat)
        session.bookmark.exclude.append("chat_update")

        @session.bookmark.on_bookmark
        def _on_bookmark(x: BookmarkState) -> None:
            vals = x.values
            for name, state in table_states.items():
                vals[f"querychat_sql_{name}"] = state.sql.get()
                vals[f"querychat_title_{name}"] = state.title.get()
            greeting_val = current_greeting.get()
            if greeting_val is not None:
                vals["querychat_greeting"] = greeting_val
            if viz_widgets:
                vals["querychat_viz_widgets"] = viz_widgets

        @session.bookmark.on_restore
        async def _on_restore(x: RestoreState) -> None:
            vals = x.values
            last_restored: str | None = None
            for name, state in table_states.items():
                if f"querychat_sql_{name}" in vals:
                    state.sql.set(vals[f"querychat_sql_{name}"])
                    if vals[f"querychat_sql_{name}"] is not None:
                        last_restored = name
                if f"querychat_title_{name}" in vals:
                    state.title.set(vals[f"querychat_title_{name}"])
            if last_restored is not None:
                _current_table.set(last_restored)
            if "querychat_greeting" in vals:
                current_greeting.set(vals["querychat_greeting"])
                await chat_ui.set_greeting(
                    shinychat.chat_greeting(
                        vals["querychat_greeting"], dismissible=False
                    )
                )
            if "querychat_viz_widgets" in vals:
                restored = restore_viz_widgets(executor, vals["querychat_viz_widgets"])
                viz_widgets[:] = restored

    if len(table_states) == 1:
        only_state = next(iter(table_states.values()))
        return ServerValues(
            df=only_state.df,
            sql=only_state.sql,
            title=only_state.title,
            tables=table_states,
            client=chat,
            data_sources=data_sources,
            current_table=_current_table,
        )

    primary_name = next(iter(table_states))
    primary_state = table_states[primary_name]
    table_list = ", ".join(f"'{n}'" for n in table_states)

    df_warned = False

    @reactive.calc
    def _multi_table_df() -> IntoFrameT:
        nonlocal df_warned
        if not df_warned:
            df_warned = True
            warn_multi_table_flat_accessor("df", primary_name, table_list)
        return primary_state.df()

    return ServerValues(
        df=_multi_table_df,
        sql=_MultiTableWarnReactive(primary_state.sql, "sql", primary_name, table_list),  # type: ignore[arg-type]
        title=_MultiTableWarnReactive(
            primary_state.title, "title", primary_name, table_list
        ),  # type: ignore[arg-type]
        tables=table_states,
        client=chat,
        data_sources=data_sources,
        current_table=_current_table,
    )


class GreetWarning(Warning):
    """Warning raised when no greeting is provided to QueryChat."""


def restore_viz_widgets(
    executor: QueryExecutor,
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
            spec = execute_ggsql(executor, validated)
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
