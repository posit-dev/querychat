from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, overload

import chatlas
import chevron
import sqlalchemy
from chatlas import ContentToolRequest, ContentToolResult
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from shiny.express._stub_session import ExpressStubSession
from shiny.session import get_current_session
from shinychat import output_markdown_stream

from ._datasource import DataFrameSource, DataSource, SQLAlchemySource
from ._icons import bs_icon
from ._querychat_module import GREETING_PROMPT, ServerValues, mod_server, mod_ui
from .tools import tool_query, tool_reset_dashboard, tool_update_dashboard

if TYPE_CHECKING:
    import pandas as pd
    from chatlas import Chat
    from narwhals.stable.v1.typing import IntoFrame

    try:
        import streamlit as st
    except ImportError:
        pass


class QueryChatBase:
    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
    ):
        self._data_source = normalize_data_source(data_source, table_name)

        # Validate table name (must begin with letter, contain only letters, numbers, underscores)
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
            raise ValueError(
                "Table name must begin with a letter and contain only letters, numbers, and underscores",
            )

        self.id = id or table_name

        self.greeting = greeting.read_text() if isinstance(greeting, Path) else greeting

        prompt = assemble_system_prompt(
            self._data_source,
            data_description=data_description,
            extra_instructions=extra_instructions,
            categorical_threshold=categorical_threshold,
            prompt_template=prompt_template,
        )

        # Fork and empty chat now so the per-session forks are fast
        client = as_querychat_client(client)
        self._client = copy.deepcopy(client)
        self._client.set_turns([])
        self._client.system_prompt = prompt

    def app(
        self, *, bookmark_store: Literal["url", "server", "disable"] = "url"
    ) -> App:
        """
        Quickly chat with a dataset.

        Creates a Shiny app with a chat sidebar and data table view -- providing a
        quick-and-easy way to start chatting with your data.

        Parameters
        ----------
        bookmark_store
            The bookmarking store to use for the Shiny app. Options are:
                - `"url"`: Store bookmarks in the URL (default).
                - `"server"`: Store bookmarks on the server.
                - `"disable"`: Disable bookmarking.

        Returns
        -------
        :
            A Shiny App object that can be run with `app.run()` or served with `shiny run`.

        """
        enable_bookmarking = bookmark_store != "disable"
        table_name = self._data_source.table_name

        def app_ui(request):
            return ui.page_sidebar(
                self.sidebar(),
                ui.card(
                    ui.card_header(
                        ui.div(
                            ui.div(
                                bs_icon("terminal-fill"),
                                ui.output_text("query_title", inline=True),
                                class_="d-flex align-items-center gap-2",
                            ),
                            ui.output_ui("ui_reset", inline=True),
                            class_="hstack gap-3",
                        ),
                    ),
                    ui.output_ui("sql_output"),
                    fill=False,
                    style="max-height: 33%;",
                ),
                ui.card(
                    ui.card_header(bs_icon("table"), " Data"),
                    ui.output_data_frame("dt"),
                ),
                title=ui.span("querychat with ", ui.code(table_name)),
                class_="bslib-page-dashboard",
                fillable=True,
            )

        def app_server(input: Inputs, output: Outputs, session: Session):
            vals = mod_server(
                self.id,
                data_source=self._data_source,
                greeting=self.greeting,
                client=self._client,
                enable_bookmarking=enable_bookmarking,
            )

            @render.text
            def query_title():
                return vals.title() or "SQL Query"

            @render.ui
            def ui_reset():
                req(vals.sql())
                return ui.input_action_button(
                    "reset_query",
                    "Reset Query",
                    class_="btn btn-outline-danger btn-sm lh-1 ms-auto",
                )

            @reactive.effect
            @reactive.event(input.reset_query)
            def _():
                vals.sql.set("")
                vals.title.set(None)

            @render.data_frame
            def dt():
                return vals.df()

            @render.ui
            def sql_output():
                sql_value = vals.sql() or f"SELECT * FROM {table_name}"
                sql_code = f"```sql\n{sql_value}\n```"
                return output_markdown_stream(
                    "sql_code",
                    content=sql_code,
                    auto_scroll=False,
                    width="100%",
                )

        return App(app_ui, app_server, bookmark_store=bookmark_store)

    def streamlit_app(self) -> None:
        """
        Create a Streamlit app to chat with a dataset.

        Creates a Streamlit interface with a chat sidebar and data table view --
        providing a quick-and-easy way to start chatting with your data using Streamlit.

        This method should be called as the main content of a Streamlit app file.
        The function configures the Streamlit page and sets up all necessary UI elements.

        Returns
        -------
        None
            This function has side effects (renders Streamlit UI) but doesn't return a value.

        Raises
        ------
        ImportError
            If streamlit is not installed.

        Examples
        --------
        Create a file named `app.py`:

        ```python
        from querychat import QueryChat
        from seaborn import load_dataset

        titanic = load_dataset("titanic")
        qc = QueryChat(titanic, "titanic")
        qc.streamlit_app()
        ```

        Then run with: `streamlit run app.py`

        """
        try:
            import streamlit as st
        except ImportError as e:
            msg = (
                "streamlit is required to use streamlit_app(). "
                "Install it with: pip install streamlit"
            )
            raise ImportError(msg) from e

        table_name = self._data_source.table_name

        # Set page configuration (only if not already set)
        try:
            st.set_page_config(
                page_title=f"querychat with {table_name}",
                layout="wide",
                initial_sidebar_state="expanded",
            )
        except Exception:
            # Page config already set - that's ok
            pass

        # Helper class to wrap session state as reactive values
        class SessionStateReactive:
            def __init__(self, key: str, default=None):
                self.key = key
                if key not in st.session_state:
                    st.session_state[key] = default

            def set(self, value):
                st.session_state[self.key] = value

            def get(self):
                return st.session_state[self.key]

        # Initialize session state
        if "querychat_initialized" not in st.session_state:
            st.session_state.querychat_initialized = True
            st.session_state.chat_history = []
            st.session_state.client = copy.deepcopy(self._client)
            st.session_state.sql = ""
            st.session_state.title = None
            st.session_state.tools_registered = False

        # Register tools with the client (only once)
        if not st.session_state.tools_registered:
            sql_reactive = SessionStateReactive("sql", "")
            title_reactive = SessionStateReactive("title", None)

            st.session_state.client.register_tool(
                tool_update_dashboard(self._data_source, sql_reactive, title_reactive)
            )
            st.session_state.client.register_tool(tool_query(self._data_source))
            st.session_state.client.register_tool(
                tool_reset_dashboard(sql_reactive, title_reactive)
            )
            st.session_state.tools_registered = True

        def streamlit_generator(prompt: str, client: Chat):
            for chunk in client.stream(prompt, content="all", echo="none"):
                if isinstance(chunk, ContentToolRequest):
                    # Show request doesn't seem all that useful since result follows and will show the SQL
                    yield ""
                elif isinstance(chunk, ContentToolResult):
                    # Get display metadata if available
                    display_info = chunk.extra.get("display") if chunk.extra else None

                    if display_info and hasattr(display_info, "markdown"):
                        res = "\n\n" + display_info.markdown + "\n\n"
                    else:
                        res = "\n\n" + str(chunk) + "\n\n"

                    # yield st.markdown(res, unsafe_allow_html=True)
                    yield res

                elif isinstance(chunk, str):
                    yield chunk

        # Sidebar with chat interface
        with st.sidebar:
            # Container for chat messages with fixed height (scrollable)
            chat_container = st.container(height="stretch")

            with chat_container:
                for message in st.session_state.chat_history:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"], unsafe_allow_html=True)

                if not st.session_state.chat_history:
                    greeting = self.greeting
                    if not greeting:
                        stream = streamlit_generator(
                            GREETING_PROMPT, st.session_state.client
                        )
                        greeting = ""
                        with st.chat_message("assistant"):
                            message_placeholder = st.empty()
                            for chunk in stream:
                                greeting += chunk
                                message_placeholder.markdown(greeting, unsafe_allow_html=True)

                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": greeting}
                    )

            # Chat input (stays at bottom of sidebar, outside the scrollable container)
            if prompt := st.chat_input(
                "Ask a question about your data...",
                key="chat_input",
            ):
                st.session_state.querychat_pending_prompt = prompt
                st.rerun()

            # Process pending prompt if any (from chat input or suggestion button)
            if st.session_state.get("querychat_pending_prompt"):
                prompt = st.session_state.querychat_pending_prompt
                st.session_state.querychat_pending_prompt = None

                st.session_state.chat_history.append(
                    {"role": "user", "content": prompt}
                )

                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    stream = streamlit_generator(prompt, st.session_state.client)
                    stream_content = ""
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        for chunk in stream:
                            stream_content += chunk
                            message_placeholder.markdown(stream_content, unsafe_allow_html=True)

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": stream_content,
                    }
                )

                # Force rerun to update the data display
                st.rerun()

        # Main content area
        st.title(f"querychat with `{table_name}`")

        # SQL Query display
        st.subheader(st.session_state.title or "SQL Query")

        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            sql_display = st.session_state.sql or f"SELECT * FROM {table_name}"
            st.code(sql_display, language="sql")

        with col2:
            if st.session_state.sql:
                if st.button("Reset Query", type="secondary"):
                    st.session_state.sql = ""
                    st.session_state.title = None
                    st.rerun()

        # Data display
        st.subheader("Data")

        if st.session_state.sql:
            df = self._data_source.execute_query(st.session_state.sql)
        else:
            df = self._data_source.get_data()

        st.dataframe(df, use_container_width=True, height=400)

    def sidebar(
        self,
        *,
        width: int = 400,
        height: str = "100%",
        **kwargs,
    ) -> ui.Sidebar:
        """
        Create a sidebar containing the querychat UI.

        Parameters
        ----------
        width
            Width of the sidebar in pixels.
        height
            Height of the sidebar.
        **kwargs
            Additional arguments passed to `shiny.ui.sidebar()`.

        Returns
        -------
        :
            A sidebar UI component.

        """
        return ui.sidebar(
            self.ui(),
            width=width,
            height=height,
            class_="querychat-sidebar",
            **kwargs,
        )

    def ui(self, **kwargs):
        """
        Create the UI for the querychat component.

        Parameters
        ----------
        **kwargs
            Additional arguments to pass to `shinychat.chat_ui()`.

        Returns
        -------
        :
            A UI component.

        """
        return mod_ui(self.id, **kwargs)

    def generate_greeting(self, *, echo: Literal["none", "output"] = "none"):
        """
        Generate a welcome greeting for the chat.

        By default, `QueryChat()` generates a greeting at the start of every new
        conversation, which is convenient for getting started and development,
        but also might add unnecessary latency and cost. Use this method to
        generate a greeting once and save it for reuse.

        Parameters
        ----------
        echo
            If `echo = "output"`, prints the greeting to standard output. If
            `echo = "none"` (default), does not print anything.

        Returns
        -------
        :
            The greeting string (in Markdown format).

        """
        client = copy.deepcopy(self._client)
        client.set_turns([])
        return str(client.chat(GREETING_PROMPT, echo=echo))

    @property
    def system_prompt(self) -> str:
        """
        Get the system prompt.

        Returns
        -------
        :
            The system prompt string.

        """
        return self._client.system_prompt or ""

    @property
    def data_source(self):
        """
        Get the current data source.

        Returns
        -------
        :
            The current data source.

        """
        return self._data_source

    def cleanup(self) -> None:
        """
        Clean up resources associated with the data source.

        Call this method when you are done using the QueryChat object to close
        database connections and avoid resource leaks.

        Returns
        -------
        None

        """
        self._data_source.cleanup()


