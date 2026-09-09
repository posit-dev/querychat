from __future__ import annotations

import html
from typing import TYPE_CHECKING

from htmltools import HTMLDependency, TagList, tags
from shiny.module import resolve_id

from shiny import ui

from .__version import __version__
from ._icons import bs_icon

if TYPE_CHECKING:
    from ._handoff_types import HandoffType


def handoff_panel_ui() -> TagList:
    return TagList(
        handoff_ui_dependency(),
        tags.div(
            tags.div(class_="querychat-handoff-backdrop"),
            tags.div(
                tags.div(
                    tags.div(
                        tags.h3("Handoff"),
                        tags.span(class_="querychat-handoff-header-spinner"),
                        class_="querychat-handoff-title",
                    ),
                    tags.div(class_="querychat-handoff-header-spacer"),
                    tags.button(
                        bs_icon("pencil-square"),
                        class_="btn btn-sm querychat-handoff-icon-btn querychat-handoff-revise-toggle",
                        type="button",
                        title="Revise with AI",
                        aria_label="Revise with AI",
                    ),
                    ui.download_button(
                        "handoff_download",
                        bs_icon("download"),
                        class_="btn btn-sm querychat-handoff-icon-btn querychat-handoff-download-btn",
                        title="Download",
                    ),
                    tags.span(class_="querychat-handoff-header-divider"),
                    ui.input_action_button(
                        "handoff_close",
                        bs_icon("x-lg"),
                        class_="btn btn-sm querychat-handoff-icon-btn",
                        title="Close",
                        aria_label="Close",
                    ),
                    class_="querychat-handoff-panel-header",
                ),
                tags.div(
                    ui.input_submit_textarea(
                        "handoff_revise_text",
                        placeholder="Ask AI to revise this handoff.",
                        rows=1,
                        width="100%",
                        submit_key="enter",
                    ),
                    class_="querychat-handoff-revise-drawer",
                ),
                tags.div(
                    class_="querychat-handoff-panel-error",
                    style="display:none",
                ),
                tags.div(
                    ui.input_code_editor(
                        "handoff_source_editor",
                        value="",
                        language="plain",
                        # TODO(carson): Cursor alignment still seems off. Also, maybe it makes more sense to encourage
                        # user to move to a different platform for authoring?
                        read_only=True,
                    ),
                    class_="querychat-handoff-panel-body",
                ),
                class_="querychat-handoff-panel",
            ),
            id=resolve_id("handoff_root"),
            class_="querychat-handoff-root",
        ),
    )


def handoff_ui_dependency() -> HTMLDependency:
    return HTMLDependency(
        "querychat-handoff",
        __version__,
        source={"package": "querychat", "subdir": "static"},
        script=[{"src": "js/handoff.js"}],
        stylesheet=[{"href": "css/handoff.css"}],
    )


def render_pill_html(
    handoff_id: str,
    handoff_type: HandoffType,
    input_id: str,
) -> str:
    icon_html = str(bs_icon(handoff_type.icon))
    open_html = str(bs_icon("box-arrow-up-right"))
    return (
        f'<button class="querychat-handoff-pill" data-handoff-id="{handoff_id}" data-input-id="{input_id}">'
        f'<span class="querychat-handoff-pill-icon">{icon_html}</span>'
        f'<span class="querychat-handoff-pill-body">'
        f'<span class="querychat-handoff-pill-title">Handoff</span>'
        f'<span class="querychat-handoff-pill-subtitle">{html.escape(handoff_type.label)}</span>'
        f"</span>"
        f'<span class="querychat-handoff-pill-open">{open_html}</span>'
        f"</button>"
    )
