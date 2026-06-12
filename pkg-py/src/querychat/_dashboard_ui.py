"""Static UI skeleton for the dashboard drawer (hidden until opened)."""

from __future__ import annotations

import html as html_mod
import json
from typing import TYPE_CHECKING

from htmltools import HTMLDependency, TagList, tags
from shiny.module import resolve_id

from .__version import __version__
from ._icons import bs_icon

if TYPE_CHECKING:
    from ._dashboard_palette import PaletteItem

# Inputs the browser sets (namespaced ids resolved server-side and embedded
# in the DOM so the TS doesn't need to know the module id).
CLIENT_INPUTS = (
    "dashboard_open",
    "dashboard_close",
    "dashboard_layout_change",
    "dashboard_remove_card",
    "dashboard_palette_add",
    "dashboard_pin",
    "dashboard_undo",
    "dashboard_redo",
)


def dashboard_dep() -> HTMLDependency:
    return HTMLDependency(
        "querychat-dashboard",
        __version__,
        source={"package": "querychat", "subdir": "static"},
        stylesheet=[{"href": "css/gridstack.css"}, {"href": "css/dashboard.css"}],
        script=[{"src": "js/dashboard.js"}],
    )


def dashboard_drawer_ui() -> TagList:
    input_ids = {name: str(resolve_id(name)) for name in CLIENT_INPUTS}
    drawer = tags.div(
        {
            "class": "querychat-dash-drawer",
            "hidden": "hidden",
            "data-qcdash-inputs": json.dumps(input_ids),
        },
        tags.div(
            {"class": "querychat-dash-header"},
            tags.span({"class": "querychat-dash-title"}, "My dashboard"),
            tags.div(
                {"class": "querychat-dash-header-actions"},
                tags.button(
                    {
                        "class": "querychat-dash-undo",
                        "disabled": "disabled",
                        "title": "Undo",
                    },
                    bs_icon("arrow-counterclockwise"),
                ),
                tags.button(
                    {
                        "class": "querychat-dash-redo",
                        "disabled": "disabled",
                        "title": "Redo",
                    },
                    bs_icon("arrow-clockwise"),
                ),
                tags.button({"class": "querychat-dash-close", "title": "Close"}, "✕"),
            ),
        ),
        tags.div(
            {"class": "querychat-dash-body"},
            tags.div({"class": "querychat-dash-chat-slot"}),
            tags.div(
                {"class": "querychat-dash-canvas-wrap"},
                tags.div(
                    {"class": "querychat-dash-autogen-spinner", "hidden": "hidden"},
                    "Generating a first-pass dashboard…",
                ),
                tags.div({"class": "grid-stack querychat-dash-canvas"}),
            ),
            tags.div(
                {"class": "querychat-dash-palette"},
                tags.div({"class": "querychat-dash-palette-header"}, "Results"),
                tags.div({"class": "querychat-dash-palette-items"}),
            ),
        ),
    )
    badge = tags.button(
        {"class": "querychat-dash-badge", "hidden": "hidden"},
        bs_icon("grid-1x2-fill"),
        tags.span({"class": "querychat-dash-badge-count"}, "0"),
    )
    return TagList(drawer, badge, dashboard_dep())


def palette_html(items: list[PaletteItem]) -> str:
    parts: list[str] = []
    for item in items:
        cls = "querychat-dash-palette-item" + (" on-canvas" if item.on_canvas else "")
        if item.thumbnail:
            thumb = f'<img src="{html_mod.escape(item.thumbnail, quote=True)}" alt="">'
        else:
            thumb = item.preview_html or ""
        check = (
            '<span class="querychat-dash-palette-check">✓</span>'
            if item.on_canvas
            else ""
        )
        parts.append(
            f'<div class="{cls}" draggable="true" data-palette-id="{html_mod.escape(item.id)}" '
            f'data-kind="{item.kind}">'
            f'<div class="querychat-dash-palette-thumb">{thumb}</div>'
            f'<div class="querychat-dash-palette-title">{html_mod.escape(item.title)}</div>'
            f"{check}"
            f"</div>"
        )
    if not parts:
        return '<div class="querychat-dash-palette-empty">Ask questions in the chat — results show up here.</div>'
    return "".join(parts)
