from __future__ import annotations

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
    from shiny.bookmark import BookmarkState, RestoreState

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


@module.server
def mod_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    data_source: DataSource,
    greeting: str | None,
    client: chatlas.Chat,
    enable_bookmarking: bool,
):
    # Reactive values to store state
    sql = ReactiveString("")
    title = ReactiveStringOrNone(None)
    has_greeted = reactive.value[bool](False)  # noqa: FBT003

    # Create the tool functions
    update_dashboard_tool = tool_update_dashboard(data_source, sql, title)
    reset_dashboard_tool = tool_reset_dashboard(sql, title)
    query_tool = tool_query(data_source)

    # Register tools with annotations for the UI
    client.register_tool(update_dashboard_tool)
    client.register_tool(query_tool)
    client.register_tool(reset_dashboard_tool)

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
        stream = await client.stream_async(user_input, echo="none", content="all")
        await chat_ui.append_message_stream(stream)

    @reactive.effect
    async def greet_on_startup():
        if has_greeted():
            return

        if greeting:
            await chat_ui.append_message(greeting)
        elif greeting is None:
            stream = await client.stream_async(
                "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list.",
                echo="none",
            )
            await chat_ui.append_message_stream(stream)

        has_greeted.set(True)

    # Handle update button clicks
    @reactive.effect
    @reactive.event(input.chat_update)
    def _():
        update = input.chat_update()
        if update is None:
            return
        if not isinstance(update, dict):
            return

        new_query = update.get("query")
        new_title = update.get("title")
        if new_query is not None:
            sql.set(new_query)
        if new_title is not None:
            title.set(new_title)

    if enable_bookmarking:
        chat_ui.enable_bookmarking(client)

        @session.bookmark.on_bookmark
        def _on_bookmark(x: BookmarkState) -> None:
            vals = x.values  # noqa: PD011
            vals["querychat_sql"] = sql.get()
            vals["querychat_title"] = title.get()
            vals["querychat_has_greeted"] = has_greeted.get()

        @session.bookmark.on_restore
        def _on_restore(x: RestoreState) -> None:
            vals = x.values  # noqa: PD011
            if "querychat_sql" in vals:
                sql.set(vals["querychat_sql"])
            if "querychat_title" in vals:
                title.set(vals["querychat_title"])
            if "querychat_has_greeted" in vals:
                has_greeted.set(vals["querychat_has_greeted"])

    return ModServerResult(df=filtered_df, sql=sql, title=title)
