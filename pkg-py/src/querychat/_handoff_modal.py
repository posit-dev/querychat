from __future__ import annotations

from typing import TYPE_CHECKING

from htmltools import Tag, TagList, tags

from shiny import ui

from ._handoff_gallery import GalleryItem, QueryGalleryItem, VizGalleryItem
from ._handoff_types import HANDOFF_FORMATS, LANGUAGES
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
            class_="querychat-handoff-modal-intro",
        ),
        # 1. Gallery
        section_label(
            "Results to include",
            "Select which queries and visualizations to include in the handoff.",
        ),
        tags.div(
            tags.div(class_="spinner"),
            "Analyzing your results...",
            class_="querychat-handoff-loading-status"
            + (" hidden" if not has_items else ""),
        ),
        tags.div(gallery, class_="querychat-handoff-gallery-scroll"),
        # 2. Output format
        section_label(
            "Output format",
            "Choose the file type for the generated handoff.",
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
                "Optional instructions for the AI on how to structure or style the handoff.",
            ),
            tags.span(
                bs_icon("stars"),
                "Pre-filled by AI",
                class_="querychat-handoff-directions-subtitle hidden",
            ),
            class_="querychat-handoff-section-label-row mt-2",
        ),
        tags.div(
            build_directions_textarea(disabled=has_items),
            class_="querychat-handoff-directions-wrapper" + loading_class,
        ),
        # 4. Footer
        tags.div(
            tags.button(
                bs_icon("stars"),
                " Generate",
                id=ns("handoff_generate"),
                class_="btn btn-primary querychat-handoff-generate",
                disabled="disabled",
            ),
            class_="d-flex justify-content-end mt-2",
        ),
        title="Prepare Handoff",
        footer=None,
        size="l",
        easy_close=True,
        id=ns("handoff_modal_root"),
        class_="querychat-handoff-modal",
    )


def build_directions_textarea(*, disabled: bool) -> Tag:
    textarea = ui.input_text_area(
        "handoff_directions",
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
    for i, (format_id, handoff_format) in enumerate(HANDOFF_FORMATS.items()):
        active_class = " active" if i == 0 else ""
        label = TagList(bs_icon(handoff_format.icon), " ", handoff_format.label)
        pills.append(
            tags.button(
                label,
                class_=f"querychat-handoff-type-pill{active_class}",
                type="button",
                data_handoff_type=format_id,
                data_languages=",".join(handoff_format.supported_languages),
            )
        )
    pills.append(
        tags.button(
            TagList(bs_icon("three-dots"), " Other"),
            class_="querychat-handoff-type-pill",
            type="button",
            data_handoff_type="other",
            data_languages="python,r",
        )
    )

    return TagList(
        tags.div(*pills, class_="querychat-handoff-type-selector"),
        tags.div(
            tags.input(
                type="text",
                class_="form-control mt-2",
                placeholder="e.g., R Markdown report, Streamlit app, SQL script...",
            ),
            class_="querychat-handoff-freeform-input hidden",
        ),
    )


def build_language_selector() -> Tag:
    radios = []
    for lang_id, label in LANGUAGES.items():
        radios.append(
            tags.label(
                tags.input(
                    type="radio",
                    name="querychat-handoff-language",
                    class_="querychat-handoff-language-radio querychat-handoff-language-pill",
                    data_language=lang_id,
                    checked="" if lang_id == "python" else None,
                ),
                label,
                class_="querychat-handoff-language-option",
            )
        )
    return tags.div(
        *radios,
        class_="querychat-handoff-language-selector",
        role="radiogroup",
        aria_label="Programming language",
    )


def build_gallery(items: list[GalleryItem]) -> Tag:
    if not items:
        return tags.div(
            tags.p("No results yet — ask a question first to populate the gallery."),
            class_="querychat-handoff-gallery-empty",
        )

    item_cards = []
    for item in items:
        if isinstance(item, VizGalleryItem):
            card = build_viz_card(item)
        else:
            card = build_query_card(item)
        item_cards.append(card)

    return tags.div(*item_cards, class_="querychat-handoff-gallery loading")


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
        visual = tags.img(src=item.thumbnail, alt=item.title, draggable="false")
    else:
        visual = tags.div("No preview", class_="placeholder-icon")

    return tags.div(
        build_checkbox(),
        tags.div(visual, class_="preview-container"),
        tags.div(item.title, class_="title"),
        class_="querychat-handoff-gallery-item",
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
        class_="querychat-handoff-gallery-item",
        data_item_id=item.id,
    )


def section_label(text: str, tooltip: str, class_: str = "") -> Tag:
    cls = "querychat-handoff-section-label"
    if class_:
        cls += f" {class_}"
    return tags.div(
        text,
        " ",
        ui.tooltip(
            tags.span(
                bs_icon("info-circle"),
                class_="querychat-handoff-info-icon",
                tabindex="0",
            ),
            tooltip,
            placement="top",
        ),
        class_=cls,
    )