class QueryChat(QueryChatBase):
    """
    Create a QueryChat instance.

    Examples
    --------
    ```python
    from querychat import QueryChat

    qc = QueryChat(my_dataframe, "my_data")
    qc.app()
    ```

    Parameters
    ----------
    data_source
        Either a Narwhals-compatible data frame (e.g., Polars or Pandas) or a
        SQLAlchemy engine containing the table to query against.
    table_name
        If a data_source is a data frame, a name to use to refer to the table in
        SQL queries (usually the variable name of the data frame, but it doesn't
        have to be). If a data_source is a SQLAlchemy engine, the table_name is
        the name of the table in the database to query against.
    id
        An optional ID for the QueryChat module. If not provided, an ID will be
        generated based on the table_name.
    greeting
        A string in Markdown format, containing the initial message. If a
        pathlib.Path object is passed, querychat will read the contents of the
        path into a string with `.read_text()`. You can use
        `querychat.greeting()` to help generate a greeting from a querychat
        configuration. If no greeting is provided, one will be generated at the
        start of every new conversation.
    client
        A `chatlas.Chat` object or a string to be passed to
        `chatlas.ChatAuto()`'s `provider_model` parameter, describing the
        provider and model combination to use (e.g. `"openai/gpt-4.1"`,
        "anthropic/claude-sonnet-4-5", "google/gemini-2.5-flash". etc).

        If `client` is not provided, querychat consults the
        `QUERYCHAT_CLIENT` environment variable. If that is not set, it
        defaults to `"openai"`.
    data_description
        Description of the data in plain text or Markdown. If a pathlib.Path
        object is passed, querychat will read the contents of the path into a
        string with `.read_text()`.
    categorical_threshold
        Threshold for determining if a column is categorical based on number of
        unique values.
    extra_instructions
        Additional instructions for the chat model. If a pathlib.Path object is
        passed, querychat will read the contents of the path into a string with
        `.read_text()`.
    prompt_template
        Path to or a string of a custom prompt file. If not provided, the default querychat
        template will be used. This should be a Markdown file that contains the
        system prompt template. The mustache template can use the following
        variables:
        - `{{db_engine}}`: The database engine used (e.g., "DuckDB")
        - `{{schema}}`: The schema of the data source, generated by
          `data_source.get_schema()`
        - `{{data_description}}`: The optional data description provided
        - `{{extra_instructions}}`: Any additional instructions provided

    """

    def server(self, *, enable_bookmarking: bool = False) -> ServerValues:
        """
        Initialize Shiny server logic.

        This method is intended for use in Shiny Code mode, where the user must
        explicitly call `.server()` within the Shiny server function. In Shiny
        Express mode, you can use `querychat.express.QueryChat` instead
        of `querychat.QueryChat`, which calls `.server()` automatically.

        Parameters
        ----------
        enable_bookmarking
            Whether to enable bookmarking for the querychat module.

        Examples
        --------
        ```python
        from shiny import App, render, ui
        from seaborn import load_dataset
        from querychat import QueryChat

        titanic = load_dataset("titanic")

        qc = QueryChat(titanic, "titanic")


        def app_ui(request):
            return ui.page_sidebar(
                qc.sidebar(),
                ui.card(
                    ui.card_header(ui.output_text("title")),
                    ui.output_data_frame("data_table"),
                ),
                title="Titanic QueryChat App",
                fillable=True,
            )


        def server(input, output, session):
            qc_vals = qc.server(enable_bookmarking=True)

            @render.data_frame
            def data_table():
                return qc_vals.df()

            @render.text
            def title():
                return qc_vals.title() or "My Data"


        app = App(app_ui, server, bookmark_store="url")
        ```

        Returns
        -------
        :
            A ServerValues dataclass containing session-specific reactive values
            and the chat client. See ServerValues documentation for details on
            the available attributes.

        """
        session = get_current_session()
        if session is None:
            raise RuntimeError(
                ".server() must be called within an active Shiny session (i.e., within the server function). "
            )

        return mod_server(
            self.id,
            data_source=self._data_source,
            greeting=self.greeting,
            client=self._client,
            enable_bookmarking=enable_bookmarking,
        )


