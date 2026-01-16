"""Gradio-specific QueryChat implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, overload

import narwhals.stable.v1 as nw
from gradio.context import Context

from ._datasource import IntoFrameT, IntoDataFrameT, IntoLazyFrameT
from ._querychat_base import TOOL_GROUPS, QueryChatBase
from ._querychat_core import (
    GREETING_PROMPT,
    AppStateDict,
    StateDictAccessorMixin,
    create_app_state,
    stream_response,
)
from ._ui_assets import GRADIO_CSS, GRADIO_JS, SUGGESTION_CSS

if TYPE_CHECKING:
    from pathlib import Path

    import chatlas
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoDataFrame, IntoLazyFrame

    import gradio as gr


class QueryChat(QueryChatBase[IntoFrameT], StateDictAccessorMixin[IntoFrameT]):
    """
    QueryChat for Gradio applications.

    Provides `.app()` for a complete app, and `.ui()` for custom layouts.

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
            with gr.Column():
                state = qc.ui()

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

    app.launch(css=qc.css, head=qc.head)
    ```

    """

    @overload
    def __init__(
        self: QueryChat[IntoLazyFrameT],
        data_source: IntoLazyFrameT,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[IntoDataFrameT],
        data_source: IntoDataFrameT,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[nw.DataFrame],
        data_source: sqlalchemy.Engine,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ) -> None: ...

    def __init__(
        self,
        data_source: IntoDataFrame | IntoLazyFrame | sqlalchemy.Engine,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
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
        return f"<script>{GRADIO_JS}</script>"

    def ui(self) -> gr.State:
        """
        Create chat UI components for custom layouts.

        Must be called within a ``gr.Blocks`` context. Creates the chat
        components (chatbot, input, button) and wires up greeting
        initialization and message submission handlers.

        Returns:
        -------
        gr.State
            The state component. Wire to other components via ``.change()``.

            The state dict contains:

            - ``sql`` (str | None): Current SQL query from chat interactions
            - ``title`` (str | None): Title describing the current query
            - ``error`` (str | None): Error message if the last query failed
            - ``turns`` (list): Serialized chat turns for state persistence

            Use ``.df(state)``, ``.sql(state)``, and ``.title(state)`` to
            access these values conveniently in your callbacks.

        Note:
        ----
        To enable clickable suggestions in custom layouts, pass
        ``.css`` and ``.head`` to your ``.launch()`` call:
        ``app.launch(css=qc.css, head=qc.head)``

        Example:
        -------
        >>> qc = QueryChat(df, "my_table")
        >>> with gr.Blocks() as app:
        ...     with gr.Column():
        ...         state = qc.ui()
        ...     output = gr.Dataframe()
        ...
        ...     def update_data(state_dict):
        ...         return qc.df(state_dict).to_native()
        ...
        ...     state.change(fn=update_data, inputs=[state], outputs=[output])
        >>> app.launch(css=qc.css, head=qc.head)

        """
        import gradio as gr

        initial_state = create_app_state(
            self._data_source, self._client_factory, self.greeting
        )

        state_holder = gr.State(value=initial_state.to_dict())

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
            send_btn = gr.Button("Send", scale=1, variant="primary", min_width=80)

        def initialize_greeting(state_dict: AppStateDict):
            state = self._deserialize_state(state_dict)

            if not state.initialize_greeting_if_preset():
                greeting = ""
                for chunk in stream_response(state.client, GREETING_PROMPT):
                    greeting += chunk
                state.set_greeting(greeting)

            return state.get_display_messages(), state.to_dict()

        def submit_message(message: str, state_dict: AppStateDict):
            state = self._deserialize_state(state_dict)

            if not message.strip():
                return state.get_display_messages(), state.to_dict(), ""

            for _chunk in stream_response(state.client, message):
                pass

            return state.get_display_messages(), state.to_dict(), ""

        # Wire load event to parent Blocks for greeting initialization
        blocks = Context.root_block
        if blocks is not None:
            blocks.load(
                fn=initialize_greeting,
                inputs=[state_holder],
                outputs=[chatbot, state_holder],
            )

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

        return state_holder

    def app(self) -> GradioBlocksWrapper:
        """
        Create a complete Gradio app.

        Returns
        -------
        GradioBlocksWrapper
            A wrapped Gradio Blocks app ready to launch. The wrapper injects
            querychat CSS/JS at launch time for Gradio 6.0+ compatibility.

        """
        from gradio.themes import Soft

        import gradio as gr

        with gr.Blocks(
            title=f"querychat with {self._data_source.table_name}",
        ) as blocks_app:
            with gr.Sidebar(label="Chat", open=True, width=420):
                state_holder = self.ui()

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

            def update_displays(state_dict: AppStateDict):
                """Update SQL and data displays based on state."""
                title = state_dict.get("title") if state_dict else None
                error = state_dict.get("error") if state_dict else None

                sql_title_text = f"### {title or 'SQL Query'}"
                sql_code = (
                    state_dict.get("sql")
                    if state_dict and state_dict.get("sql")
                    else f"SELECT * FROM {self._data_source.table_name}"
                )

                # Wrap in narwhals for uniform DataFrame operations
                df = nw.from_native(self.df(state_dict))
                if isinstance(df, nw.LazyFrame):
                    df = df.collect()

                data_info_parts = []
                if error:
                    data_info_parts.append(f"⚠️ {error}")
                data_info_parts.append(
                    f"*Data has {df.shape[0]} rows and {df.shape[1]} columns.*"
                )
                data_info_text = " ".join(data_info_parts)

                return sql_title_text, sql_code, df.to_native(), data_info_text

            def reset_query(state_dict: AppStateDict):
                """Reset state to show full dataset."""
                state = self._deserialize_state(state_dict)
                state.reset_dashboard()
                return state.to_dict()

            # Update displays when state changes
            state_holder.change(
                fn=update_displays,
                inputs=[state_holder],
                outputs=[sql_title, sql_display, data_display, data_info],
            )

            reset_btn.click(
                fn=reset_query,
                inputs=[state_holder],
                outputs=[state_holder],
            )

        # Wrap the Blocks to inject CSS/JS/theme at launch() time (Gradio 6.0+)
        combined_css = f"{SUGGESTION_CSS}\n{GRADIO_CSS}"
        return GradioBlocksWrapper(
            blocks_app,
            combined_css,
            f"<script>{GRADIO_JS}</script>",
            theme=Soft(),
        )


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
        css = f"{self._css}\n{user_css}" if user_css else self._css
        head = f"{self._head}\n{user_head}" if user_head else self._head
        if "theme" not in kwargs and self._theme is not None:
            kwargs["theme"] = self._theme
        return self._blocks.launch(css=css, head=head, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped Blocks object."""
        return getattr(self._blocks, name)
