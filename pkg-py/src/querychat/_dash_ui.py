"""Dash UI components for querychat."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dash.development.base_component import Component

    from ._querychat_core import AppState


@dataclass(frozen=True)
class IDs:
    """Element IDs for a QueryChat Dash component."""

    store: str
    chat_history: str
    chat_input: str
    send_button: str
    loading_indicator: str
    sql_display: str
    sql_title: str
    reset_button: str
    data_table: str
    data_info: str
    download_csv: str
    export_button: str
    tabs: str
    filter_plot: str
    filter_plot_title: str
    filter_ggsql: str
    query_plot: str
    query_plot_title: str
    query_ggsql: str

    @classmethod
    def from_table_name(cls, table_name: str) -> IDs:
        """Create IDs from a table name."""
        prefix = f"querychat-{table_name}"
        return cls(
            store=f"{prefix}-store",
            chat_history=f"{prefix}-chat-history",
            chat_input=f"{prefix}-chat-input",
            send_button=f"{prefix}-send-button",
            loading_indicator=f"{prefix}-loading-indicator",
            sql_display=f"{prefix}-sql-display",
            sql_title=f"{prefix}-sql-title",
            reset_button=f"{prefix}-reset-button",
            data_table=f"{prefix}-data-table",
            data_info=f"{prefix}-data-info",
            download_csv=f"{prefix}-download-csv",
            export_button=f"{prefix}-export-button",
            tabs=f"{prefix}-tabs",
            filter_plot=f"{prefix}-filter-plot",
            filter_plot_title=f"{prefix}-filter-plot-title",
            filter_ggsql=f"{prefix}-filter-ggsql",
            query_plot=f"{prefix}-query-plot",
            query_plot_title=f"{prefix}-query-plot-title",
            query_ggsql=f"{prefix}-query-ggsql",
        )


def card_ui(
    body: Component | list[Component],
    *,
    title: str | None = None,
    title_id: str | None = None,
    action_button: Component | None = None,
    class_name: str = "",
    body_class_name: str = "",
) -> Component:
    """Create a Bootstrap card with optional header and action button."""
    import dash_bootstrap_components as dbc

    from dash import html

    children = []

    # Build header if any header content is provided
    if title is not None or title_id is not None or action_button is not None:
        title_kwargs: dict = {"className": "mb-0"}
        if title_id:
            title_kwargs["id"] = title_id
        title_el = html.H4(title or "", **title_kwargs)

        if action_button:
            header_content = dbc.Row(
                [
                    dbc.Col(title_el),
                    dbc.Col(action_button, width="auto"),
                ],
                align="center",
            )
        else:
            header_content = title_el

        children.append(dbc.CardHeader(header_content))

    children.append(dbc.CardBody(body, className=body_class_name or None))

    return dbc.Card(children, className=class_name or None)


def chat_container_ui(ids: IDs) -> list[Component]:
    """Create the chat UI container (messages + input)."""
    import dash_bootstrap_components as dbc

    from dash import html

    return [
        html.Div(
            id=ids.chat_history,
            className="querychat-chat-history",
        ),
        dbc.InputGroup(
            [
                dbc.Input(
                    id=ids.chat_input,
                    placeholder="Ask a question about your data...",
                    type="text",
                ),
                dbc.Button(
                    "Send",
                    id=ids.send_button,
                    color="primary",
                ),
            ]
        ),
        html.Div(
            dbc.Spinner(
                size="sm",
                color="primary",
                spinner_class_name="ms-2",
            ),
            id=ids.loading_indicator,
            className="querychat-loading d-none",
        ),
    ]


def chat_messages_ui(state: AppState) -> list[Component]:
    """Render chat messages as Dash components."""
    from dash import dcc, html

    chat_elements = []
    for msg in state.get_display_messages():
        role_class = (
            "querychat-message-user"
            if msg["role"] == "user"
            else "querychat-message-assistant"
        )
        class_name = f"querychat-message {role_class}"

        if msg["role"] == "assistant":
            content = prepare_content_for_markdown(msg["content"])
        else:
            content = msg["content"]

        chat_elements.append(
            html.Div(
                [
                    html.Strong(msg["role"].title() + ": "),
                    dcc.Markdown(content, dangerously_allow_html=True),
                ],
                className=class_name,
            )
        )
    return chat_elements


def prepare_content_for_markdown(content: str) -> str:
    """Prepare content for rendering in dcc.Markdown."""
    content = convert_suggestion_spans(content)
    content = convert_filter_button(content)
    return content


def convert_suggestion_spans(content: str) -> str:
    """Convert suggestion spans to styled <p> tags for dcc.Markdown."""
    style = "color: #0066cc; cursor: pointer; text-decoration: underline; display: inline; margin: 0;"
    content = re.sub(
        r'<span\s+class="suggestion',
        f'<p style="{style}" class="suggestion',
        content,
    )
    content = re.sub(r"</span>", "</p>", content)
    return content


def convert_filter_button(content: str) -> str:
    """Convert <button> to <div> tags for dcc.Markdown."""
    content = re.sub(r"<button", "<div", content)
    content = re.sub(r"</button>", "</div>", content)
    return content
