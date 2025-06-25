from __future__ import annotations

import re
import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol, Union

import chatlas
import chevron
import narwhals as nw
import pandas as pd
import sqlalchemy
from narwhals.typing import IntoFrame
from shiny import Inputs, Outputs, Session, module, reactive, ui

if TYPE_CHECKING:
    import pandas as pd
    from narwhals.typing import IntoFrame

from .datasource import DataFrameSource, DataSource, SQLAlchemySource


class CreateChatCallback(Protocol):
    def __call__(self, system_prompt: str) -> chatlas.Chat: ...


class QueryChatConfig:
    """
    Configuration class for querychat.
    """

    def __init__(
        self,
        data_source: DataSource,
        system_prompt: str,
        greeting: Optional[str],
        create_chat_callback: CreateChatCallback,
    ):
        self.data_source = data_source
        self.system_prompt = system_prompt
        self.greeting = greeting
        self.create_chat_callback = create_chat_callback


class QueryChat:
    """
    An object representing a query chat session. This is created within a Shiny
    server function or Shiny module server function by using
    `querychat.server()`. Use this object to bridge the chat interface with the
    rest of the Shiny app, for example, by displaying the filtered data.
    """

    def __init__(
        self,
        chat: chatlas.Chat,
        sql: Callable[[], str],
        title: Callable[[], Union[str, None]],
        df: Callable[[], pd.DataFrame],
    ):
        """
        Initialize a QueryChat object.

        Args:
            chat: The chat object for the session
            sql: Reactive that returns the current SQL query
            title: Reactive that returns the current title
            df: Reactive that returns the filtered data frame

        """
        self._chat = chat
        self._sql = sql
        self._title = title
        self._df = df

    def chat(self) -> chatlas.Chat:
        """
        Get the chat object for this session.

        Returns:
            The chat object

        """
        return self._chat

    def sql(self) -> str:
        """
        Reactively read the current SQL query that is in effect.

        Returns:
            The current SQL query as a string, or `""` if no query has been set.

        """
        return self._sql()

    def title(self) -> Union[str, None]:
        """
        Reactively read the current title that is in effect. The title is a
        short description of the current query that the LLM provides to us
        whenever it generates a new SQL query. It can be used as a status string
        for the data dashboard.

        Returns:
            The current title as a string, or `None` if no title has been set
            due to no SQL query being set.

        """
        return self._title()

    def df(self) -> pd.DataFrame:
        """
        Reactively read the current filtered data frame that is in effect.

        Returns:
            The current filtered data frame as a pandas DataFrame. If no query
            has been set, this will return the unfiltered data frame from the
            data source.

        """
        return self._df()

    def __getitem__(self, key: str) -> Any:
        """
        Allow access to configuration parameters like a dictionary. For
        backwards compatibility only; new code should use the attributes
        directly instead.
        """
        if key == "chat":  # noqa: SIM116
            return self.chat
        elif key == "sql":
            return self.sql
        elif key == "title":
            return self.title
        elif key == "df":
            return self.df

        raise KeyError(
            f"`QueryChat` does not have a key `'{key}'`. "
            "Use the attributes `chat`, `sql`, `title`, or `df` instead.",
        )


from .datasource import DataFrameSource, DataSource, SQLAlchemySource


class CreateChatCallback(Protocol):
    def __call__(self, system_prompt: str) -> chatlas.Chat: ...


class QueryChatConfig:
    """
    Configuration class for querychat.
    """

    def __init__(
        self,
        data_source: DataSource,
        system_prompt: str,
        greeting: Optional[str],
        create_chat_callback: CreateChatCallback,
    ):
        self.data_source = data_source
        self.system_prompt = system_prompt
        self.greeting = greeting
        self.create_chat_callback = create_chat_callback


class QueryChat:
    """
    An object representing a query chat session. This is created within a Shiny
    server function or Shiny module server function by using
    `querychat.server()`. Use this object to bridge the chat interface with the
    rest of the Shiny app, for example, by displaying the filtered data.
    """

    def __init__(
        self,
        chat: chatlas.Chat,
        sql: Callable[[], str],
        title: Callable[[], Union[str, None]],
        df: Callable[[], pd.DataFrame],
    ):
        """
        Initialize a QueryChat object.

        Args:
            chat: The chat object for the session
            sql: Reactive that returns the current SQL query
            title: Reactive that returns the current title
            df: Reactive that returns the filtered data frame

        """
        self._chat = chat
        self._sql = sql
        self._title = title
        self._df = df

    def chat(self) -> chatlas.Chat:
        """
        Get the chat object for this session.

        Returns:
            The chat object

        """
        return self._chat

    def sql(self) -> str:
        """
        Reactively read the current SQL query that is in effect.

        Returns:
            The current SQL query as a string, or `""` if no query has been set.

        """
        return self._sql()

    def title(self) -> Union[str, None]:
        """
        Reactively read the current title that is in effect. The title is a
        short description of the current query that the LLM provides to us
        whenever it generates a new SQL query. It can be used as a status string
        for the data dashboard.

        Returns:
            The current title as a string, or `None` if no title has been set
            due to no SQL query being set.

        """
        return self._title()

    def df(self) -> pd.DataFrame:
        """
        Reactively read the current filtered data frame that is in effect.

        Returns:
            The current filtered data frame as a pandas DataFrame. If no query
            has been set, this will return the unfiltered data frame from the
            data source.

        """
        return self._df()

    def __getitem__(self, key: str) -> Any:
        """
        Allow access to configuration parameters like a dictionary. For
        backwards compatibility only; new code should use the attributes
        directly instead.
        """
        return {
            "chat": self.chat,
            "sql": self.sql,
            "title": self.title,
            "df": self.df,
        }.get(key)


