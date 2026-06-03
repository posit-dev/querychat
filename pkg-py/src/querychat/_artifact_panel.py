from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING

from htmltools import TagList, tags

from shiny import ui

from ._icons import bs_icon

if TYPE_CHECKING:
    from ._artifact_types import ArtifactType


def artifact_panel_ui() -> TagList:
    css_path = Path(__file__).parent / "static" / "css" / "artifact.css"
    js_path = Path(__file__).parent / "static" / "js" / "artifact.js"

    return TagList(
        ui.head_content(
            ui.include_css(css_path),
            ui.include_js(js_path),
        ),
        tags.div(class_="querychat-artifact-backdrop"),
        tags.div(
            tags.div(
                tags.div(
                    tags.h3("Artifact"),
                    tags.span(class_="querychat-artifact-header-spinner"),
                    class_="querychat-artifact-title",
                ),
                tags.div(
                    ui.input_action_button(
                        "artifact_version_prev",
                        bs_icon("chevron-left"),
                        class_="btn btn-sm querychat-artifact-icon-btn",
                        title="Previous version",
                        aria_label="Previous version",
                    ),
                    tags.span(class_="querychat-artifact-version-label"),
                    ui.input_action_button(
                        "artifact_version_next",
                        bs_icon("chevron-right"),
                        class_="btn btn-sm querychat-artifact-icon-btn",
                        title="Next version",
                        aria_label="Next version",
                    ),
                    class_="querychat-artifact-version-nav",
                ),
                tags.div(class_="querychat-artifact-header-spacer"),
                tags.button(
                    bs_icon("pencil-square"),
                    class_="btn btn-sm querychat-artifact-icon-btn querychat-artifact-revise-toggle",
                    type="button",
                    title="Revise with AI",
                    aria_label="Revise with AI",
                ),
                ui.download_button(
                    "artifact_download",
                    bs_icon("download"),
                    class_="btn btn-sm querychat-artifact-icon-btn querychat-artifact-download-btn",
                    title="Download",
                ),
                tags.span(class_="querychat-artifact-header-divider"),
                ui.input_action_button(
                    "artifact_close",
                    bs_icon("x-lg"),
                    class_="btn btn-sm querychat-artifact-icon-btn",
                    title="Close",
                    aria_label="Close",
                ),
                class_="querychat-artifact-panel-header",
            ),
            tags.div(
                ui.input_submit_textarea(
                    "artifact_revise_text",
                    placeholder="Ask AI to revise this artifact.",
                    rows=1,
                    width="100%",
                    submit_key="enter",
                ),
                class_="querychat-artifact-revise-drawer",
            ),
            tags.div(
                class_="querychat-artifact-panel-error",
                style="display:none",
            ),
            tags.div(
                ui.input_code_editor(
                    "artifact_source_editor",
                    value="",
                    language="plain",
                    # TODO(carson): Cursor alignment still seems off. Also, maybe it makes more sense to encourage
                    # user to move to a different platform for authoring?
                    read_only=True,
                ),
                class_="querychat-artifact-panel-body",
            ),
            class_="querychat-artifact-panel",
        ),
    )


def render_pill_html(
    artifact_id: str,
    artifact_type: ArtifactType,
    input_id: str,
) -> str:
    icon_html = str(bs_icon(artifact_type.icon))
    open_html = str(bs_icon("box-arrow-up-right"))
    return (
        f'<button class="querychat-artifact-pill" data-artifact-id="{artifact_id}" data-input-id="{input_id}">'
        f'<span class="querychat-artifact-pill-icon">{icon_html}</span>'
        f'<span class="querychat-artifact-pill-body">'
        f'<span class="querychat-artifact-pill-title">Artifact</span>'
        f'<span class="querychat-artifact-pill-subtitle">{html.escape(artifact_type.label)}</span>'
        f"</span>"
        f'<span class="querychat-artifact-pill-open">{open_html}</span>'
        f"</button>"
    )
