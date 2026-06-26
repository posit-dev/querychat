from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal, Optional, overload

from narwhals.stable.v1.typing import IntoDataFrameT, IntoFrameT, IntoLazyFrameT
from shiny.express._stub_session import ExpressStubSession
from shiny.session import get_current_session

from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui

from ._icons import bs_icon
from ._querychat_base import DEFAULT_TOOLS, TOOL_GROUPS, QueryChatBase, resolve_client
from ._shiny_module import ServerValues, mod_server, mod_ui
from ._utils import MISSING, MISSING_TYPE, as_narwhals
from ._viz_utils import has_viz_tool

if TYPE_CHECKING:
    from pathlib import Path

    import chatlas
    import ibis
    import narwhals.stable.v1 as nw
    import sqlalchemy
    from narwhals.stable.v1.typing import IntoFrame

    from ._data_dict import DataDict
    from ._table_accessor import TableAccessor


class QueryChat(QueryChatBase[IntoFrameT]):
    """
    Create a QueryChat instance for Shiny applications.

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
    qc = QueryChat(df, "my_data", tools="filter")
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
        - A single tool string: `"filter"` or `"query"`
        - A tuple of tools: `("filter", "query", "visualize")`
        - `None` or `()` to disable all tools

        Default is `("filter", "query")`. The visualization tool (`"visualize"`)
        can be opted into by including it in the tuple.

        Pass only `"filter"` to restrict the LLM to dashboard filtering,
        omitting both the `"query"` and `"visualize"` tools so the LLM
        cannot access or display any raw data values.

        The legacy name `"update"` is still accepted as an alias for `"filter"`.

        The tools can be overridden per-client by passing a different `tools`
        parameter to the `.client()` method.
    data_dict
        A :class:`~querychat.DataDict` instance, or a path (``str`` or
        ``pathlib.Path``) to a YAML file, that provides rich per-table and
        per-column metadata. When set, documented columns use the dict's
        ``values``, ``range``, and ``description`` fields instead of querying
        the data source for statistics, which speeds up schema generation and
        improves LLM context. Supersedes ``data_description``.
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
    categorical_threshold
        Threshold for determining if a column is categorical based on number of
        unique values.
    data_description
        Optional plain-text or Markdown description of the data, as a string or
        file path. Superseded by ``data_dict`` for new code.

    """

    @overload
    def __init__(
        self: QueryChat[Any],
        data_source: None = None,
        table_name: str | None = None,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("filter", "query"),
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[ibis.Table],
        data_source: ibis.Table,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[IntoLazyFrameT],
        data_source: IntoLazyFrameT,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[IntoDataFrameT],
        data_source: IntoDataFrameT,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChat[nw.DataFrame],
        data_source: sqlalchemy.Engine,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
    ) -> None: ...

    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine | ibis.Table | None = None,
        table_name: str | None = None,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
    ):
        super().__init__(
            data_source,
            table_name,
            greeting=greeting,
            client=client,
            tools=tools,
            data_description=data_description,
            data_dict=data_dict,
            categorical_threshold=categorical_threshold,
            extra_instructions=extra_instructions,
            prompt_template=prompt_template,
        )
        self.id = id or (f"querychat_{table_name}" if table_name else "querychat")

    def app(
        self, *, bookmark_store: Literal["url", "server", "disable"] = "url"
    ) -> App:
        """
        Quickly chat with a dataset.

        Creates a Shiny app with a chat sidebar and data view -- providing a
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
        self._require_initialized("app")
        enable_bookmarking = bookmark_store != "disable"
        first_table_name = next(iter(self._data_sources))

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
                            ui.div(
                                ui.output_ui("ui_reset", inline=True),
                                class_="ms-auto",
                            ),
                            class_="hstack gap-3 w-100",
                        ),
                    ),
                    ui.output_ui("sql_output"),
                    fill=False,
                    style="max-height: 33%;",
                ),
                ui.card(
                    ui.card_header(
                        bs_icon("table"),
                        " Data — ",
                        ui.output_text("data_card_header_text", inline=True),
                    ),
                    ui.output_data_frame("dt"),
                ),
                title=ui.span("querychat with ", ui.code(first_table_name)),
                class_="bslib-page-dashboard",
                fillable=True,
            )

        def app_server(input: Inputs, output: Outputs, session: Session):
            self._mark_server_initialized()
            if enable_bookmarking:
                session.bookmark.exclude.extend(["reset_query", "sql_editor"])
            vals = mod_server(
                self.id,
                data_sources=dict(self._data_sources),
                executor=self._require_query_executor("server"),
                greeting=self.greeting,
                client=self._create_session_client,
                enable_bookmarking=enable_bookmarking,
                tools=self.tools,
                greeter=self.greeter,
                greeting_base=None,
            )

            @reactive.calc
            def active_table_name() -> str:
                return vals.current_table() or first_table_name

            @render.text
            def data_card_header_text():
                return active_table_name()

            @render.text
            def query_title():
                return vals.table(active_table_name()).title() or "SQL Query"

            @render.ui
            def ui_reset():
                req(vals.table(active_table_name()).sql())
                return ui.input_action_button(
                    "reset_query",
                    "Reset Query",
                    class_="btn btn-outline-danger btn-sm lh-1 ms-auto",
                )

            @reactive.effect
            @reactive.event(input.reset_query)
            def _():
                name = active_table_name()
                # TableAccessor is read-only; mutation requires direct TableState access
                vals._tables[name].sql.set(None)
                vals._tables[name].title.set(None)

            @render.data_frame
            def dt():
                # Collect lazy sources (LazyFrame, Ibis Table) to eager DataFrame
                return as_narwhals(vals.table(active_table_name()).df())

            def sql_text_for_editor(name: str) -> str:
                return vals.table(name).sql() or f"SELECT * FROM {name}"

            @render.ui
            def sql_output():
                name = active_table_name()
                with reactive.isolate():
                    sql_text = sql_text_for_editor(name)
                return ui.input_code_editor(
                    "sql_editor",
                    value=sql_text,
                    language="sql",
                    line_numbers=False,
                    height="auto",
                )

            @reactive.effect
            def sync_sql_editor():
                name = active_table_name()
                ui.update_code_editor("sql_editor", value=sql_text_for_editor(name))

            @reactive.effect
            @reactive.event(input.sql_editor)
            def _():
                name = active_table_name()
                query = input.sql_editor()
                default_query = f"SELECT * FROM {name}"
                vals._tables[name].sql.set(
                    query if query and query.strip() != default_query else None
                )

        return App(app_ui, app_server, bookmark_store=bookmark_store)

    def sidebar(
        self,
        *,
        width: int = 400,
        height: str = "100%",
        fillable: bool = True,
        id: Optional[str] = None,
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
        id
            Optional ID for the QueryChat instance. If not provided,
            will use the ID provided at initialization.
        **kwargs
            Additional arguments passed to `shiny.ui.sidebar()`.

        Returns
        -------
        :
            A sidebar UI component.

        """
        return ui.sidebar(
            self.ui(id=id),
            width=width,
            height=height,
            fillable=fillable,
            class_="querychat-sidebar",
            **kwargs,
        )

    def ui(self, *, id: Optional[str] = None, **kwargs):
        """
        Create the UI for the querychat component.

        Parameters
        ----------
        id
            Optional ID for the QueryChat instance. If not provided,
            will use the ID provided at initialization.
        **kwargs
            Additional arguments to pass to `shinychat.chat_ui()`.

        Returns
        -------
        :
            A UI component.

        """
        return mod_ui(
            id or self.id,
            preload_viz=has_viz_tool(self.tools),
            greeting=self.greeting,
            **kwargs,
        )

    def server(
        self,
        *,
        client: str | chatlas.Chat | MISSING_TYPE = MISSING,
        enable_bookmarking: bool = False,
        id: Optional[str] = None,
    ) -> ServerValues[IntoFrameT]:
        """
        Initialize Shiny server logic.

        This method is intended for use in Shiny Code mode, where the user must
        explicitly call `.server()` within the Shiny server function. In Shiny
        Express mode, you can use `querychat.express.QueryChat` instead
        of `querychat.QueryChat`, which calls `.server()` automatically.

        Parameters
        ----------
        client
            Optional chat client to use for this session. If provided, overrides
            any client set at initialization time for this call only. This is useful
            for the deferred pattern where the client cannot be created at
            initialization time (e.g., when using Posit Connect managed OAuth
            credentials that require session access).
        enable_bookmarking
            Whether to enable bookmarking for the querychat module.
        id
            Optional module ID for the QueryChat instance. If not provided,
            will use the ID provided at initialization. This must match the ID
            used in the `.ui()` or `.sidebar()` methods.

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

        self._require_initialized("server")
        resolved_client: chatlas.Chat | None = (
            None if isinstance(client, MISSING_TYPE) else resolve_client(client)
        )

        def create_session_client(**kwargs) -> chatlas.Chat:
            return self._create_session_client(base=resolved_client, **kwargs)

        self._mark_server_initialized()
        return mod_server(
            id or self.id,
            data_sources=dict(self._data_sources),
            executor=self._require_query_executor("server"),
            greeting=self.greeting,
            client=create_session_client,
            enable_bookmarking=enable_bookmarking,
            tools=self.tools,
            greeter=self.greeter,
            greeting_base=resolved_client,
        )


class QueryChatExpress(QueryChatBase[IntoFrameT]):
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
        SQLAlchemy engine containing the table to query against. Can be ``None``
        for deferred binding (set via the ``data_source`` property before the
        real session starts).
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
    data_dict
        A :class:`~querychat.DataDict` instance, or a path (``str`` or
        ``pathlib.Path``) to a YAML file, that provides rich per-table and
        per-column metadata. When set, documented columns use the dict's
        ``values``, ``range``, and ``description`` fields instead of querying
        the data source for statistics, which speeds up schema generation and
        improves LLM context. Supersedes ``data_description``.
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
    categorical_threshold
        Threshold for determining if a column is categorical based on number of
        unique values.
    data_description
        Optional plain-text or Markdown description of the data, as a string or
        file path. Superseded by ``data_dict`` for new code.

    """

    # Class-level cache for bookmarking settings detected during stub session
    _bookmarking_settings: ClassVar[dict[str, bool]] = {}

    @overload
    def __init__(
        self: QueryChatExpress[Any],
        data_source: None = None,
        table_name: str | None = None,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = ("filter", "query"),
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
        enable_bookmarking: Literal["auto", True, False] = "auto",
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChatExpress[ibis.Table],
        data_source: ibis.Table,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
        enable_bookmarking: Literal["auto", True, False] = "auto",
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChatExpress[IntoLazyFrameT],
        data_source: IntoLazyFrameT,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
        enable_bookmarking: Literal["auto", True, False] = "auto",
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChatExpress[IntoDataFrameT],
        data_source: IntoDataFrameT,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
        enable_bookmarking: Literal["auto", True, False] = "auto",
    ) -> None: ...

    @overload
    def __init__(
        self: QueryChatExpress[nw.DataFrame],
        data_source: sqlalchemy.Engine,
        table_name: str,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
        enable_bookmarking: Literal["auto", True, False] = "auto",
    ) -> None: ...

    def __init__(
        self,
        data_source: IntoFrame | sqlalchemy.Engine | ibis.Table | None = None,
        table_name: str | None = None,
        *,
        id: Optional[str] = None,
        greeting: Optional[str | Path] = None,
        client: Optional[str | chatlas.Chat] = None,
        tools: TOOL_GROUPS | tuple[TOOL_GROUPS, ...] | None = DEFAULT_TOOLS,
        data_dict: DataDict | str | Path | None = None,
        extra_instructions: Optional[str | Path] = None,
        prompt_template: Optional[str | Path] = None,
        categorical_threshold: int = 20,
        data_description: Optional[str | Path] = None,
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
            greeting=greeting,
            client=client,
            tools=tools,
            data_description=data_description,
            data_dict=data_dict,
            categorical_threshold=categorical_threshold,
            extra_instructions=extra_instructions,
            prompt_template=prompt_template,
        )
        self.id = id or (f"querychat_{table_name}" if table_name else "querychat")

        # Determine bookmarking setting
        # During stub session: detect from app_opts and cache in class variable
        # During real session: retrieve from class variable
        enable: bool
        if enable_bookmarking == "auto":
            if isinstance(session, ExpressStubSession):
                store = session.app_opts.get("bookmark_store", "disable")
                enable = store != "disable"
                # Cache for the real session
                QueryChatExpress._bookmarking_settings[self.id] = enable
            else:
                # Retrieve and clean up (pop prevents memory accumulation)
                enable = QueryChatExpress._bookmarking_settings.pop(self.id, False)
        else:
            enable = enable_bookmarking

        self._enable_bookmarking = enable
        self._vals: ServerValues[IntoFrameT] | None = None

    def _ensure_server_started(self) -> None:
        """
        Start the Shiny module server if not already started.

        Called lazily from ui()/sidebar() and the reactive accessors so that
        module-level add_table() calls (which happen after __init__ but before
        sidebar()/ui()) can complete before server initialization locks the
        table set.
        """
        if self._server_initialized:
            return
        session = get_current_session()
        if isinstance(session, ExpressStubSession):
            return
        if not self._data_sources:
            return
        self._require_initialized("_ensure_server_started")
        self._mark_server_initialized()
        self._vals = mod_server(
            self.id,
            data_sources=dict(self._data_sources),
            executor=self._require_query_executor("_ensure_server_started"),
            greeting=self.greeting,
            client=self._create_session_client,
            enable_bookmarking=self._enable_bookmarking,
            tools=self.tools,
            greeter=self.greeter,
            greeting_base=None,
        )

    def sidebar(
        self,
        *,
        width: int = 400,
        height: str = "100%",
        fillable: bool = True,
        id: Optional[str] = None,
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
        id
            Optional ID for the QueryChat instance. If not provided,
            will use the ID provided at initialization.
        **kwargs
            Additional arguments passed to `shiny.ui.sidebar()`.

        Returns
        -------
        :
            A sidebar UI component.

        """
        return ui.sidebar(
            self.ui(id=id),
            width=width,
            height=height,
            fillable=fillable,
            class_="querychat-sidebar",
            **kwargs,
        )

    def ui(self, *, id: Optional[str] = None, **kwargs):
        """
        Create the UI for the querychat component.

        Parameters
        ----------
        id
            Optional ID for the QueryChat instance. If not provided,
            will use the ID provided at initialization.
        **kwargs
            Additional arguments to pass to `shinychat.chat_ui()`.

        Returns
        -------
        :
            A UI component.

        """
        result = mod_ui(
            id or self.id,
            preload_viz=has_viz_tool(self.tools),
            greeting=self.greeting,
            **kwargs,
        )
        self._ensure_server_started()
        return result

    def _require_vals(self) -> ServerValues[IntoFrameT]:
        self._ensure_server_started()
        if self._vals is None:
            raise RuntimeError(
                "QueryChat server is not initialized. "
                "Ensure add_table() is called and sidebar()/ui() has been rendered."
            )
        return self._vals

    def df(self) -> IntoFrameT:
        """
        Reactively read the current filtered data frame that is in effect.

        Returns
        -------
        :
            The current filtered data frame, in the same format as the original
            data source (e.g., polars DataFrame, Polars LazyFrame, Ibis Table).
            If no query has been set, returns the unfiltered data from the
            data source.

        """
        return self._require_vals().df()

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
            return self._require_vals().sql()
        else:
            return self._require_vals().sql.set(query)

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
            return self._require_vals().title()
        else:
            return self._require_vals().title.set(value)

    def table(self, name: str) -> TableAccessor:
        """
        Get a per-table accessor with reactive state.

        Parameters
        ----------
        name
            Table name (must match a name passed to ``add_table()``).

        Returns
        -------
        TableAccessor
            Accessor with ``df()``, ``sql()``, and ``title()`` backed by
            per-session reactive state.

        Examples
        --------
        ```python
        from querychat.express import QueryChat
        from shiny.express import render

        qc = QueryChat(orders, "orders")
        qc.add_table(customers, "customers")
        qc.sidebar()


        @render.data_frame
        def orders_table():
            return qc.table("orders").df()


        @render.data_frame
        def customers_table():
            return qc.table("customers").df()
        ```

        """
        return self._require_vals().table(name)

    def current_table(self) -> str | None:
        """
        Reactively read the name of the most recently queried table.

        Returns ``None`` if no query has run yet in this session. Useful for
        auto-switching a tabbed UI to the active table.

        Returns
        -------
        str or None
            Table name, or ``None``.

        """
        return self._require_vals().current_table()