def system_prompt(
    data_source: DataSource,
    data_description: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    categorical_threshold: int = 10,
) -> str:
    """
    Create a system prompt for the chat model based on a data source's schema
    and optional additional context and instructions.

    Parameters
    ----------
    data_source : DataSource
        A data source to generate schema information from
    data_description : str, optional
        Optional description of the data, in plain text or Markdown format
    extra_instructions : str, optional
        Optional additional instructions for the chat model, in plain text or
        Markdown format
    categorical_threshold : int, default=10
        Threshold for determining if a column is categorical based on number of
        unique values

    Returns
    -------
    str
        The system prompt for the chat model.

    """
    # Read the prompt file
    prompt_path = Path(__file__).parent / "prompt" / "prompt.md"
    prompt_text = prompt_path.read_text()

    return chevron.render(
        prompt_text,
        {
            "db_engine": data_source.db_engine,
            "schema": data_source.get_schema(
                categorical_threshold=categorical_threshold,
            ),
            "data_description": data_description,
            "extra_instructions": extra_instructions,
        },
    )


def df_to_html(df: IntoFrame, maxrows: int = 5) -> str:
    """
    Convert a DataFrame to an HTML table for display in chat.

    Parameters
    ----------
    df : IntoFrame
        The DataFrame to convert
    maxrows : int, default=5
        Maximum number of rows to display

    Returns
    -------
    str
        HTML string representation of the table

    """
    ndf = nw.from_native(df)
    df_short = nw.from_native(df).head(maxrows)

    # Generate HTML table
    table_html = df_short.to_pandas().to_html(
        index=False,
        classes="table table-striped",
    )

    # Add note about truncated rows if needed
    if len(df_short) != len(ndf):
        rows_notice = (
            f"\n\n(Showing only the first {maxrows} rows out of {len(ndf)}.)\n"
        )
    else:
        rows_notice = ""

    return table_html + rows_notice


def init(
    data_source: IntoFrame | sqlalchemy.Engine,
    table_name: str,
    greeting: Optional[str] = None,
    data_description: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    create_chat_callback: Optional[CreateChatCallback] = None,
    system_prompt_override: Optional[str] = None,
) -> QueryChatConfig:
    """
    Initialize querychat with any compliant data source.

    Parameters
    ----------
    data_source : IntoFrame | sqlalchemy.Engine
        Either a Narwhals-compatible data frame (e.g., Polars or Pandas) or a
        SQLAlchemy engine containing the table to query against.
    table_name : str
        If a data_source is a data frame, a name to use to refer to the table in
        SQL queries (usually the variable name of the data frame, but it doesn't
        have to be). If a data_source is a SQLAlchemy engine, the table_name is
        the name of the table in the database to query against.
    greeting : str, optional
        A string in Markdown format, containing the initial message
    data_description : str, optional
        Description of the data in plain text or Markdown
    extra_instructions : str, optional
        Additional instructions for the chat model
    create_chat_callback : CreateChatCallback, optional
        A function that creates a chat object
    system_prompt_override : str, optional
        A custom system prompt to use instead of the default

    Returns
    -------
    QueryChatConfig
        A QueryChatConfig object that can be passed to server()

    """
    # Validate table name (must begin with letter, contain only letters, numbers, underscores)
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
        raise ValueError(
            "Table name must begin with a letter and contain only letters, numbers, and underscores",
        )

    data_source_obj: DataSource
    if isinstance(data_source, sqlalchemy.Engine):
        data_source_obj = SQLAlchemySource(data_source, table_name)
    else:
        data_source_obj = DataFrameSource(
            nw.from_native(data_source).to_pandas(),
            table_name,
        )
    # Process greeting
    if greeting is None:
        print(
            "Warning: No greeting provided; the LLM will be invoked at conversation start to generate one. "
            "For faster startup, lower cost, and determinism, please save a greeting and pass it to init().",
            file=sys.stderr,
        )

    # Create the system prompt, or use the override
    _system_prompt = system_prompt_override or system_prompt(
        data_source_obj,
        data_description,
        extra_instructions,
    )

    # Default chat function if none provided
    create_chat_callback = create_chat_callback or partial(
        chatlas.ChatOpenAI,
        model="gpt-4.1",
    )

    return QueryChatConfig(
        data_source=data_source_obj,
        system_prompt=_system_prompt,
        greeting=greeting,
        create_chat_callback=create_chat_callback,
    )


