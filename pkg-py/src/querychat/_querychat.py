from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, overload

import chatlas
import chevron
import sqlalchemy
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from shiny.express._stub_session import ExpressStubSession
from shiny.session import get_current_session
from shinychat import output_markdown_stream

from ._datasource import DataFrameSource, DataSource, SQLAlchemySource
from ._icons import bs_icon
from ._querychat_module import GREETING_PROMPT, ServerValues, mod_server, mod_ui
from ._system_prompt import QueryChatSystemPrompt
from ._utils import MISSING, MISSING_TYPE
from .tools import (
    UpdateDashboardData,
    tool_query,
    tool_reset_dashboard,
    tool_update_dashboard,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import pandas as pd
    from narwhals.stable.v1.typing import IntoFrame

TOOL_GROUPS = Literal["update", "query"]


class QueryChatBase:
    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("update", "query"),
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

        self.tools = normalize_tools(tools, default=("update", "query"))
        self.greeting = greeting.read_text() if isinstance(greeting, Path) else greeting

        # Store prompt components for lazy assembly
        if prompt_template is None:
            prompt_template = Path(__file__).parent / "prompts" / "prompt.md"

        self._system_prompt = QueryChatSystemPrompt(
            prompt_template=prompt_template,
            data_source=self._data_source,
            data_description=data_description,
            extra_instructions=extra_instructions,
            categorical_threshold=categorical_threshold,
        )

        # Fork and empty chat now so the per-session forks are fast
        client = as_querychat_client(client)
        self._client = copy.deepcopy(client)
        self._client.set_turns([])

        # Storage for console client
        self._client_console = None

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
                vals.sql.set(None)
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

    def sidebar(
        self,
        *,
        width: int = 400,
        height: str = "100%",
        fillable: bool = True,
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
        fillable
            Whether the sidebar should be fillable. Default is `True`.
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
            fillable=fillable,
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

    def client(
        self,
        *,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None | MISSING_TYPE = MISSING,
        update_dashboard: Callable[[UpdateDashboardData], None] | None = None,
        reset_dashboard: Callable[[], None] | None = None,
    ) -> chatlas.Chat:
        """
        Create a chat client with registered tools.

        This method creates a standalone chat client configured with the
        specified tools and callbacks. Each call returns an independent client
        instance with its own conversation state.

        Parameters
        ----------
        tools
            Which tools to include: `"update"`, `"query"`, or both. Can be:
            - A single tool string: `"update"` or `"query"`
            - A tuple of tools: `("update", "query")`
            - `None` or `()` to skip adding any tools
            - If not provided (default), uses the tools specified during initialization
        update_dashboard
            Optional callback function to call when the update_dashboard tool
            succeeds. Takes a dict with `"query"` and `"title"` keys. Only used
            if `"update"` is in tools.
        reset_dashboard
            Optional callback function to call when the `tool_reset_dashboard`
            is invoked. Takes no arguments. Only used if `"update"` is in tools.

        Returns
        -------
        chatlas.Chat
            A configured chat client with tools registered based on the tools parameter.

        Examples
        --------
        ```python
        from querychat import QueryChat
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, 3]})
        qc = QueryChat(df, "my_data")

        # Create client with all tools (default)
        client = qc.client()
        response = client.chat("What's the average of column a?")

        # Create client with only query tool (single string)
        client = qc.client(tools="query")

        # Create client with only query tool (tuple)
        client = qc.client(tools=("query",))

        # Create client with custom callbacks
        from querychat import UpdateDashboardData


        def my_update(data: UpdateDashboardData):
            print(f"Query: {data['query']}, Title: {data['title']}")


        client = qc.client(update_dashboard=my_update)
        ```

        """
        tools = normalize_tools(tools, default=self.tools)

        chat = copy.deepcopy(self._client)
        chat.set_turns([])

        chat.system_prompt = self._system_prompt.render(tools)

        if tools is None:
            return chat

        if "update" in tools:
            # Default callbacks that do nothing
            update_fn = update_dashboard or (lambda _: None)
            reset_fn = reset_dashboard or (lambda: None)

            chat.register_tool(tool_update_dashboard(self._data_source, update_fn))
            chat.register_tool(tool_reset_dashboard(reset_fn))

        if "query" in tools:
            chat.register_tool(tool_query(self._data_source))

        return chat

    def console(
        self,
        *,
        new: bool = False,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = "query",
        **kwargs,
    ) -> None:
        """
        Launch an interactive console chat with the data.

        This method provides a REPL (Read-Eval-Print Loop) interface for
        chatting with your data from the command line. The console session
        persists by default, so you can exit and return to continue your
        conversation.

        Parameters
        ----------
        new
            If True, creates a new chat client and starts a fresh conversation.
            If False (default), continues the conversation from the previous
            console session.
        tools
            Which tools to include: "update", "query", or both. Can be:
            - A single tool string: `"update"` or `"query"`
            - A tuple of tools: `("update", "query")`
            - `None` or `()` to skip adding any tools
            - If not provided (default), defaults to `("query",)` only for
              privacy (prevents the LLM from accessing data values)
            Ignored if `new=False` and a console session already exists.
        **kwargs
            Additional arguments passed to the `client()` method when creating a
            new client.

        Examples
        --------
        ```python
        from querychat import QueryChat
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        qc = QueryChat(df, "my_data")

        # Start console (query tool only by default)
        qc.console()

        # Start fresh console with all tools (using tuple)
        qc.console(new=True, tools=("update", "query"))

        # Start fresh console with all tools (using single string for one tool)
        qc.console(new=True, tools="query")

        # Continue previous console session
        qc.console()  # picks up where you left off
        ```

        """
        tools = normalize_tools(tools, default=("query",))

        if new or self._client_console is None:
            self._client_console = self.client(tools=tools, **kwargs)

        self._client_console.console()

    @property
    def system_prompt(self) -> str:
        """
        Get the system prompt.

        Returns
        -------
        :
            The system prompt string.

        """
        return self._system_prompt.render(self.tools)

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

    QueryChat enables natural language interaction with your data through an
    LLM-powered chat interface. It can be used in Shiny applications, as a
    standalone chat client, or in an interactive console.

    Examples
    --------
    **Basic Shiny app:**
    ```python
    from querychat import QueryChat

    qc = QueryChat(my_dataframe, "my_data")
    qc.app()
    ```

    **Standalone chat client:**
    ```python
    from querychat import QueryChat
    import pandas as pd

    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    qc = QueryChat(df, "my_data")

    # Get a chat client with all tools
    client = qc.client()
    response = client.chat("What's the average of column a?")

    # Start an interactive console chat
    qc.console()
    ```

    **Privacy-focused mode:** Only allow dashboard filtering, ensuring the LLM
    can't see any raw data.
    ```python
    qc = QueryChat(df, "my_data", tools="update")
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
    tools
        Which querychat tools to include in the chat client by default. Can be:
        - A single tool string: `"update"` or `"query"`
        - A tuple of tools: `("update", "query")`
        - `None` or `()` to disable all tools

        Default is `("update", "query")` (both tools enabled).

        Set to `"update"` to prevent the LLM from accessing data values, only
        allowing dashboard filtering without answering questions.

        The tools can be overridden per-client by passing a different `tools`
        parameter to the `.client()` method.
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
            client=self.client,
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
    def sql(self, query: None = None) -> str | None: ...

    @overload
    def sql(self, query: str) -> bool: ...

    def sql(self, query: Optional[str] = None) -> str | None | bool:
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
            (or `None` if no query has been set). If a `query` is provided,
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


def normalize_tools(
    tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None | MISSING_TYPE,
    default: tuple[TOOL_GROUPS, ...] | None,
) -> tuple[TOOL_GROUPS, ...] | None:
    if tools is None or tools == ():
        return None
    elif isinstance(tools, MISSING_TYPE):
        return default
    elif isinstance(tools, str):
        return (tools,)
    elif isinstance(tools, tuple):
        return tools
    else:
        # Convert any other sequence to tuple
        return tuple(tools)
