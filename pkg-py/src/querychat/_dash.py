"""Dash-specific QueryChat implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, Optional, cast

from chatlas import Turn

from ._querychat_base import TOOL_GROUPS, QueryChatBase
from ._shiny_module import GREETING_PROMPT
from ._querychat_core import (
    AppState,
    AppStateDict,
    create_app_state,
    create_app_state_from_dict,
    stream_response_async,
)
from ._ui_assets import DASH_CSS, SUGGESTION_CSS

if TYPE_CHECKING:
    from pathlib import Path as PathType

    import chatlas
    import narwhals.stable.v1 as nw
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame

    import dash
    from dash import html

DEFAULT_MAX_DISPLAY_ROWS = 100

# Combined CSS for all Dash querychat components
_QUERYCHAT_CSS = DASH_CSS + "\n" + SUGGESTION_CSS


class QueryChat(QueryChatBase):
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
        max_display_rows: int = DEFAULT_MAX_DISPLAY_ROWS,
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
        self._max_display_rows = max_display_rows
        self._storage_type: Literal["memory", "session", "local"] = storage_type
        self._id_prefix = f"querychat-{self._data_source.table_name}"
        self._store_id = self._id("store")

    def _id(self, suffix: str) -> str:
        """Generate a unique element ID with the table name prefix."""
        return f"{self._id_prefix}-{suffix}"

    def _client_factory(self, update_cb, reset_cb):
        """Create a chat client with dashboard callbacks."""
        return self.client(update_dashboard=update_cb, reset_dashboard=reset_cb)

    def _chat_ui_content(self):
        """Create the inner chat UI content (history, input, button, spinner)."""
        import dash_bootstrap_components as dbc

        from dash import html

        return [
            html.Div(
                id=self._id("chat-history"),
                className="querychat-chat-history",
            ),
            dbc.InputGroup(
                [
                    dbc.Input(
                        id=self._id("chat-input"),
                        placeholder="Ask a question about your data...",
                        type="text",
                    ),
                    dbc.Button(
                        "Send",
                        id=self._id("send-button"),
                        color="primary",
                    ),
                ]
            ),
            html.Div(
                dbc.Spinner(
                    size="sm",
                    color="primary",
                    spinner_class_name="ms-2",
                ),
                id=self._id("loading-indicator"),
                className="querychat-loading d-none",
            ),
        ]

    def _chat_card(self):
        """Create the chat Card component for .app() layout."""
        import dash_bootstrap_components as dbc

        from dash import html

        return dbc.Card(
            [
                dbc.CardHeader(html.H4("Chat", className="mb-0")),
                dbc.CardBody(
                    self._chat_ui_content(),
                    className="d-flex flex-column",
                ),
            ],
            className="h-100",
        )

    def _create_store(self):
        """Create the dcc.Store component with initial state."""
        from dash import dcc

        initial_state = create_app_state(
            self._data_source, self._client_factory, self.greeting
        )

        return dcc.Store(
            id=self._store_id,
            data=cast("dict", initial_state.to_dict()),
            storage_type=self._storage_type,
        )

    @property
    def store_id(self) -> str:
        """
        Get the dcc.Store component ID for callback wiring.

        Use this in @app.callback Input/Output to react to state changes.
        """
        return self._store_id

    def df(self, state: AppStateDict | None) -> nw.DataFrame:
        """
        Get the current filtered DataFrame from state.

        Parameters
        ----------
        state
            The state dictionary from a Dash callback (from ``dcc.Store``).

        Returns
        -------
        nw.DataFrame
            The filtered data if a SQL query is active, otherwise the full dataset.

        Examples
        --------
        >>> @app.callback(Output("data-table", "data"), Input(qc.store_id, "data"))
        ... def update_table(state):
        ...     df = qc.df(state)
        ...     return df.to_pandas().to_dict("records")

        """
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
            The state dictionary from a Dash callback (from ``dcc.Store``).

        Returns
        -------
        str | None
            The current SQL query, or None if showing full dataset.

        """
        return state.get("sql") if state else None

    def title(self, state: AppStateDict | None) -> str | None:
        """
        Get the current query title from state.

        Parameters
        ----------
        state
            The state dictionary from a Dash callback (from ``dcc.Store``).

        Returns
        -------
        str | None
            A short description of the current filter, or None if showing full dataset.

        """
        return state.get("title") if state else None

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
        from dash import dash_table, dcc, html

        app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            title=f"querychat with {self._data_source.table_name}",
        )

        app.layout = dbc.Container(
            [
                self._create_store(),
                html.H1(f"querychat with {self._data_source.table_name}"),
                dbc.Row(
                    [
                        dbc.Col(self._chat_card(), width=4),
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        html.H4(
                                                            id=self._id("sql-title"),
                                                            className="mb-0",
                                                        )
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            "Reset Query",
                                                            id=self._id("reset-button"),
                                                            color="danger",
                                                            size="sm",
                                                            outline=True,
                                                        ),
                                                        width="auto",
                                                    ),
                                                ],
                                                align="center",
                                            )
                                        ),
                                        dbc.CardBody(
                                            dcc.Markdown(
                                                id=self._id("sql-display"),
                                                className="querychat-sql-display",
                                            )
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        html.H4(
                                                            "Data view",
                                                            className="mb-0",
                                                        )
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            "Export CSV",
                                                            id=self._id(
                                                                "export-button"
                                                            ),
                                                            color="secondary",
                                                            size="sm",
                                                            outline=True,
                                                        ),
                                                        width="auto",
                                                    ),
                                                ],
                                                align="center",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [
                                                html.Div(
                                                    dash_table.DataTable(
                                                        id=self._id("data-table"),
                                                        style_table={
                                                            "overflowX": "auto",
                                                            "overflowY": "auto",
                                                        },
                                                        style_cell={
                                                            "textAlign": "left",
                                                            "padding": "8px",
                                                        },
                                                        style_header={
                                                            "fontWeight": "bold",
                                                            "backgroundColor": "#f8f9fa",
                                                        },
                                                        filter_action="native",
                                                        sort_action="native",
                                                        page_size=20,
                                                    ),
                                                    className="querychat-data-table-wrapper",
                                                ),
                                                html.P(
                                                    id=self._id("data-info"),
                                                    className="mt-2 mb-0 text-muted",
                                                ),
                                            ],
                                            className="d-flex flex-column",
                                        ),
                                        dcc.Download(id=self._id("download-csv")),
                                    ],
                                    className="h-100 d-flex flex-column",
                                ),
                            ],
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

        self.init_app(app)
        self._register_display_callbacks(app)

        return app

    def _register_display_callbacks(self, app: dash.Dash) -> None:
        """Register callbacks for SQL display, data table, and export."""
        from dash.dcc.express import send_data_frame

        import dash
        from dash import Input, Output, State

        reset_button_id = self._id("reset-button")
        sql_title_id = self._id("sql-title")
        sql_display_id = self._id("sql-display")
        data_table_id = self._id("data-table")
        data_info_id = self._id("data-info")
        export_button_id = self._id("export-button")
        download_id = self._id("download-csv")

        @app.callback(
            [
                Output(sql_title_id, "children"),
                Output(sql_display_id, "children"),
                Output(data_table_id, "data"),
                Output(data_table_id, "columns"),
                Output(data_info_id, "children"),
                Output(self._store_id, "data", allow_duplicate=True),
            ],
            [
                Input(self._store_id, "data"),
                Input(reset_button_id, "n_clicks"),
            ],
            prevent_initial_call="initial_duplicate",
        )
        def update_display(state_data: AppStateDict, reset_clicks):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            state = create_app_state_from_dict(
                state_data or {},
                self._data_source,
                self._client_factory,
                self.greeting,
            )

            if trigger_id == reset_button_id:
                state.reset_dashboard()

            sql_title = state.title or "SQL Query"
            sql_code = f"```sql\n{state.get_display_sql()}\n```"

            df = state.get_current_data()
            display_df = df.head(self._max_display_rows).to_pandas()
            table_data = display_df.to_dict("records")
            table_columns = [{"name": col, "id": col} for col in display_df.columns]

            data_info_parts = []
            if state.error:
                data_info_parts.append(f"Warning: {state.error}")
            data_info_parts.append(
                f"Data has {df.shape[0]} rows and {df.shape[1]} columns."
            )
            if len(df) > self._max_display_rows:
                data_info_parts.append(f"(showing first {self._max_display_rows} rows)")
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
            Output(download_id, "data"),
            Input(export_button_id, "n_clicks"),
            State(self._store_id, "data"),
            prevent_initial_call=True,
        )
        def export_csv(n_clicks: int, state_data: AppStateDict):
            state = create_app_state_from_dict(
                state_data or {},
                self._data_source,
                self._client_factory,
                self.greeting,
            )
            df = state.get_current_data().to_pandas()
            return send_data_frame(df.to_csv, "querychat_data.csv", index=False)

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
        from dash import html

        # Build style only if non-auto values provided
        style = {}
        if height != "auto":
            style["height"] = height
        if width != "auto":
            style["width"] = width

        return html.Div(
            [
                self._create_store(),
                *self._chat_ui_content(),
            ],
            style=style if style else None,
        )

    @staticmethod
    def _render_chat_history(state: AppState) -> list:
        """Render chat history as Dash components."""
        from dash import dcc, html

        chat_elements = []
        for msg in state.get_display_messages():
            role_class = (
                "querychat-message-user"
                if msg["role"] == "user"
                else "querychat-message-assistant"
            )
            class_name = f"querychat-message {role_class}"

            display_content = msg["content"]
            if msg["role"] == "assistant":
                display_content = _convert_suggestion_spans(msg["content"])

            content_element = dcc.Markdown(display_content, dangerously_allow_html=True)

            chat_elements.append(
                html.Div(
                    [
                        html.Strong(msg["role"].title() + ": "),
                        content_element,
                    ],
                    className=class_name,
                )
            )
        return chat_elements

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
        self._inject_css(app)
        self._register_chat_callbacks(app)

    @staticmethod
    def _inject_css(app: dash.Dash) -> None:
        """Inject querychat CSS into the app's index_string."""
        css_tag = f"<style>{_QUERYCHAT_CSS}</style>"

        if css_tag not in app.index_string:
            # Insert CSS after {%css%} placeholder
            app.index_string = app.index_string.replace(
                "{%css%}", f"{{%css%}}\n        {css_tag}"
            )

    def _register_chat_callbacks(self, app: dash.Dash) -> None:
        """Register clientside and server-side callbacks for chat functionality."""
        import dash
        from dash import Input, Output, State

        chat_history_id = self._id("chat-history")
        chat_input_id = self._id("chat-input")
        send_button_id = self._id("send-button")
        loading_id = self._id("loading-indicator")

        # Clientside callback: show loading indicator when user sends a message
        app.clientside_callback(
            """
            function(n_clicks, n_submit, message) {
                if (message && message.trim()) {
                    return 'querychat-loading';
                }
                return window.dash_clientside.no_update;
            }
            """,
            Output(loading_id, "className", allow_duplicate=True),
            [
                Input(send_button_id, "n_clicks"),
                Input(chat_input_id, "n_submit"),
            ],
            [State(chat_input_id, "value")],
            prevent_initial_call=True,
        )

        # Clientside callback: set up suggestion click handler on app load
        app.clientside_callback(
            """
            function(data) {
                if (!window._querychatSuggestionHandlerRegistered) {
                    window._querychatSuggestionHandlerRegistered = true;
                    document.addEventListener('click', function(e) {
                        var suggestion = e.target.closest('.suggestion');
                        if (suggestion) {
                            e.preventDefault();
                            var suggestionText = suggestion.textContent.trim();
                            var card = suggestion.closest('.card');
                            var chatInput = card ? card.querySelector('input[type="text"]') : null;
                            if (chatInput && window.dash_clientside && window.dash_clientside.set_props) {
                                window.dash_clientside.set_props(chatInput.id, {value: suggestionText});
                                chatInput.focus();
                            }
                        }
                    });
                }
                return window.dash_clientside.no_update;
            }
            """,
            Output(chat_history_id, "data-suggestion-handler", allow_duplicate=True),
            Input(self._store_id, "data"),
            prevent_initial_call="initial_duplicate",
        )

        # Server-side callback: handle chat messages
        @app.callback(
            [
                Output(chat_history_id, "children"),
                Output(self._store_id, "data"),
                Output(chat_input_id, "value"),
                Output(loading_id, "className"),
            ],
            [
                Input(send_button_id, "n_clicks"),
                Input(chat_input_id, "n_submit"),
            ],
            [State(chat_input_id, "value"), State(self._store_id, "data")],
            prevent_initial_call=False,
        )
        async def handle_chat(
            send_clicks,
            input_submit,
            message,
            state_data: AppStateDict,
        ):
            ctx = dash.callback_context
            state = create_app_state_from_dict(
                state_data or {},
                self._data_source,
                self._client_factory,
                self.greeting,
            )

            trigger_id = ctx.triggered_id or "init"

            if not state.get_display_messages():
                the_greeting = state.greeting
                if not the_greeting:
                    the_greeting = ""
                    async for chunk in stream_response_async(
                        state.client, GREETING_PROMPT
                    ):
                        the_greeting += chunk
                state.client.set_turns([Turn(role="assistant", contents=the_greeting)])

            if (
                trigger_id in (send_button_id, chat_input_id)
                and message
                and message.strip()
            ):
                try:
                    async for _chunk in stream_response_async(
                        state.client, message
                    ):
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

            chat_elements = self._render_chat_history(state)
            return chat_elements, state.to_dict(), "", "querychat-loading d-none"

        # Clientside callback: auto-scroll chat history
        app.clientside_callback(
            """
            function(children) {
                var chatHistories = document.querySelectorAll('.querychat-chat-history');
                chatHistories.forEach(function(chatHistory) {
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                });
                return window.dash_clientside.no_update;
            }
            """,
            Output(chat_history_id, "data-scroll", allow_duplicate=True),
            Input(chat_history_id, "children"),
            prevent_initial_call=True,
        )


def _convert_suggestion_spans(content: str) -> str:
    """
    Convert <span class="suggestion"> to styled <p> tags for dcc.Markdown compatibility.

    dcc.Markdown with dangerously_allow_html=True preserves attributes on block-level
    elements (div, p) but strips them from inline elements (span).
    """
    style = "color: #0066cc; cursor: pointer; text-decoration: underline; display: inline; margin: 0;"
    content = re.sub(
        r'<span\s+class="suggestion"\s*>',
        f'<p class="suggestion" style="{style}">',
        content,
    )
    content = re.sub(r"</span>", "</p>", content)
    return content
