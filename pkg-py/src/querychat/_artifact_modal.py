from __future__ import annotations

from typing import TYPE_CHECKING

from htmltools import Tag, TagList, tags

from shiny import ui

from ._artifact_gallery import GalleryItem, QueryGalleryItem, VizGalleryItem
from ._artifact_types import ARTIFACT_TYPES, LANGUAGES
from ._icons import bs_icon

if TYPE_CHECKING:
    from collections.abc import Callable


def build_modal_ui(
    ns: Callable[[str], str],
    gallery_items: list[GalleryItem],
) -> Tag:
    has_items = len(gallery_items) > 0
    gallery = build_gallery(gallery_items)
    type_pills = build_type_selector()
    language_pills = build_language_selector()

    loading_class = " loading" if has_items else ""

    return ui.modal(
        tags.p(
            "Preserve important findings in a standalone report, dashboard, or script.",
            class_="querychat-artifact-modal-intro",
        ),
        # 1. Gallery
        section_label(
            "Results to include",
            "Select which queries and visualizations to include in the artifact.",
        ),
        tags.div(
            tags.div(class_="spinner"),
            "Analyzing your results...",
            class_="querychat-artifact-loading-status"
            + (" hidden" if not has_items else ""),
        ),
        tags.div(gallery, class_="querychat-artifact-gallery-scroll"),
        # 2. Output format
        section_label(
            "Output format",
            "Choose the file type for the generated artifact.",
            class_="mt-2",
        ),
        type_pills,
        # 2b. Language
        section_label(
            "Language",
            "Preferred programming language. Quarto, Shiny, and Jupyter support either R or Python; Marimo is Python only.",
            class_="mt-2",
        ),
        language_pills,
        # 3. Generation notes
        tags.div(
            section_label(
                "Generation notes",
                "Optional instructions for the AI on how to structure or style the artifact.",
            ),
            tags.span(
                bs_icon("stars"),
                "Pre-filled by AI",
                class_="querychat-artifact-directions-subtitle hidden",
            ),
            class_="querychat-artifact-section-label-row mt-2",
        ),
        tags.div(
            build_directions_textarea(disabled=has_items),
            class_="querychat-artifact-directions-wrapper" + loading_class,
        ),
        # 4. Footer
        tags.div(
            tags.button(
                bs_icon("stars"),
                " Generate",
                id=ns("artifact_generate"),
                class_="btn btn-primary querychat-artifact-generate",
                disabled="disabled",
            ),
            class_="d-flex justify-content-end mt-2",
        ),
        title="Create Artifact",
        footer=None,
        size="l",
        easy_close=True,
    )


def build_directions_textarea(*, disabled: bool) -> Tag:
    textarea = ui.input_text_area(
        "artifact_directions",
        label=None,
        placeholder="e.g., Use a dark theme, put the revenue chart prominently...",
        width="100%",
        autoresize=True,
    )
    # input_text_area has no `disabled` parameter, so set the attribute on the
    # underlying <textarea> directly. JS re-enables it once recommendation completes.
    if disabled:
        for child in textarea.children:
            if isinstance(child, Tag) and child.name == "textarea":
                child.attrs["disabled"] = "disabled"
    return textarea


def build_type_selector() -> TagList:
    pills = []
    for i, (type_id, art_type) in enumerate(ARTIFACT_TYPES.items()):
        active_class = " active" if i == 0 else ""
        label = TagList(bs_icon(art_type.icon), " ", art_type.label)
        pills.append(
            tags.button(
                label,
                class_=f"querychat-artifact-type-pill{active_class}",
                type="button",
                data_artifact_type=type_id,
                data_languages=",".join(art_type.supported_languages),
            )
        )
    pills.append(
        tags.button(
            TagList(bs_icon("three-dots"), " Other"),
            class_="querychat-artifact-type-pill",
            type="button",
            data_artifact_type="other",
            data_languages="python,r",
        )
    )

    return TagList(
        tags.div(*pills, class_="querychat-artifact-type-selector"),
        tags.div(
            tags.input(
                type="text",
                class_="form-control mt-2",
                placeholder="e.g., R Markdown report, Streamlit app, SQL script...",
            ),
            class_="querychat-artifact-freeform-input hidden",
        ),
    )


def build_language_selector() -> Tag:
    pills = [
        tags.button(
            "No preference",
            class_="querychat-artifact-language-pill active",
            type="button",
            data_language="",
        )
    ]
    for lang_id, label in LANGUAGES.items():
        pills.append(
            tags.button(
                label,
                class_="querychat-artifact-language-pill",
                type="button",
                data_language=lang_id,
            )
        )
    return tags.div(*pills, class_="querychat-artifact-language-selector")


def build_gallery(items: list[GalleryItem]) -> Tag:
    if not items:
        return tags.div(
            tags.p("No results yet — ask a question first to populate the gallery."),
            class_="querychat-artifact-gallery-empty",
        )

    item_cards = []
    for item in items:
        if isinstance(item, VizGalleryItem):
            card = build_viz_card(item)
        else:
            card = build_query_card(item)
        item_cards.append(card)

    return tags.div(*item_cards, class_="querychat-artifact-gallery loading")


def build_checkbox() -> Tag:
    return tags.div(
        tags.svg(
            Tag("polyline", points="3 6.5 5.5 9 9 3.5"),
            viewBox="0 0 12 12",
            xmlns="http://www.w3.org/2000/svg",
        ),
        class_="gallery-checkbox",
    )


def build_viz_card(item: VizGalleryItem) -> Tag:
    if item.thumbnail:
        visual = tags.img(src=item.thumbnail, alt=item.title)
    else:
        visual = tags.div("No preview", class_="placeholder-icon")

    return tags.div(
        build_checkbox(),
        tags.div(visual, class_="preview-container"),
        tags.div(item.title, class_="title"),
        class_="querychat-artifact-gallery-item",
        data_item_id=item.id,
    )


def build_query_card(item: QueryGalleryItem) -> Tag:
    if item.preview_html:
        preview = tags.div(ui.HTML(item.preview_html), class_="preview-container")
    else:
        preview = tags.div(
            tags.div(item.sql[:80], class_="sql-snippet"),
            class_="preview-container",
        )

    return tags.div(
        build_checkbox(),
        preview,
        tags.div(item.title, class_="title"),
        class_="querychat-artifact-gallery-item",
        data_item_id=item.id,
    )


def section_label(text: str, tooltip: str, class_: str = "") -> Tag:
    cls = "querychat-artifact-section-label"
    if class_:
        cls += f" {class_}"
    return tags.div(
        text,
        " ",
        ui.tooltip(
            tags.span(
                bs_icon("info-circle"),
                class_="querychat-artifact-info-icon",
                tabindex="0",
            ),
            tooltip,
            placement="top",
        ),
        class_=cls,
    )
