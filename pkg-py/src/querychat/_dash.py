"""Dash-specific QueryChat implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional, cast, overload

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
from ._utils import as_narwhals

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path as PathType

    import altair as alt
    import chatlas
    import ibis
    import narwhals.stable.v1 as nw
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
        self: QueryChat[Any],
        data_source: None,
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
        self: QueryChat[ibis.Table],
        data_source: ibis.Table,
        table_name: str,
        *,
        greeting: Optional[str | PathType] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
        data_description: Optional[str | PathType] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | PathType] = None,
        prompt_template: Optional[str | PathType] = None,
        storage_type: Literal["memory", "session", "local"] = "memory",
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[IntoLazyFrameT],
        data_source: IntoLazyFrameT,
        table_name: str,
        *,
        greeting: Optional[str | PathType] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
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
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
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
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
        data_description: Optional[str | PathType] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | PathType] = None,
        prompt_template: Optional[str | PathType] = None,
        storage_type: Literal["memory", "session", "local"] = "memory",
    ) -> None: ...

    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine | ibis.Table | None,
        table_name: str,
        *,
        greeting: Optional[str | PathType] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
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
        self._ids = IDs.from_table_name(table_name)
        self._initialized_apps: set[int] = set()

    @property
    def store_id(self) -> str:
        """
        Get the dcc.Store component ID for callback wiring.

        Use this in @app.callback Input/Output to react to state changes.
        """
        return self._ids.store

    def ggvis(
        self, state: AppStateDict, source: Literal["filter", "query"] = "filter"
    ) -> alt.Chart | None:
        """
        Get the current Altair visualization chart.

        Parameters
        ----------
        state
            The state dict from the store component.
        source
            Which visualization to return. "filter" returns the dashboard
            visualization (from visualize_dashboard tool), "query" returns
            the query visualization (from visualize_query tool).

        Returns
        -------
        :
            An Altair Chart object, or None if no visualization exists.

        """
        import ggsql

        if source == "filter":
            spec = state.get("filter_viz_spec")
            if spec is None:
                return None
            # Render against current filtered data
            df = as_narwhals(self.df(state))
            return ggsql.render_altair(df, spec)
        else:
            ggsql_query = state.get("query_viz_ggsql")
            if ggsql_query is None:
                return None
            # Re-execute SQL and render
            sql, viz_spec = ggsql.split_query(ggsql_query)
            df = as_narwhals(self._data_source.execute_query(sql))
            return ggsql.render_altair(df, viz_spec)

    def ggsql(
        self, state: AppStateDict, source: Literal["filter", "query"] = "filter"
    ) -> str | None:
        """
        Get the current ggsql specification.

        Parameters
        ----------
        state
            The state dict from the store component.
        source
            Which specification to return. "filter" returns the VISUALISE spec
            from visualize_dashboard, "query" returns the full ggsql query
            from visualize_query.

        Returns
        -------
        :
            The ggsql specification string, or None if no visualization exists.

        """
        if source == "filter":
            return state.get("filter_viz_spec")
        else:
            return state.get("query_viz_ggsql")

    def ggtitle(
        self, state: AppStateDict, source: Literal["filter", "query"] = "filter"
    ) -> str | None:
        """
        Get the current visualization title.

        Parameters
        ----------
        state
            The state dict from the store component.
        source
            Which title to return. "filter" returns the title from
            visualize_dashboard, "query" returns the title from visualize_query.

        Returns
        -------
        :
            The visualization title, or None if no visualization exists.

        """
        if source == "filter":
            return state.get("filter_viz_title")
        else:
            return state.get("query_viz_title")

    def app(self) -> dash.Dash:
        """
        Create a complete Dash app.

        Returns
        -------
        dash.Dash
            A Dash app ready to run.

        """
        data_source = self._require_data_source("app")
        import dash_bootstrap_components as dbc

        import dash

        table_name = data_source.table_name

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
            data_source.table_name,
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
        data_source = self._require_data_source("ui")
        from dash import dcc, html

        initial_state = create_app_state(
            data_source,
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

    # Filter plot card
    filter_plot_card = card_ui(
        body=[
            html.Iframe(
                id=ids.filter_plot,
                srcDoc="<p>No filter visualization yet. Ask the assistant to create one.</p>",
                style={"width": "100%", "height": "400px", "border": "none"},
            ),
            dcc.Markdown(id=ids.filter_ggsql, className="querychat-ggsql-display mt-2"),
        ],
        title_id=ids.filter_plot_title,
        class_name="h-100",
    )

    # Query plot card
    query_plot_card = card_ui(
        body=[
            html.Iframe(
                id=ids.query_plot,
                srcDoc="<p>No query visualization yet. Ask the assistant to create one.</p>",
                style={"width": "100%", "height": "400px", "border": "none"},
            ),
            dcc.Markdown(id=ids.query_ggsql, className="querychat-ggsql-display mt-2"),
        ],
        title_id=ids.query_plot_title,
        class_name="h-100",
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
                        dbc.Tabs(
                            [
                                dbc.Tab(
                                    [sql_card, data_card],
                                    label="Data",
                                    tab_id="data-tab",
                                ),
                                dbc.Tab(
                                    filter_plot_card,
                                    label="Filter Plot",
                                    tab_id="filter-plot-tab",
                                ),
                                dbc.Tab(
                                    query_plot_card,
                                    label="Query Plot",
                                    tab_id="query-plot-tab",
                                ),
                            ],
                            id=ids.tabs,
                            active_tab="data-tab",
                        ),
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
    """Register callbacks for SQL display, data table, visualizations, and export."""
    import ggsql
    from dash.dcc.express import send_data_frame

    import dash
    from dash import Input, Output, State

    from ._ggsql import vegalite_to_html

    @app.callback(
        [
            Output(ids.sql_title, "children"),
            Output(ids.sql_display, "children"),
            Output(ids.data_table, "rowData"),
            Output(ids.data_table, "columnDefs"),
            Output(ids.data_info, "children"),
            Output(ids.store, "data", allow_duplicate=True),
            Output(ids.filter_plot_title, "children"),
            Output(ids.filter_plot, "srcDoc"),
            Output(ids.filter_ggsql, "children"),
            Output(ids.query_plot_title, "children"),
            Output(ids.query_plot, "srcDoc"),
            Output(ids.query_ggsql, "children"),
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

        current_data = state.get_current_data()
        nw_df = as_narwhals(current_data)
        nrow, ncol = nw_df.shape

        display_df = nw_df.to_pandas()
        table_data = display_df.to_dict("records")
        table_columns = [{"field": col} for col in display_df.columns]

        data_info_parts = []
        if state.error:
            data_info_parts.append(f"Warning: {state.error}")
        data_info_parts.append(f"Data has {nrow} rows and {ncol} columns.")
        data_info = " ".join(data_info_parts)

        # Filter visualization - render on demand
        filter_title = state.filter_viz_title or "Filter Plot"
        filter_spec = state.filter_viz_spec

        if filter_spec:
            # Render against current filtered data
            chart = ggsql.render_altair(nw_df, filter_spec)
            filter_html = vegalite_to_html(chart.to_dict())
        else:
            filter_html = (
                "<p>No filter visualization yet. Ask the assistant to create one.</p>"
            )

        filter_ggsql_md = f"```sql\n{filter_spec}\n```" if filter_spec else ""

        # Query visualization - render on demand
        query_title = state.query_viz_title or "Query Plot"
        query_ggsql_str = state.query_viz_ggsql

        if query_ggsql_str:
            # Re-execute SQL and render
            sql_part, viz_spec = ggsql.split_query(query_ggsql_str)
            query_df = as_narwhals(state.data_source.execute_query(sql_part))
            chart = ggsql.render_altair(query_df, viz_spec)
            query_html = vegalite_to_html(chart.to_dict())
        else:
            query_html = (
                "<p>No query visualization yet. Ask the assistant to create one.</p>"
            )

        query_ggsql_md = f"```sql\n{query_ggsql_str}\n```" if query_ggsql_str else ""

        return (
            sql_title,
            sql_code,
            table_data,
            table_columns,
            data_info,
            state.to_dict(),
            filter_title,
            filter_html,
            filter_ggsql_md,
            query_title,
            query_html,
            query_ggsql_md,
        )

    @app.callback(
        Output(ids.download_csv, "data"),
        Input(ids.export_button, "n_clicks"),
        State(ids.store, "data"),
        prevent_initial_call=True,
    )
    def export_csv(n_clicks: int, state_data: AppStateDict):
        state = deserialize_state(state_data)
        nw_df = as_narwhals(state.get_current_data())
        return send_data_frame(
            nw_df.to_pandas().to_csv, "querychat_data.csv", index=False
        )


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
