from __future__ import annotations

import copy
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, TypedDict, Union

import chevron
import shinychat
import sqlalchemy
from shiny import Inputs, Outputs, Session, reactive, ui

from ._utils import normalize_client
from .datasource import DataFrameSource, DataSource, SQLAlchemySource
from .tools import tool_query, tool_reset_dashboard, tool_update_dashboard

if TYPE_CHECKING:
    import chatlas
    import pandas as pd
    from narwhals.stable.v1.typing import IntoFrame
    from shiny.bookmark import BookmarkState, RestoreState


ReactiveString = reactive.Value[str]
"""A reactive string value."""
ReactiveStringOrNone = reactive.Value[Union[str, None]]
"""A reactive string (or None) value."""


def system_prompt_impl(
    data_source: DataSource,
    *,
    data_description: Optional[str | Path] = None,
    extra_instructions: Optional[str | Path] = None,
    categorical_threshold: int = 10,
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


class InitResult(TypedDict):
    data_source: DataSource
    system_prompt: str
    greeting: Optional[str]
    client: chatlas.Chat


def init_impl(
    data_source: IntoFrame | sqlalchemy.Engine,
    table_name: str,
    *,
    greeting: Optional[str | Path] = None,
    data_description: Optional[str | Path] = None,
    extra_instructions: Optional[str | Path] = None,
    prompt_template: Optional[str | Path] = None,
    system_prompt_override: Optional[str] = None,
    client: Optional[Union[chatlas.Chat, str]] = None,
) -> InitResult:
    resolved_client = normalize_client(client)

    # Validate table name (must begin with letter, contain only letters, numbers, underscores)
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", table_name):
        raise ValueError(
            "Table name must begin with a letter and contain only letters, numbers, and underscores",
        )

    data_source_obj = normalize_data_source(data_source, table_name)

    # Process greeting
    if greeting is None:
        print(
            "Warning: No greeting provided; the LLM will be invoked at conversation start to generate one. "
            "For faster startup, lower cost, and determinism, please save a greeting and pass it to init().",
            "You can also use `querychat.greeting()` to help generate a greeting.",
            file=sys.stderr,
        )

    # quality of life improvement to do the Path.read_text() for user or pass along the string
    greeting_str = greeting.read_text() if isinstance(greeting, Path) else greeting

    # Create the system prompt, or use the override
    if isinstance(system_prompt_override, Path):
        system_prompt_ = system_prompt_override.read_text()
    else:
        system_prompt_ = system_prompt_override or system_prompt_impl(
            data_source_obj,
            data_description=data_description,
            extra_instructions=extra_instructions,
            prompt_template=prompt_template,
        )

    return InitResult(
        data_source=data_source_obj,
        system_prompt=system_prompt_,
        greeting=greeting_str,
        client=resolved_client,
    )


def normalize_data_source(
    data_source: IntoFrame | sqlalchemy.Engine | DataSource,
    table_name: str,
) -> DataSource:
    if isinstance(data_source, DataSource):
        return data_source
    if isinstance(data_source, sqlalchemy.Engine):
        return SQLAlchemySource(data_source, table_name)
    return DataFrameSource(data_source, table_name)


def ui_impl(**kwargs) -> ui.TagList:
    css_path = Path(__file__).parent / "static" / "css" / "styles.css"
    js_path = Path(__file__).parent / "static" / "js" / "querychat.js"

    tag = shinychat.chat_ui("chat", **kwargs)
    tag.add_class("querychat")

    return ui.TagList(
        ui.head_content(
            ui.include_css(css_path),
            ui.include_js(js_path),
        ),
        tag,
    )


@dataclass
class ServerResult:
    df: Callable[[], pd.DataFrame]
    current_query: ReactiveString
    current_title: ReactiveStringOrNone
    chat: chatlas.Chat


def server_impl(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    data_source: DataSource,
    system_prompt: str,
    greeting: Optional[str],
    client: chatlas.Chat,
    enable_bookmarking: bool = False,
) -> ServerResult:
    # Reactive values to store state
    current_title = ReactiveStringOrNone(None)
    current_query = ReactiveString("")
    has_greeted = reactive.value[bool](False)  # noqa: FBT003

    @reactive.calc
    def filtered_df():
        if current_query.get() == "":
            return data_source.get_data()
        else:
            return data_source.execute_query(current_query.get())

    # Create the tool functions
    update_dashboard_tool = tool_update_dashboard(
        data_source,
        current_query,
        current_title,
    )
    reset_dashboard_tool = tool_reset_dashboard(
        current_query,
        current_title,
    )
    query_tool = tool_query(data_source)

    chat_ui = shinychat.Chat("chat")

    # Set up the chat object for this session
    chat = copy.deepcopy(client)
    chat.set_turns([])
    chat.system_prompt = system_prompt

    # Register tools with annotations for the UI
    chat.register_tool(update_dashboard_tool)
    chat.register_tool(query_tool)
    chat.register_tool(reset_dashboard_tool)

    # Handle user input
    @chat_ui.on_user_submit
    async def _(user_input: str):
        stream = await chat.stream_async(user_input, echo="none", content="all")
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
            current_query.set(query)
        if title is not None:
            current_title.set(title)

    @reactive.effect
    async def greet_on_startup():
        if has_greeted():
            return

        if greeting:
            await chat_ui.append_message(greeting)
        elif greeting is None:
            stream = await chat.stream_async(
                "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list.",
                echo="none",
            )
            await chat_ui.append_message_stream(stream)

        has_greeted.set(True)

    if enable_bookmarking:
        chat_ui.enable_bookmarking(client)

        def _on_bookmark(x: BookmarkState) -> None:
            vals = x.values  # noqa: PD011
            vals["querychat_current_query"] = current_query.get()
            vals["querychat_current_title"] = current_title.get()
            vals["querychat_has_greeted"] = has_greeted.get()

        session.bookmark.on_bookmark(_on_bookmark)

        def _on_restore(x: RestoreState) -> None:
            vals = x.values  # noqa: PD011
            if "querychat_current_query" in vals:
                current_query.set(vals["querychat_current_query"])
            if "querychat_current_title" in vals:
                current_title.set(vals["querychat_current_title"])
            if "querychat_has_greeted" in vals:
                has_greeted.set(vals["querychat_has_greeted"])

        session.bookmark.on_restore(_on_restore)

    return ServerResult(
        df=filtered_df,
        current_query=current_query,
        current_title=current_title,
        chat=chat,
    )