class QueryChatExpress(QueryChatBase):
    """
    Use QueryChat with Shiny Express.

    This class makes it easy to use querychat within Shiny Express apps --
    it automatically calls `.server()` during initialization, so you don't
    have to do it manually.

    Examples
    --------
    ```python
    from querychat.express import QueryChat
    from seaborn import load_dataset
    from shiny.express import app_opts, render, ui

    titanic = load_dataset("titanic")

    qc = QueryChat(titanic, "titanic")
    qc.sidebar()

    with ui.card(fill=True):
        with ui.card_header():

            @render.text
            def title():
                return qc.title() or "Titanic Dataset"

        @render.data_frame
        def data_table():
            return qc.df()


    ui.page_opts(
        title="Titanic QueryChat App",
        fillable=True,
    )

    app_opts(bookmark_store="url")
    ```

    Parameters
    ----------
    data_source
        Either a Narwhals-compatible data frame (e.g., Polars or Pandas) or a
        SQLAlchemy engine containing the table to query against.
    table_name
        If a data_source is a data frame, a name to use to refer to the table in
        SQL queries (usually the variable name of the data frame, but it doesn't
        have to be). If a data_source is a SQLAlchemy engine, the table_name is
        the name of the table in the database to query against.
    id
        An optional ID for the QueryChat module. If not provided, an ID will be
        generated based on the table_name.
    greeting
        A string in Markdown format, containing the initial message. If a
        pathlib.Path object is passed, querychat will read the contents of the
        path into a string with `.read_text()`. You can use
        `querychat.greeting()` to help generate a greeting from a querychat
        configuration. If no greeting is provided, one will be generated at the
        start of every new conversation.
    client
        A `chatlas.Chat` object or a string to be passed to
        `chatlas.ChatAuto()`'s `provider_model` parameter, describing the
        provider and model combination to use (e.g. `"openai/gpt-4.1"`,
        "anthropic/claude-sonnet-4-5", "google/gemini-2.5-flash". etc).

        If `client` is not provided, querychat consults the
        `QUERYCHAT_CLIENT` environment variable. If that is not set, it
        defaults to `"openai"`.
    data_description
        Description of the data in plain text or Markdown. If a pathlib.Path
        object is passed, querychat will read the contents of the path into a
        string with `.read_text()`.
    categorical_threshold
        Threshold for determining if a column is categorical based on number of
        unique values.
    extra_instructions
        Additional instructions for the chat model. If a pathlib.Path object is
        passed, querychat will read the contents of the path into a string with
        `.read_text()`.
    prompt_template
        Path to or a string of a custom prompt file. If not provided, the default querychat
        template will be used. This should be a Markdown file that contains the
        system prompt template. The mustache template can use the following
        variables:
        - `{{db_engine}}`: The database engine used (e.g., "DuckDB")
        - `{{schema}}`: The schema of the data source, generated by
          `data_source.get_schema()`
        - `{{data_description}}`: The optional data description provided
        - `{{extra_instructions}}`: Any additional instructions provided

    """

    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        data_description: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        enable_bookmarking: Literal["auto", True, False] = "auto",
    ):
        # Sanity check: Express should always have a (stub/real) session
        session = get_current_session()
        if session is None:
            raise RuntimeError(
                "Unexpected error: No active Shiny session found. "
                "Is express.QueryChat() being called outside of a Shiny Express app?",
            )

        super().__init__(
            data_source,
            table_name,
            id=id,
            greeting=greeting,
            client=client,
            data_description=data_description,
            categorical_threshold=categorical_threshold,
            extra_instructions=extra_instructions,
            prompt_template=prompt_template,
        )

        # If the Express session has a bookmark store set, automatically enable
        # querychat's bookmarking
        enable: bool
        if enable_bookmarking == "auto":
            if isinstance(session, ExpressStubSession):
                store = session.app_opts.get("bookmark_store", "disable")
                enable = store != "disable"
            else:
                enable = False
        else:
            enable = enable_bookmarking

        self._vals = mod_server(
            self.id,
            data_source=self._data_source,
            greeting=self.greeting,
            client=self._client,
            enable_bookmarking=enable,
        )

    def df(self) -> pd.DataFrame:
        """
        Reactively read the current filtered data frame that is in effect.

        Returns
        -------
        :
            The current filtered data frame as a pandas DataFrame. If no query
            has been set, this will return the unfiltered data frame from the
            data source.

        """
        return self._vals.df()

    @overload
    def sql(self, query: None = None) -> str: ...

    @overload
    def sql(self, query: str) -> bool: ...

    def sql(self, query: Optional[str] = None) -> str | bool:
        """
        Reactively read (or set) the current SQL query that is in effect.

        Parameters
        ----------
        query
            If provided, sets the current SQL query to this value.

        Returns
        -------
        :
            If no `query` is provided, returns the current SQL query as a string
            (possibly `""` if no query has been set). If a `query` is provided,
            returns `True` if the query was changed to a new value, or `False`
            if it was the same as the current value.

        """
        if query is None:
            return self._vals.sql()
        else:
            return self._vals.sql.set(query)

    @overload
    def title(self, value: None = None) -> str | None: ...

    @overload
    def title(self, value: str) -> bool: ...

    def title(self, value: Optional[str] = None) -> str | None | bool:
        """
        Reactively read (or set) the current title that is in effect.

        The title is a short description of the current query that the LLM
        provides to us whenever it generates a new SQL query. It can be used as
        a status string for the data dashboard.

        Parameters
        ----------
        value
            If provided, sets the current title to this value.

        Returns
        -------
        :
            If no `value` is provided, returns the current title as a string, or
            `None` if no title has been set due to no SQL query being set. If a
            `value` is provided, sets the current title to this value and
            returns `True` if the title was changed to a new value, or `False`
            if it was the same as the current value.

        """
        if value is None:
            return self._vals.title()
        else:
            return self._vals.title.set(value)

    @property
    def client(self):
        """
        Get the (session-specific) chat client.

        Returns
        -------
        :
            The current chat client.

        """
        return self._vals.client


