from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Union

import shinychat
from shiny import module, reactive, ui

from .tools import tool_query, tool_reset_dashboard, tool_update_dashboard

if TYPE_CHECKING:
    import chatlas
    import pandas as pd
    from shiny import Inputs, Outputs, Session

    from .datasource import DataSource

ReactiveString = reactive.Value[str]
"""A reactive string value."""
ReactiveStringOrNone = reactive.Value[Union[str, None]]
"""A reactive string (or None) value."""

CHAT_ID = "chat"


@module.ui
def mod_ui(**kwargs):
    css_path = Path(__file__).parent / "static" / "css" / "styles.css"
    js_path = Path(__file__).parent / "static" / "js" / "querychat.js"

    tag = shinychat.chat_ui(CHAT_ID, **kwargs)
    tag.add_class("querychat")

    return ui.TagList(
        ui.head_content(
            ui.include_css(css_path),
            ui.include_js(js_path),
        ),
        tag,
    )


@dataclass
class ModServerResult:
    df: Callable[[], pd.DataFrame]
    sql: ReactiveString
    title: ReactiveStringOrNone
    client: chatlas.Chat


@module.server
def mod_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    data_source: DataSource,
    system_prompt: str,
    greeting: str | None,
    client: chatlas.Chat,
):
    # Reactive values to store state
    sql = ReactiveString("")
    title = ReactiveStringOrNone(None)

    # Set up the chat object for this session
    chat = copy.deepcopy(client)
    chat.set_turns([])
    chat.system_prompt = system_prompt

    # Create the tool functions
    update_dashboard_tool = tool_update_dashboard(data_source, sql, title)
    reset_dashboard_tool = tool_reset_dashboard(sql, title)
    query_tool = tool_query(data_source)

    # Register tools with annotations for the UI
    chat.register_tool(update_dashboard_tool)
    chat.register_tool(query_tool)
    chat.register_tool(reset_dashboard_tool)

    # Execute query when SQL changes
    @reactive.calc
    def filtered_df():
        if sql.get() == "":
            return data_source.get_data()
        else:
            return data_source.execute_query(sql.get())

    # Chat UI logic
    chat_ui = shinychat.Chat(CHAT_ID)

    # Handle user input
    @chat_ui.on_user_submit
    async def _(user_input: str):
        stream = await chat.stream_async(user_input, echo="none", content="all")
        await chat_ui.append_message_stream(stream)

    @reactive.effect
    async def greet_on_startup():
        if greeting:
            await chat_ui.append_message(greeting)
        elif greeting is None:
            stream = await chat.stream_async(
                "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list.",
                echo="none",
            )
            await chat_ui.append_message_stream(stream)

    # Handle update button clicks
    @reactive.effect
    @reactive.event(input.chat_update)
    def _():
        update = input.chat_update()
        if update is None:
            return
        if not isinstance(update, dict):
            return

        query = update.get("query")
        title = update.get("title")
        if query is not None:
            sql.set(query)
        if title is not None:
            title.set(title)

    return ModServerResult(df=filtered_df, sql=sql, title=title, client=chat)
