from __future__ import annotations

import sys
import os
import re
import pandas as pd
import duckdb
import json
from functools import partial
from typing import List, Dict, Any, Callable, Optional, Union, Protocol

import chatlas
from htmltools import TagList, tags, HTML
from shiny import module, reactive, ui, Inputs, Outputs, Session
import narwhals as nw
from narwhals.typing import IntoFrame


def system_prompt(
    df: IntoFrame,
    table_name: str,
    data_description: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    categorical_threshold: int = 10,
) -> str:
    """
    Create a system prompt for the chat model based on a DataFrame's
    schema and optional context and instructions.

    Parameters
    ----------
    df : IntoFrame
        Input data to generate schema information from.
    table_name : str
        Name of the table to be used in SQL queries.
    data_description : str, optional
        Description of the data, in plain text or Markdown format.
    extra_instructions : str, optional
        Additional instructions for the chat model, in plain text or Markdown format.
    categorical_threshold : int, default=10
        Maximum number of unique values for a text column to be considered categorical.

    Returns
    -------
    str
        The system prompt for the chat model.
    """
    schema = df_to_schema(df, table_name, categorical_threshold)

    # Read the prompt file
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt", "prompt.md")
    with open(prompt_path, "r") as f:
        prompt_text = f.read()

    # Simple template replacement (a more robust template engine could be used)
    if data_description:
        data_description_section = (
            "Additional helpful info about the data:\n\n"
            "<data_description>\n"
            f"{data_description}\n"
            "</data_description>"
        )
    else:
        data_description_section = ""

    # Replace variables in the template
    prompt_text = prompt_text.replace("{{schema}}", schema)
    prompt_text = prompt_text.replace("{{data_description}}", data_description_section)
    prompt_text = prompt_text.replace(
        "{{extra_instructions}}", extra_instructions or ""
    )

    return prompt_text


def df_to_schema(df: IntoFrame, table_name: str, categorical_threshold: int) -> str:
    """
    Convert a DataFrame schema to a string representation for the system prompt.

    Parameters
    ----------
    df : IntoFrame
        The DataFrame to extract schema from
    table_name : str
        The name of the table in SQL queries
    categorical_threshold : int
        The maximum number of unique values for a text column to be considered categorical

    Returns
    -------
    str
        A string containing the schema information.
    """

    ndf = nw.from_native(df)

    schema = [f"Table: {table_name}", "Columns:"]

    for column in ndf.columns:
        # Map pandas dtypes to SQL-like types
        dtype = ndf[column].dtype
        if dtype.is_integer():
            sql_type = "INTEGER"
        elif dtype.is_float():
            sql_type = "FLOAT"
        elif dtype == nw.Boolean:
            sql_type = "BOOLEAN"
        elif dtype == nw.Datetime:
            sql_type = "TIME"
        elif dtype == nw.Date:
            sql_type = "DATE"
        else:
            sql_type = "TEXT"

        column_info = [f"- {column} ({sql_type})"]

        # For TEXT columns, check if they're categorical
        if sql_type == "TEXT":
            unique_values = ndf[column].drop_nulls().unique()
            if unique_values.len() <= categorical_threshold:
                categories = unique_values.to_list()
                categories_str = ", ".join([f"'{c}'" for c in categories])
                column_info.append(f"  Categorical values: {categories_str}")

        # For numeric columns, include range
        elif sql_type in ["INTEGER", "FLOAT", "DATE", "TIME"]:
            rng = ndf[column].min(), ndf[column].max()
            if rng[0] is None and rng[1] is None:
                column_info.append("  Range: NULL to NULL")
            else:
                column_info.append(f"  Range: {rng[0]} to {rng[1]}")

        schema.extend(column_info)

    return "\n".join(schema)


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
    table_html = df_short.to_pandas().to_html(index=False, classes="table table-striped")

    # Add note about truncated rows if needed
    if len(df_short) != len(ndf):
        rows_notice = (
            f"\n\n(Showing only the first {maxrows} rows out of {len(ndf)}.)\n"
        )
    else:
        rows_notice = ""

    return table_html + rows_notice


