"""Streamlit-specific QueryChat implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ._querychat_base import TOOL_GROUPS, QueryChatBase
from ._querychat_core import (
    GREETING_PROMPT,
    AppState,
    create_app_state,
    stream_response,
)
from ._ui_assets import STREAMLIT_JS, SUGGESTION_CSS

if TYPE_CHECKING:
    from pathlib import Path

    import chatlas
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame

    from ._datasource import LazyOrDataFrame


class QueryChat(QueryChatBase):
    """
    QueryChat for Streamlit applications.

    Provides `.app()`, `.sidebar()`, `.ui()` for rendering, and
    `.df()`, `.sql()`, `.title()` accessors that read from session state.

    Examples
    --------
    Simple app:
    ```python
    from querychat.streamlit import QueryChat

    qc = QueryChat(df, "titanic")
    qc.app()
    ```

    Custom layout:
    ```python
    from querychat.streamlit import QueryChat
    import streamlit as st

    qc = QueryChat(df, "titanic")
    qc.sidebar()

    st.header(qc.title() or "Data View")
    st.dataframe(qc.df())
    st.code(qc.sql() or "SELECT * FROM titanic", language="sql")
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
        self._state_key = f"_querychat_{self._data_source.table_name}"

    def _get_state(self) -> AppState:
        """Get or create session state."""
        import streamlit as st

        if self._state_key not in st.session_state:
            st.session_state[self._state_key] = create_app_state(
                self._data_source,
                lambda update_cb, reset_cb: self.client(
                    update_dashboard=update_cb,
                    reset_dashboard=reset_cb,
                ),
                self.greeting,
            )
        return st.session_state[self._state_key]

    def app(self) -> None:
        """
        Render a complete Streamlit app.

        Configures the page, renders chat in sidebar, and displays
        SQL query and data table in the main area.
        """
        import streamlit as st

        st.set_page_config(
            page_title=f"querychat with {self._data_source.table_name}",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        self.sidebar()
        self._render_main_content()

    def sidebar(self) -> None:
        """Render the chat interface in the Streamlit sidebar."""
        import streamlit as st

        with st.sidebar:
            self.ui()

    def ui(self) -> None:
        """Render the chat interface component."""
        import streamlit.components.v1 as components

        import streamlit as st

        # Inject CSS/JS for clickable suggestions (once per session)
        assets_key = "_querychat_assets_loaded"
        if assets_key not in st.session_state:
            st.session_state[assets_key] = True
            st.html(f"<style>{SUGGESTION_CSS}</style>")
            components.html(f"<script>{STREAMLIT_JS}</script>", height=0)

        state = self._get_state()

        # Initialize greeting BEFORE rendering messages so it appears on first render
        needs_greeting_stream = not state.initialize_greeting_if_preset()

        chat_container = st.container(height="stretch")

        with chat_container:
            for msg in state.get_display_messages():
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"], unsafe_allow_html=True)

            if needs_greeting_stream:
                greeting = ""
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    placeholder.markdown("*Preparing your data assistant...*")
                    for chunk in stream_response(state.client, GREETING_PROMPT):
                        greeting += chunk
                        placeholder.markdown(greeting, unsafe_allow_html=True)
                state.set_greeting(greeting)

        if prompt := st.chat_input(
            "Ask a question about your data...",
            key=f"{self._state_key}_input",
        ):
            if f"{self._state_key}_pending" not in st.session_state:
                st.session_state[f"{self._state_key}_pending"] = prompt
            st.rerun()

        if f"{self._state_key}_pending" in st.session_state:
            prompt = st.session_state[f"{self._state_key}_pending"]
            del st.session_state[f"{self._state_key}_pending"]

            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                content = ""
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    placeholder.markdown("*Thinking...*")
                    for chunk in stream_response(state.client, prompt):
                        content += chunk
                        placeholder.markdown(content, unsafe_allow_html=True)

            st.rerun()

    def df(self) -> LazyOrDataFrame:
        """Get the current filtered data frame (or LazyFrame if data source is lazy)."""
        return self._get_state().get_current_data()

    def sql(self) -> str | None:
        """Get the current SQL query, or None if using default."""
        return self._get_state().sql

    def title(self) -> str | None:
        """Get the current query title, or None if using default."""
        return self._get_state().title

    def reset(self) -> None:
        """
        Reset the dashboard to show all data.

        Clears the current SQL filter, title, and any errors.
        Use this in custom layouts to provide reset functionality.

        Examples
        --------
        ```python
        if st.button("Reset"):
            qc.reset()
        ```

        """
        import streamlit as st

        state = self._get_state()
        state.reset_dashboard()
        st.rerun()

    def _render_main_content(self) -> None:
        """Render the main content area (SQL + data table)."""
        import streamlit as st

        state = self._get_state()

        st.title(f"querychat with `{self._data_source.table_name}`")

        st.subheader(state.title or "SQL Query")

        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.code(state.get_display_sql(), language="sql")

        with col2:
            if state.sql and st.button("Reset Query", type="secondary"):
                state.reset_dashboard()
                st.rerun()

        st.subheader("Data view")
        df = state.get_current_data()
        if state.error:
            st.error(state.error)
        st.dataframe(df, use_container_width=True, height=400, hide_index=True)
        st.caption(f"Data has {df.shape[0]} rows and {df.shape[1]} columns.")
