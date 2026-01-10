"""Gradio-specific QueryChat implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from chatlas import Turn

from ._querychat_base import TOOL_GROUPS, QueryChatBase
from ._shiny_module import GREETING_PROMPT
from ._querychat_core import (
    AppState,
    AppStateDict,
    create_app_state,
    create_app_state_from_dict,
    stream_response,
)
from ._ui_assets import GRADIO_CSS, GRADIO_SUGGESTION_JS, SUGGESTION_CSS

DEFAULT_MAX_DISPLAY_ROWS = 100

if TYPE_CHECKING:
    from pathlib import Path

    import chatlas
    import narwhals.stable.v1 as nw
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame

    import gradio as gr


class QueryChat(QueryChatBase):
    """
    QueryChat for Gradio applications.

    Provides `.app()` for a complete app, and `.ui()` which returns
    `(components, state)` for custom layouts with explicit event wiring.

    Use `.df(state)`, `.sql(state)`, and `.title(state)` to access state
    values in your callbacks.

    Examples
    --------
    Simple app:
    ```python
    from querychat.gradio import QueryChat

    qc = QueryChat(df, "titanic")
    qc.app().launch()
    ```

    Custom layout:
    ```python
    from querychat.gradio import QueryChat
    import gradio as gr

    qc = QueryChat(df, "titanic")

    with gr.Blocks() as app:
        with gr.Row():
            chat_ui, state = qc.ui()

            with gr.Column():
                data_table = gr.Dataframe()
                sql_display = gr.Code(language="sql")

        def update_outputs(state_dict):
            df = qc.df(state_dict)
            sql = qc.sql(state_dict)
            return df.to_native(), sql or ""

        state.change(
            fn=update_outputs,
            inputs=[state],
            outputs=[data_table, sql_display],
        )

    app.launch()
    ```

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
        max_display_rows: int = DEFAULT_MAX_DISPLAY_ROWS,
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

    @property
    def css(self) -> str:
        """
        CSS styles for querychat components.

        Use this when building custom layouts with `.ui()` to enable
        suggestion click styling. Pass to `.launch(css=qc.css)`.
        """
        return SUGGESTION_CSS

    @property
    def head(self) -> str:
        """
        JavaScript for querychat functionality.

        Use this when building custom layouts with `.ui()` to enable
        suggestion click handling. Pass to `.launch(head=qc.head)`.
        """
        return f"<script>{GRADIO_SUGGESTION_JS}</script>"

    def launch(self, app: gr.Blocks, **kwargs):
        """
        Launch a Gradio app with querychat CSS/JS automatically injected.

        This is a convenience method that wraps ``app.launch()`` and
        automatically passes the required ``.css`` and ``.head`` properties.

        Parameters
        ----------
        app
            The Gradio Blocks app to launch.
        **kwargs
            Additional arguments passed to ``app.launch()``.

        Returns
        -------
        The result of ``app.launch()``.

        Examples
        --------
        >>> qc = QueryChat(df, "my_table")
        >>> with gr.Blocks() as app:
        ...     chat_ui, state = qc.ui()
        ...     # ... custom layout ...
        >>> qc.launch(app)  # Instead of app.launch(css=qc.css, head=qc.head)

        """
        user_css = kwargs.pop("css", None)
        user_head = kwargs.pop("head", None)

        final_css = self.css
        if user_css:
            final_css = f"{self.css}\n{user_css}"

        final_head = self.head
        if user_head:
            final_head = f"{self.head}\n{user_head}"

        return app.launch(css=final_css, head=final_head, **kwargs)

    def app(self) -> GradioBlocksWrapper:
        """
        Create a complete Gradio app.

        Returns
        -------
        _GradioBlocksWrapper
            A wrapped Gradio Blocks app ready to launch. The wrapper injects
            querychat CSS/JS at launch time for Gradio 6.0+ compatibility.

        """
        from gradio.themes import Soft

        import gradio as gr

        def client_factory(update_cb, reset_cb):
            return self.client(update_dashboard=update_cb, reset_dashboard=reset_cb)

        def deserialize_state(state_dict: AppStateDict):
            return create_app_state_from_dict(
                state_dict, self._data_source, client_factory, self.greeting
            )

        initial_state = create_app_state(
            self._data_source, client_factory, self.greeting
        )

        with gr.Blocks(
            title=f"querychat with {self._data_source.table_name}",
        ) as blocks_app:
            state_holder = gr.State(value=initial_state.to_dict())

            with gr.Sidebar(label="Chat", open=True, width=420):
                chatbot = gr.Chatbot(
                    label="Chat",
                    layout="bubble",
                    buttons=["copy", "copy_all"],
                    elem_classes="querychat-chatbot",
                )
                with gr.Row(elem_classes="querychat-chat-input"):
                    msg_input = gr.Textbox(
                        placeholder="Ask a question about your data...",
                        scale=4,
                        show_label=False,
                        container=False,
                    )
                    send_btn = gr.Button(
                        "Send", scale=1, variant="primary", min_width=80
                    )

            gr.Markdown(f"## `{self._data_source.table_name}`")

            with gr.Group():
                with gr.Row():
                    sql_title = gr.Markdown("**Current Query**")
                    reset_btn = gr.Button(
                        "Reset", size="sm", variant="secondary", scale=0
                    )
                sql_display = gr.Code(
                    label="",
                    language="sql",
                    value=f"SELECT * FROM {self._data_source.table_name}",
                    interactive=False,
                    lines=2,
                )

            with gr.Group():
                gr.Markdown("**Data Preview**")
                data_display = gr.Dataframe(
                    label="",
                    buttons=["fullscreen", "copy"],
                    show_search="filter",
                )
                data_info = gr.Markdown("")

            def initialize_greeting(state_dict: AppStateDict):
                state = deserialize_state(state_dict)

                if not state.get_display_messages():
                    the_greeting = state.greeting
                    if not the_greeting:
                        the_greeting = ""
                        for chunk in stream_response(state.client, GREETING_PROMPT):
                            the_greeting += chunk

                    state.client.set_turns(
                        [Turn(role="assistant", contents=the_greeting)]
                    )

                ui_values = state_to_ui(state, self._max_display_rows)
                return (*ui_values, state.to_dict())

            def submit_message(message: str, state_dict: AppStateDict):
                state = deserialize_state(state_dict)

                if not message.strip():
                    yield (
                        *state_to_ui(state, self._max_display_rows),
                        "",
                        state.to_dict(),
                    )
                    return

                # Get chat messages for streaming display
                chat_messages = state.get_display_messages()

                # Get current UI values for non-streaming outputs
                sql_title_text = f"### {state.title or 'SQL Query'}"
                sql_code = state.get_display_sql()
                df = state.get_current_data()
                data_info_parts = []
                if state.error:
                    data_info_parts.append(f"⚠️ {state.error}")
                data_info_parts.append(
                    f"*Data has {df.shape[0]} rows and {df.shape[1]} columns.*"
                )
                if len(df) > self._max_display_rows:
                    data_info_parts.append(
                        f"(showing first {self._max_display_rows} rows)"
                    )
                data_info_text = " ".join(data_info_parts)
                display_df = df.head(self._max_display_rows).to_native()

                response = ""
                for chunk in stream_response(state.client, message):
                    response += chunk
                    streaming_messages = [
                        *chat_messages,
                        {"role": "assistant", "content": response},
                    ]
                    yield (
                        streaming_messages,
                        sql_title_text,
                        sql_code,
                        display_df,
                        data_info_text,
                        "",
                        state_dict,
                    )

                yield (
                    *state_to_ui(state, self._max_display_rows),
                    "",
                    state.to_dict(),
                )

            def reset_query(state_dict: AppStateDict):
                state = deserialize_state(state_dict)
                state.reset_dashboard()
                ui_values = state_to_ui(state, self._max_display_rows)
                return (*ui_values, state.to_dict())

            blocks_app.load(
                fn=initialize_greeting,
                inputs=[state_holder],
                outputs=[
                    chatbot,
                    sql_title,
                    sql_display,
                    data_display,
                    data_info,
                    state_holder,
                ],
            )

            send_btn.click(
                fn=submit_message,
                inputs=[msg_input, state_holder],
                outputs=[
                    chatbot,
                    sql_title,
                    sql_display,
                    data_display,
                    data_info,
                    msg_input,
                    state_holder,
                ],
            )

            msg_input.submit(
                fn=submit_message,
                inputs=[msg_input, state_holder],
                outputs=[
                    chatbot,
                    sql_title,
                    sql_display,
                    data_display,
                    data_info,
                    msg_input,
                    state_holder,
                ],
            )

            reset_btn.click(
                fn=reset_query,
                inputs=[state_holder],
                outputs=[
                    chatbot,
                    sql_title,
                    sql_display,
                    data_display,
                    data_info,
                    state_holder,
                ],
            )

        # Wrap the Blocks to inject CSS/JS/theme at launch() time (Gradio 6.0+)
        combined_css = f"{SUGGESTION_CSS}\n{GRADIO_CSS}"
        return GradioBlocksWrapper(
            blocks_app,
            combined_css,
            f"<script>{GRADIO_SUGGESTION_JS}</script>",
            theme=Soft(),
        )

    def df(self, state: AppStateDict | None) -> nw.DataFrame:
        """
        Get the current filtered DataFrame from state.

        Parameters
        ----------
        state
            The state dictionary from a Gradio callback (from ``gr.State``).

        Returns
        -------
        nw.DataFrame
            The filtered data if a SQL query is active, otherwise the full dataset.

        Examples
        --------
        >>> def update_display(state_dict):
        ...     df = qc.df(state_dict)
        ...     return df.to_native()
        ...
        >>> state.change(fn=update_display, inputs=[state], outputs=[data_table])

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
            The state dictionary from a Gradio callback (from ``gr.State``).

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
            The state dictionary from a Gradio callback (from ``gr.State``).

        Returns
        -------
        str | None
            A short description of the current filter, or None if showing full dataset.

        """
        return state.get("title") if state else None

    def ui(self) -> tuple[gr.Column, gr.State]:
        """
        Create chat UI components and state for custom layouts.

        Returns:
        -------
        tuple[gr.Column, gr.State]
            A tuple of (chat_column, state) where state can be wired
            to other components via `.change()` events.

            The state dict contains:

            - ``sql`` (str | None): Current SQL query from chat interactions
            - ``title`` (str | None): Title describing the current query
            - ``error`` (str | None): Error message if the last query failed
            - ``turns`` (list): Serialized chat turns for state persistence

            Use ``.df(state)``, ``.sql(state)``, and ``.title(state)`` to
            access these values conveniently in your callbacks.

            Note: Unlike `.app()`, the greeting is not automatically generated
            when using `.ui()`. The chat starts empty until the user sends
            a message.

            Note: To enable clickable suggestions in custom layouts, pass
            ``.css`` and ``.head`` to your ``.launch()`` call:
            ``app.launch(css=qc.css, head=qc.head)``

        Example:
        -------
        >>> qc = QueryChat(df, "my_table")
        >>> with gr.Blocks() as app:
        ...     chat_ui, state = qc.ui()
        ...     output = gr.Dataframe()
        ...
        ...     def update_data(state_dict):
        ...         return qc.df(state_dict).to_native()
        ...
        ...     state.change(fn=update_data, inputs=[state], outputs=[output])
        >>> app.launch(css=qc.css, head=qc.head)  # Enable clickable suggestions

        """
        import gradio as gr

        def client_factory(update_cb, reset_cb):
            return self.client(update_dashboard=update_cb, reset_dashboard=reset_cb)

        def deserialize_state(state_dict: AppStateDict):
            return create_app_state_from_dict(
                state_dict, self._data_source, client_factory, self.greeting
            )

        initial_state = create_app_state(
            self._data_source, client_factory, self.greeting
        )

        state_holder = gr.State(value=initial_state.to_dict())

        with gr.Column() as chat_column:
            gr.Markdown("## Chat")
            chatbot = gr.Chatbot(label="Chat with your data", height=500)

            with gr.Row():
                msg_input = gr.Textbox(
                    label="Ask a question about your data...",
                    placeholder="Type your question here...",
                    scale=4,
                    show_label=False,
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")

        def submit_message(message: str, state_dict: AppStateDict):
            state = deserialize_state(state_dict)

            if not message.strip():
                return state.get_display_messages(), state.to_dict(), ""

            response = ""
            for chunk in stream_response(state.client, message):
                response += chunk

            return state.get_display_messages(), state.to_dict(), ""

        send_btn.click(
            fn=submit_message,
            inputs=[msg_input, state_holder],
            outputs=[chatbot, state_holder, msg_input],
        )

        msg_input.submit(
            fn=submit_message,
            inputs=[msg_input, state_holder],
            outputs=[chatbot, state_holder, msg_input],
        )

        return chat_column, state_holder


def state_to_ui(
    state: AppState,
    max_display_rows: int = DEFAULT_MAX_DISPLAY_ROWS,
) -> tuple:
    """Convert AppState to UI component values."""
    chat_messages = state.get_display_messages()

    sql_title_text = f"### {state.title or 'SQL Query'}"
    sql_code = state.get_display_sql()

    df = state.get_current_data()
    data_info_parts = []
    if state.error:
        data_info_parts.append(f"⚠️ {state.error}")
    data_info_parts.append(f"*Data has {df.shape[0]} rows and {df.shape[1]} columns.*")
    if len(df) > max_display_rows:
        data_info_parts.append(f"(showing first {max_display_rows} rows)")
    data_info_text = " ".join(data_info_parts)

    display_df = df.head(max_display_rows).to_native()

    return (chat_messages, sql_title_text, sql_code, display_df, data_info_text)


class GradioBlocksWrapper:
    """
    Wrapper for gr.Blocks that passes css/head/theme to launch() for Gradio 6.0+.

    In Gradio 6.0+, css, head, and theme parameters moved from Blocks() constructor
    to launch(). This wrapper intercepts launch() calls to add these automatically.
    """

    def __init__(self, blocks: gr.Blocks, css: str, head: str, theme=None):
        self._blocks = blocks
        self._css = css
        self._head = head
        self._theme = theme

    def launch(self, **kwargs):
        """Launch the Gradio app with querychat CSS/JS/theme injected."""
        user_css = kwargs.pop("css", None)
        user_head = kwargs.pop("head", None)

        final_css = self._css
        if user_css:
            final_css = f"{self._css}\n{user_css}"

        final_head = self._head
        if user_head:
            final_head = f"{self._head}\n{user_head}"

        if "theme" not in kwargs and self._theme is not None:
            kwargs["theme"] = self._theme

        return self._blocks.launch(css=final_css, head=final_head, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped Blocks object."""
        return getattr(self._blocks, name)
