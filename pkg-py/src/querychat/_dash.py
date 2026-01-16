"""Dash-specific QueryChat implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, cast, overload

import narwhals.stable.v1 as nw
from chatlas import Turn
from narwhals.stable.v1.typing import IntoDataFrameT, IntoFrameT, IntoLazyFrameT

from ._dash_ui import IDs, card_ui, chat_container_ui, chat_messages_ui
from ._querychat_base import TOOL_GROUPS, QueryChatBase
from ._querychat_core import (
    GREETING_PROMPT,
    AppState,
    AppStateDict,
    StateDictAccessorMixin,
    create_app_state,
    stream_response_async,
)
from ._ui_assets import DASH_CSS, DASH_JS, SUGGESTION_CSS

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path as PathType

    import chatlas
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame

    import dash
    from dash import html


class QueryChat(QueryChatBase[IntoFrameT], StateDictAccessorMixin[IntoFrameT]):
    """
    QueryChat for Dash applications.

    Provides `.app()` for a complete app, and `.ui()` + `.init_app()`
    for custom layouts with callback wiring. Use `.store_id` to react to
    state changes in your own callbacks.

    Use `.df(state)`, `.sql(state)`, and `.title(state)` to access state
    values in your callbacks.

    Note:
    ----
    LLM calls use async callbacks (Dash 3.1+) which allow other requests to be
    processed while waiting for the LLM response. For production deployments
    with high concurrency, consider using an ASGI server like uvicorn with
    multiple workers.

    Examples:
    --------
    Simple app:
    ```python
    from querychat.dash import QueryChat

    qc = QueryChat(df, "titanic")
    qc.app().run()
    ```

    Custom layout:
    ```python
    from querychat.dash import QueryChat
    from dash import Dash, html, Input, Output

    qc = QueryChat(df, "titanic")
    app = Dash(__name__)

    app.layout = html.Div(
        [
            qc.ui(height="500px"),
            html.Pre(id="sql-display"),
        ]
    )
    qc.init_app(app)


    @app.callback(Output("sql-display", "children"), Input(qc.store_id, "data"))
    def update_sql(state):
        return qc.sql(state) or "SELECT * FROM titanic"


    app.run()
    ```

    """

    @overload
    def __init__(
        self: QueryChat[IntoLazyFrameT],
        data_source: IntoLazyFrameT,
        table_name: str,
        *,
        greeting: Optional[str | PathType] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | PathType] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | PathType] = None,
        prompt_template: Optional[str | PathType] = None,
        storage_type: Literal["memory", "session", "local"] = "memory",
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[IntoDataFrameT],
        data_source: IntoDataFrameT,
        table_name: str,
        *,
        greeting: Optional[str | PathType] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | PathType] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | PathType] = None,
        prompt_template: Optional[str | PathType] = None,
        storage_type: Literal["memory", "session", "local"] = "memory",
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[nw.DataFrame],
        data_source: sqlalchemy.Engine,
        table_name: str,
        *,
        greeting: Optional[str | PathType] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | PathType] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | PathType] = None,
        prompt_template: Optional[str | PathType] = None,
        storage_type: Literal["memory", "session", "local"] = "memory",
    ) -> None: ...

    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine,
        table_name: str,
        *,
        greeting: Optional[str | PathType] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | PathType] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | PathType] = None,
        prompt_template: Optional[str | PathType] = None,
        storage_type: Literal["memory", "session", "local"] = "memory",
    ):
        super().__init__(
            data_source,
            table_name,
            greeting=greeting,
            client=client,
            tools=tools,
            data_description=data_description,
            categorical_threshold=categorical_threshold,
            extra_instructions=extra_instructions,
            prompt_template=prompt_template,
        )
        self._storage_type: Literal["memory", "session", "local"] = storage_type
        self._ids = IDs.from_table_name(self._data_source.table_name)
        self._initialized_apps: set[int] = set()

    @property
    def store_id(self) -> str:
        """
        Get the dcc.Store component ID for callback wiring.

        Use this in @app.callback Input/Output to react to state changes.
        """
        return self._ids.store

    def app(self) -> dash.Dash:
        """
        Create a complete Dash app.

        Returns
        -------
        dash.Dash
            A Dash app ready to run.

        """
        import dash_bootstrap_components as dbc

        import dash

        table_name = self._data_source.table_name

        app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            title=f"querychat with {table_name}",
        )

        self.init_app(app)
        app.layout = app_layout(self._ids, table_name, self.ui())
        register_app_callbacks(
            app,
            self._ids,
            self._data_source.table_name,
            self._deserialize_state,
        )

        return app

    def ui(
        self,
        *,
        height: str = "auto",
        width: str = "min(680px, 100%)",
    ) -> html.Div:
        """
        Create interactive chat UI component for custom layouts.

        Requires calling ``init_app(app)`` to register callbacks.

        Parameters
        ----------
        height
            CSS height value (e.g., "400px", "100%", "auto"). Default is "auto".
        width
            CSS width value (e.g., "300px", "100%", "auto").

        Returns
        -------
        html.Div
            A Div containing the chat UI and state store.

        Example
        -------
        >>> qc = QueryChat(df, "my_table")
        >>> app.layout = html.Div([qc.ui(height="500px"), html.Div(id="output")])
        >>> qc.init_app(app)
        >>>
        >>> @app.callback(Output("output", "children"), Input(qc.store_id, "data"))
        ... def update(state):
        ...     sql = state.get("sql") if state else None
        ...     return f"Current SQL: {sql}"

        """
        from dash import dcc, html

        initial_state = create_app_state(
            self._data_source,
            self._client_factory,
            self.greeting,
        )

        return html.Div(
            [
                dcc.Store(
                    id=self._ids.store,
                    data=cast("dict", initial_state.to_dict()),
                    storage_type=self._storage_type,
                ),
                *chat_container_ui(self._ids),
            ],
            style={"height": height, "width": width},
        )

    def init_app(self, app: dash.Dash) -> None:
        """
        Register callbacks for chat functionality.

        Required after using ui() in a custom layout.

        Parameters
        ----------
        app
            The Dash application to register callbacks on.

        Note
        ----
        This registers callbacks for the chat component only.
        For SQL display and data table functionality, use ``.app()`` instead.

        """
        app_id = id(app)
        if app_id in self._initialized_apps:
            return
        self._initialized_apps.add(app_id)

        register_chat_callbacks(app, self._ids, self._deserialize_state)

        # Inject querychat CSS and JS into the app's index_string
        css = DASH_CSS + "\n" + SUGGESTION_CSS
        css_tag = f"<style>{css}</style>"
        js_tag = f"<script>{DASH_JS}</script>"
        assets = f"{css_tag}\n        {js_tag}"

        app.index_string = app.index_string.replace(
            "{%css%}", f"{{%css%}}\n        {assets}"
        )


def app_layout(ids: IDs, table_name: str, chat_ui):
    """Build the layout for the complete app."""
    import dash_ag_grid as dag
    import dash_bootstrap_components as dbc

    from dash import dcc, html

    # SQL card with dynamic title and reset button
    sql_card = card_ui(
        body=dcc.Markdown(
            id=ids.sql_display,
            className="querychat-sql-display",
        ),
        title_id=ids.sql_title,
        action_button=dbc.Button(
            "Reset Query",
            id=ids.reset_button,
            color="danger",
            size="sm",
            outline=True,
        ),
        class_name="mb-3",
    )

    # Data table card with export button
    data_card = card_ui(
        body=[
            html.Div(
                dag.AgGrid(
                    id=ids.data_table,
                    className="ag-theme-balham",
                    defaultColDef={
                        "filter": True,
                        "sortable": True,
                        "resizable": True,
                        "minWidth": 100,
                    },
                    dashGridOptions={
                        "pagination": True,
                        "paginationPageSize": 20,
                    },
                    columnSize="responsiveSizeToFit",
                    style={"height": "100%", "width": "100%"},
                ),
                className="querychat-data-table-wrapper",
            ),
            html.P(id=ids.data_info, className="mt-2 mb-0 text-muted"),
            dcc.Download(id=ids.download_csv),
        ],
        title="Data view",
        action_button=dbc.Button(
            "Export CSV",
            id=ids.export_button,
            color="secondary",
            size="sm",
            outline=True,
        ),
        class_name="h-100 d-flex flex-column",
        body_class_name="d-flex flex-column",
    )

    chat_card = card_ui(
        body=chat_ui,
        title="Chat",
        class_name="h-100 d-flex flex-column",
        body_class_name="d-flex flex-column p-0 flex-grow-1",
    )

    return dbc.Container(
        [
            html.H1(f"querychat with {table_name}"),
            dbc.Row(
                [
                    dbc.Col(chat_card, width=4),
                    dbc.Col(
                        [sql_card, data_card],
                        width=8,
                        className="d-flex flex-column",
                    ),
                ],
                className="flex-grow-1 g-3",
            ),
        ],
        fluid=True,
        className="vh-100 d-flex flex-column p-3 querychat-app-layout",
    )


def register_app_callbacks(
    app: dash.Dash,
    ids: IDs,
    table_name: str,
    deserialize_state: Callable[[AppStateDict], AppState],
) -> None:
    """Register callbacks for SQL display, data table, and export."""
    from dash.dcc.express import send_data_frame

    import dash
    from dash import Input, Output, State

    @app.callback(
        [
            Output(ids.sql_title, "children"),
            Output(ids.sql_display, "children"),
            Output(ids.data_table, "rowData"),
            Output(ids.data_table, "columnDefs"),
            Output(ids.data_info, "children"),
            Output(ids.store, "data", allow_duplicate=True),
        ],
        [
            Input(ids.store, "data"),
            Input(ids.reset_button, "n_clicks"),
        ],
        prevent_initial_call="initial_duplicate",
    )
    def update_display(state_data: AppStateDict, reset_clicks):
        ctx = dash.callback_context
        trigger_id = ctx.triggered_id

        state = deserialize_state(state_data)

        if trigger_id == ids.reset_button:
            state.reset_dashboard()

        sql_title = state.title or "SQL Query"
        sql_code = f"```sql\n{state.get_display_sql()}\n```"

        df = nw.from_native(state.get_current_data())
        if isinstance(df, nw.LazyFrame):
            df = df.collect()

        display_df = df.to_pandas()
        table_data = display_df.to_dict("records")
        table_columns = [{"field": col} for col in display_df.columns]

        data_info_parts = []
        if state.error:
            data_info_parts.append(f"Warning: {state.error}")
        data_info_parts.append(
            f"Data has {df.shape[0]} rows and {df.shape[1]} columns."
        )
        data_info = " ".join(data_info_parts)

        return (
            sql_title,
            sql_code,
            table_data,
            table_columns,
            data_info,
            state.to_dict(),
        )

    @app.callback(
        Output(ids.download_csv, "data"),
        Input(ids.export_button, "n_clicks"),
        State(ids.store, "data"),
        prevent_initial_call=True,
    )
    def export_csv(n_clicks: int, state_data: AppStateDict):
        state = deserialize_state(state_data)
        df = nw.from_native(state.get_current_data())
        if isinstance(df, nw.LazyFrame):
            df = df.collect()
        return send_data_frame(df.to_pandas().to_csv, "querychat_data.csv", index=False)


def register_chat_callbacks(
    app: dash.Dash,
    ids: IDs,
    deserialize_state: Callable[[AppStateDict], AppState],
) -> None:
    """Register clientside and server-side callbacks for chat functionality."""
    import dash
    from dash import ClientsideFunction, Input, Output, State

    # Show loading indicator when user sends a message
    app.clientside_callback(
        ClientsideFunction("querychat", "show_loading"),
        Output(ids.loading_indicator, "className", allow_duplicate=True),
        [
            Input(ids.send_button, "n_clicks"),
            Input(ids.chat_input, "n_submit"),
        ],
        [State(ids.chat_input, "value")],
        prevent_initial_call=True,
    )

    # Setup suggestion click handler on app load
    app.clientside_callback(
        ClientsideFunction("querychat", "setup_suggestion_handler"),
        Output(ids.chat_history, "data-suggestion-handler", allow_duplicate=True),
        Input(ids.store, "data"),
        prevent_initial_call="initial_duplicate",
    )

    # When chat input is submitted, stream response and update chat history
    @app.callback(
        [
            Output(ids.chat_history, "children"),
            Output(ids.store, "data"),
            Output(ids.chat_input, "value"),
            Output(ids.loading_indicator, "className"),
        ],
        [
            Input(ids.send_button, "n_clicks"),
            Input(ids.chat_input, "n_submit"),
        ],
        [State(ids.chat_input, "value"), State(ids.store, "data")],
        prevent_initial_call=False,
    )
    async def handle_chat(
        send_clicks,
        input_submit,
        message: str | None,
        state_data: AppStateDict,
    ):
        state = deserialize_state(state_data)

        if not state.initialize_greeting_if_preset():
            greeting = ""
            async for chunk in stream_response_async(state.client, GREETING_PROMPT):
                greeting += chunk
            state.set_greeting(greeting)

        ctx = dash.callback_context
        trigger_id = ctx.triggered_id or "init"

        if (
            trigger_id in (ids.send_button, ids.chat_input)
            and message
            and message.strip()
        ):
            try:
                async for _ in stream_response_async(state.client, message):
                    pass
            except Exception as e:
                turns = state.client.get_turns()
                turns.append(
                    Turn(
                        role="assistant",
                        contents=f"Sorry, I encountered an error processing your request: {e}",
                    )
                )
                state.client.set_turns(turns)

        messages = chat_messages_ui(state)
        return messages, state.to_dict(), "", "querychat-loading d-none"

    # Clientside callback: auto-scroll chat history
    app.clientside_callback(
        ClientsideFunction("querychat", "scroll_to_bottom"),
        Output(ids.chat_history, "data-scroll", allow_duplicate=True),
        Input(ids.chat_history, "children"),
        prevent_initial_call=True,
    )