@module.ui
def mod_ui() -> ui.TagList:
    """
    Create the UI for the querychat component.

    Parameters
    ----------
    id : str
        The module ID

    Returns
    -------
    ui.TagList
        A UI component.

    """
    # Include CSS
    css_path = Path(__file__).parent / "static" / "css" / "styles.css"

    return ui.TagList(
        ui.include_css(css_path),
        # Chat interface goes here - placeholder for now
        # This would need to be replaced with actual chat UI components
        ui.chat_ui("chat"),
    )


def sidebar(id: str, width: int = 400, height: str = "100%", **kwargs) -> ui.Sidebar:
    """
    Create a sidebar containing the querychat UI.

    Parameters
    ----------
    id : str
        The module ID.
    width : int, default=400
        Width of the sidebar in pixels.
    height : str, default="100%"
        Height of the sidebar.
    **kwargs
        Additional arguments to pass to the sidebar component.

    Returns
    -------
    ui.Sidebar
        A sidebar UI component.

    """
    return ui.sidebar(
        mod_ui(id),
        width=width,
        height=height,
        **kwargs,
    )


@module.server
def mod_server(  # noqa: D417
    input: Inputs,
    output: Outputs,
    session: Session,
    querychat_config: QueryChatConfig,
) -> QueryChat:
    """
    Initialize the querychat server.

    Parameters
    ----------
    querychat_config : QueryChatConfig
        Configuration object from init().

    Returns
    -------
    dict[str, Any]
        A dictionary with reactive components:
            - sql: A reactive that returns the current SQL query.
            - title: A reactive that returns the current title.
            - df: A reactive that returns the filtered data frame.
            - chat: The chat object.

    """

    @reactive.effect
    def _():
        # This will be triggered when the module is initialized
        # Here we would set up the chat interface, initialize the chat model, etc.
        pass

    # Extract config parameters
    data_source = querychat_config.data_source
    system_prompt = querychat_config.system_prompt
    greeting = querychat_config.greeting
    create_chat_callback = querychat_config.create_chat_callback

    # Reactive values to store state
    current_title = reactive.value[Union[str, None]](None)
    current_query = reactive.value("")

    @reactive.calc
    def filtered_df():
        if current_query.get() == "":
            return data_source.get_data()
        else:
            return data_source.execute_query(current_query.get())

    # This would handle appending messages to the chat UI
    async def append_output(text):
        async with chat_ui.message_stream_context() as msgstream:
            await msgstream.append(text)

    # The function that updates the dashboard with a new SQL query
    async def update_dashboard(query: str, title: str):
        """
        Modify the data presented in the data dashboard, based on the given SQL query,
        and also updates the title.

        Parameters
        ----------
        query : str
            A DuckDB SQL query; must be a SELECT statement.
        title : str
            A title to display at the top of the data dashboard, summarizing the intent of the SQL query.

        """
        await append_output(f"\n```sql\n{query}\n```\n\n")

        try:
            # Try the query to see if it errors
            data_source.execute_query(query)
        except Exception as e:
            error_msg = str(e)
            await append_output(f"> Error: {error_msg}\n\n")
            raise e

        if query is not None:
            current_query.set(query)
        if title is not None:
            current_title.set(title)

    # Function to perform a SQL query and return results as JSON
    async def query(query: str):
        """
        Perform a SQL query on the data, and return the results as JSON.

        Parameters
        ----------
        query
            A DuckDB SQL query; must be a SELECT statement.

        """
        await append_output(f"\n```sql\n{query}\n```\n\n")

        try:
            result_df = data_source.execute_query(query)
        except Exception as e:
            error_msg = str(e)
            await append_output(f"> Error: {error_msg}\n\n")
            raise e

        tbl_html = df_to_html(result_df, maxrows=5)
        await append_output(f"{tbl_html}\n\n")

        return result_df.to_json(orient="records")

    chat_ui = ui.Chat("chat")

    # Initialize the chat with the system prompt
    # This is a placeholder - actual implementation would depend on chatlas
    chat = create_chat_callback(system_prompt=system_prompt)
    chat.register_tool(update_dashboard)
    chat.register_tool(query)

    # Register tools with the chat
    # This is a placeholder - actual implementation would depend on chatlas
    # chat.register_tool("update_dashboard", update_dashboard)
    # chat.register_tool("query", query)

    # Add greeting if provided
    if greeting and any(len(g) > 0 for g in greeting.split("\n")):
        # Display greeting in chat UI
        pass
    else:
        # Generate greeting using the chat model
        pass

    # Handle user input
    @chat_ui.on_user_submit
    async def _(user_input: str):
        stream = await chat.stream_async(user_input, echo="none")
        await chat_ui.append_message_stream(stream)

    @reactive.effect
    async def greet_on_startup():
        if querychat_config.greeting:
            await chat_ui.append_message(greeting)
        elif querychat_config.greeting is None:
            stream = await chat.stream_async(
                "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list.",
                echo="none",
            )
            await chat_ui.append_message_stream(stream)

    # Return the interface for other components to use
    return QueryChat(chat, current_query.get, current_title.get, filtered_df)