class CreateChatCallback(Protocol):
    def __call__(self, system_prompt: str) -> chatlas.Chat: ...


class QueryChatConfig:
    """
    Configuration class for querychat.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        conn: duckdb.DuckDBPyConnection,
        system_prompt: str,
        greeting: Optional[str],
        create_chat_callback: CreateChatCallback,
    ):
        self.df = df
        self.conn = conn
        self.system_prompt = system_prompt
        self.greeting = greeting
        self.create_chat_callback = create_chat_callback


def init(
    df: pd.DataFrame,
    table_name: str,
    greeting: Optional[str] = None,
    data_description: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    create_chat_callback: Optional[CreateChatCallback] = None,
    system_prompt_override: Optional[str] = None,
) -> QueryChatConfig:
    """
    Call this once outside of any server function to initialize querychat.

    Parameters
    ----------
    df : pd.DataFrame
        A data frame
    table_name : str
        A string containing a valid table name for the data frame
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
            "Table name must begin with a letter and contain only letters, numbers, and underscores"
        )

    # Process greeting
    if greeting is None:
        print(
            "Warning: No greeting provided; the LLM will be invoked at conversation start to generate one. "
            "For faster startup, lower cost, and determinism, please save a greeting and pass it to init().",
            file=sys.stderr,
        )

    # Create the system prompt
    if system_prompt_override is None:
        _system_prompt = system_prompt(
            df, table_name, data_description, extra_instructions
        )
    else:
        _system_prompt = system_prompt_override

    # Set up DuckDB connection and register the data frame
    conn = duckdb.connect(database=":memory:")
    conn.register(table_name, df)

    # Default chat function if none provided
    create_chat_callback = create_chat_callback or partial(
        chatlas.ChatOpenAI, model="gpt-4o"
    )

    return QueryChatConfig(
        df=df,
        conn=conn,
        system_prompt=_system_prompt,
        greeting=greeting,
        create_chat_callback=create_chat_callback,
    )


@module.ui
def mod_ui() -> ui.TagList:
    """
    Create the UI for the querychat component.

    Returns
    -------
    ui.TagList
        A UI component.
    """
    # Include CSS
    css_path = os.path.join(os.path.dirname(__file__), "static", "css", "styles.css")

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
def server(
    input: Inputs, output: Outputs, session: Session, querychat_config: QueryChatConfig
) -> Dict[str, Any]:
    """
    Initialize the querychat server.

    Parameters
    ----------
    querychat_config : QueryChatConfig
        Configuration object from init().

    Returns
    -------
    Dict[str, Any]
        A dictionary with reactive components:
            - sql: A reactive that returns the current SQL query.
            - title: A reactive that returns the current title.
            - df: A reactive that returns the filtered data frame.
            - chat: The chat object.
    """

    @reactive.Effect
    def _():
        # This will be triggered when the module is initialized
        # Here we would set up the chat interface, initialize the chat model, etc.
        pass

    # Extract config parameters
    df = querychat_config.df
    conn = querychat_config.conn
    system_prompt = querychat_config.system_prompt
    greeting = querychat_config.greeting
    create_chat_callback = querychat_config.create_chat_callback

    # Reactive values to store state
    current_title = reactive.Value(None)
    current_query = reactive.Value("")

    @reactive.Calc
    def filtered_df():
        if current_query.get() == "":
            return df
        else:
            return conn.execute(current_query.get()).fetch_df()

    # This would handle appending messages to the chat UI
    async def append_output(text):
        async with chat_ui.message_stream_context() as msgstream:
            await msgstream.append(text)

    # The function that updates the dashboard with a new SQL query
    async def update_dashboard(query: str, title: str):
        """
        Modifies the data presented in the data dashboard, based on the given SQL query,
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
            conn.execute(query)
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
            result_df = conn.execute(query).fetch_df()
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
    return {
        "chat": chat,
        "sql": current_query.get,
        "title": current_title.get,
        "df": filtered_df,
    }
