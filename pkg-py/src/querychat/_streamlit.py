"""Streamlit-specific QueryChat implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional, cast, overload

from narwhals.stable.v1.typing import IntoDataFrameT, IntoFrameT, IntoLazyFrameT

from ._querychat_base import TOOL_GROUPS, QueryChatBase
from ._querychat_core import (
    GREETING_PROMPT,
    AppState,
    create_app_state,
    stream_response,
)
from ._ui_assets import STREAMLIT_JS, SUGGESTION_CSS
from ._utils import as_narwhals

if TYPE_CHECKING:
    from pathlib import Path

    import altair as alt
    import chatlas
    import ibis
    import narwhals.stable.v1 as nw
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame


class QueryChat(QueryChatBase[IntoFrameT]):
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

    @overload
    def __init__(
        self: QueryChat[Any],
        data_source: None,
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
        self: QueryChat[ibis.Table],
        data_source: ibis.Table,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[IntoLazyFrameT],
        data_source: IntoLazyFrameT,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
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
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
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
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ) -> None: ...

    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine | ibis.Table | None,
        table_name: str,
        *,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = (
            "update",
            "query",
            "visualize_dashboard",
            "visualize_query",
        ),
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
        self._state_key = f"_querychat_{table_name}"

    def _get_state(self) -> AppState:
        """Get or create session state."""
        data_source = self._require_data_source("_get_state")
        import streamlit as st

        if self._state_key not in st.session_state:
            st.session_state[self._state_key] = create_app_state(
                data_source,
                lambda update_cb, reset_cb, filter_viz_cb, query_viz_cb: self.client(
                    update_dashboard=update_cb,
                    reset_dashboard=reset_cb,
                    visualize_dashboard=filter_viz_cb,
                    visualize_query=query_viz_cb,
                ),
                self.greeting,
            )
        return st.session_state[self._state_key]

    def app(self) -> None:
        """
        Render a complete Streamlit app.

        Configures the page, renders chat in sidebar, and displays
        SQL query, data table, and visualizations in a tabbed interface.

        The app includes three tabs:
        - **Data**: Shows the filtered data table with the current SQL query
        - **Filter Plot**: Shows the persistent dashboard visualization
        - **Query Plot**: Shows the most recent query visualization
        """
        data_source = self._require_data_source("app")
        import streamlit as st

        st.set_page_config(
            page_title=f"querychat with {data_source.table_name}",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        self.sidebar()

        state = self._get_state()

        st.title(f"querychat with `{self._data_source.table_name}`")

        data_tab, filter_plot_tab, query_plot_tab = st.tabs(
            ["Data", "Filter Plot", "Query Plot"]
        )

        with data_tab:
            self._render_data_tab(state)

        with filter_plot_tab:
            self._render_filter_plot_tab()

        with query_plot_tab:
            self._render_query_plot_tab()

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

    def df(self) -> IntoFrameT:
        """
        Get the current filtered data.

        Returns the same type as the original data source: a DataFrame for
        eager sources, a LazyFrame for Polars lazy sources, or an Ibis Table
        for Ibis sources. Callers needing an eager DataFrame should collect
        the result (e.g., via ``as_narwhals(qc.df())``).
        """
        # Cast is safe because get_current_data() returns the same type as the data source
        return cast("IntoFrameT", self._get_state().get_current_data())

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

    def ggvis(self, source: Literal["filter", "query"] = "filter") -> alt.Chart | None:
        """
        Get the current Altair visualization chart.

        Parameters
        ----------
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

        from ._utils import as_narwhals

        state = self._get_state()
        if source == "filter":
            spec = state.filter_viz_spec
            if spec is None:
                return None
            # Render against current filtered data
            df = as_narwhals(self.df())
            return ggsql.render_altair(df, spec)
        else:
            ggsql_query = state.query_viz_ggsql
            if ggsql_query is None:
                return None
            # Re-execute SQL and render
            sql, viz_spec = ggsql.split_query(ggsql_query)
            df = as_narwhals(self._data_source.execute_query(sql))
            return ggsql.render_altair(df, viz_spec)

    def ggsql(self, source: Literal["filter", "query"] = "filter") -> str | None:
        """
        Get the current ggsql specification.

        Parameters
        ----------
        source
            Which specification to return. "filter" returns the VISUALISE spec
            from visualize_dashboard, "query" returns the full ggsql query
            from visualize_query.

        Returns
        -------
        :
            The ggsql specification string, or None if no visualization exists.

        """
        state = self._get_state()
        if source == "filter":
            return state.filter_viz_spec
        else:
            return state.query_viz_ggsql

    def ggtitle(self, source: Literal["filter", "query"] = "filter") -> str | None:
        """
        Get the current visualization title.

        Parameters
        ----------
        source
            Which title to return. "filter" returns the title from
            visualize_dashboard, "query" returns the title from visualize_query.

        Returns
        -------
        :
            The visualization title, or None if no visualization exists.

        """
        state = self._get_state()
        if source == "filter":
            return state.filter_viz_title
        else:
            return state.query_viz_title

    def _render_data_tab(self, state: AppState) -> None:
        """Render the Data tab content."""
        import streamlit as st

        st.subheader(state.title or "SQL Query")

        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.code(state.get_display_sql(), language="sql")

        with col2:
            if state.sql and st.button("Reset Query", type="secondary"):
                state.reset_dashboard()
                st.rerun()

        st.subheader("Data view")
        df = as_narwhals(state.get_current_data())
        if state.error:
            st.error(state.error)
        st.dataframe(
            df.to_native(), use_container_width=True, height=400, hide_index=True
        )
        st.caption(f"Data has {df.shape[0]} rows and {df.shape[1]} columns.")

    def _render_filter_plot_tab(self) -> None:
        """Render the Filter Plot tab content."""
        import streamlit as st

        chart = self.ggvis("filter")
        if chart is not None:
            title = self.ggtitle("filter")
            if title:
                st.subheader(title)
            st.altair_chart(chart, use_container_width=True)

            spec = self.ggsql("filter")
            if spec:
                with st.expander("ggsql spec"):
                    st.code(spec, language="sql")
        else:
            st.info(
                "No filter visualization. Ask the assistant to create one "
                "using the visualize_dashboard tool."
            )

    def _render_query_plot_tab(self) -> None:
        """Render the Query Plot tab content."""
        import streamlit as st

        chart = self.ggvis("query")
        if chart is not None:
            title = self.ggtitle("query")
            if title:
                st.subheader(title)
            st.altair_chart(chart, use_container_width=True)

            spec = self.ggsql("query")
            if spec:
                with st.expander("ggsql query"):
                    st.code(spec, language="sql")
        else:
            st.info(
                "No query visualization. Ask the assistant to create one "
                "using the visualize_query tool."
            )