def normalize_data_source(
    data_source: IntoFrame | sqlalchemy.Engine | DataSource,
    table_name: str,
) -> DataSource:
    if isinstance(data_source, DataSource):
        return data_source
    if isinstance(data_source, sqlalchemy.Engine):
        return SQLAlchemySource(data_source, table_name)
    return DataFrameSource(data_source, table_name)


def as_querychat_client(client: str | chatlas.Chat | None) -> chatlas.Chat:
    if client is None:
        client = os.getenv("QUERYCHAT_CLIENT", None)

    if client is None:
        client = "openai"

    if isinstance(client, chatlas.Chat):
        return client

    return chatlas.ChatAuto(provider_model=client)


def assemble_system_prompt(
    data_source: DataSource,
    *,
    data_description: Optional[str | Path] = None,
    extra_instructions: Optional[str | Path] = None,
    categorical_threshold: int = 20,
    prompt_template: Optional[str | Path] = None,
) -> str:
    # Read the prompt file
    if prompt_template is None:
        # Default to the prompt file in the same directory as this module
        # This allows for easy customization by placing a different prompt.md file there
        prompt_template = Path(__file__).parent / "prompts" / "prompt.md"
    prompt_str = (
        prompt_template.read_text()
        if isinstance(prompt_template, Path)
        else prompt_template
    )

    data_description_str = (
        data_description.read_text()
        if isinstance(data_description, Path)
        else data_description
    )

    extra_instructions_str = (
        extra_instructions.read_text()
        if isinstance(extra_instructions, Path)
        else extra_instructions
    )

    is_duck_db = data_source.get_db_type().lower() == "duckdb"

    return chevron.render(
        prompt_str,
        {
            "db_type": data_source.get_db_type(),
            "is_duck_db": is_duck_db,
            "schema": data_source.get_schema(
                categorical_threshold=categorical_threshold,
            ),
            "data_description": data_description_str,
            "extra_instructions": extra_instructions_str,
        },
    )
