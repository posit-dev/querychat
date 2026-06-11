"""
Validation (dry-run) and HTML rendering for dashboard cards.

Every mutation path (LLM tools, pins, palette drops, autogen, bookmark
restore) goes through validate-then-render here, so a broken card can never
reach the canvas — the pieces lesson: dry-run before DOM mutation.
"""

from __future__ import annotations

import html as html_mod
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from shiny import ui

from ._utils import as_narwhals, df_to_html

if TYPE_CHECKING:
    from ._dashboard_state import CardSpec
    from ._datasource import DataSource

CURRENCY_PREFIXES = ("$", "€", "£", "¥")


def validate_card(data_source: DataSource, card: CardSpec) -> None:
    """Raise ValueError if the card's source can't execute. Cheap where possible."""
    if card.type == "markdown":
        return
    if card.type == "chart":
        from ggsql import validate

        validated = validate(card.ggsql)
        if not validated.has_visual():
            raise ValueError(
                "A chart card's ggsql must include a VISUALISE clause."
            )
        if not validated.valid():
            raise ValueError(
                "\n".join(e["message"] for e in validated.errors())
            )
        return
    # table / value_box
    try:
        data_source.test_query(card.sql)
    except Exception as e:
        raise ValueError(str(e)) from e
    if card.type == "value_box":
        scalar_value(data_source, card.sql)  # raises if not 1x1
        if card.delta_sql:
            scalar_value(data_source, card.delta_sql)


def scalar_value(data_source: DataSource, sql: str) -> object:
    """Execute sql and return the single scalar result, or raise ValueError."""
    result = as_narwhals(data_source.execute_query(sql))
    rows = result.rows()
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ValueError(
            f"value_box SQL must return a single value (got "
            f"{len(rows)} row(s) x {len(rows[0]) if rows else 0} column(s))."
        )
    return rows[0][0]


def format_value(value: object, fmt: str) -> str:
    """Format a scalar value using a Python format spec, with optional currency prefix."""
    if fmt:
        prefix = ""
        if fmt[0] in CURRENCY_PREFIXES:
            prefix, fmt = fmt[0], fmt[1:]
        try:
            return f"{prefix}{format(value, fmt)}"
        except (ValueError, TypeError):
            return f"{prefix}{value}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def card_html(data_source: DataSource, card: CardSpec) -> str:
    """Render a card's inner HTML. Charts also register a shinywidgets widget."""
    body = render_body(data_source, card)
    footer = query_footer(card)
    title_html = (
        f'<div class="querychat-dash-card-title">{html_mod.escape(card.title)}</div>'
        if card.title
        else ""
    )
    return (
        f'<div class="querychat-dash-card querychat-dash-card-{card.type}">'
        f"{title_html}"
        f'<div class="querychat-dash-card-body">{body}</div>'
        f"{footer}"
        f"</div>"
    )


def render_body(data_source: DataSource, card: CardSpec) -> str:
    """Render the body HTML for a card, dispatching by type."""
    if card.type == "markdown":
        return str(ui.markdown(card.text))

    if card.type == "value_box":
        value = format_value(scalar_value(data_source, card.sql), card.format)
        delta_html = ""
        if card.delta_sql:
            delta = scalar_value(data_source, card.delta_sql)
            arrow = "▲" if isinstance(delta, (int, float)) and delta >= 0 else "▼"
            delta_html = (
                f'<div class="querychat-dash-delta">{arrow} '
                f"{format_value(delta, card.format)}</div>"
            )
        icon_html = ""
        if card.icon:
            from ._icons import ICON_NAMES, bs_icon

            # CardSpec.icon is str; ICON_NAMES is a Literal union. The LLM is
            # constrained to valid icon names by the tool schema, so this cast
            # is safe — bs_icon will raise at runtime if an invalid name slips
            # through.
            icon_html = str(
                bs_icon(cast(ICON_NAMES, card.icon), cls="querychat-dash-vb-icon")
            )
        theme_cls = f" querychat-dash-vb-{card.theme}" if card.theme else ""
        return (
            f'<div class="querychat-dash-value-box{theme_cls}">{icon_html}'
            f'<div class="querychat-dash-vb-value">{html_mod.escape(value)}</div>'
            f"{delta_html}</div>"
        )

    if card.type == "table":
        result = data_source.execute_query(card.sql)
        return str(df_to_html(result, maxrows=card.page_size))

    # chart — registers a shinywidgets widget as a side effect
    # Import ggsql lazily to match the optional-dep pattern in _viz_tools.py
    from ggsql import validate
    from shinywidgets import output_widget, register_widget

    from ._viz_altair_widget import AltairWidget
    from ._viz_ggsql import execute_ggsql

    validated = validate(card.ggsql)
    spec = execute_ggsql(data_source, validated)
    widget_id = f"qcdash_{card.name}_{uuid4().hex[:8]}"
    altair_widget = AltairWidget.from_ggsql(spec, widget_id=widget_id)
    register_widget(widget_id, altair_widget.widget)
    widget_html = output_widget(widget_id, fill=True, fillable=True)
    widget_html.add_class("querychat-dash-chart")
    return str(widget_html)


def query_footer(card: CardSpec) -> str:
    """Return a <details> element with the card's source query, or '' for markdown."""
    if card.type == "markdown":
        return ""
    return (
        '<details class="querychat-dash-query-footer">'
        "<summary>Show Query</summary>"
        f"<pre><code>{html_mod.escape(card.source)}</code></pre>"
        "</details>"
    )
