from __future__ import annotations

import html
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from chatlas.types import Content, ContentImageInline, ContentToolResult

from ._tool_names import TOOL_QUERY, TOOL_UPDATE_DASHBOARD, TOOL_VISUALIZE

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chatlas import Turn

MAX_TITLE_LENGTH = 60
MAX_PREVIEW_ROWS = 4
MAX_PREVIEW_COLS = 4


@dataclass(frozen=True)
class VizGalleryItem:
    id: str
    title: str
    thumbnail: str | None
    ggsql: str


@dataclass(frozen=True)
class QueryGalleryItem:
    id: str
    title: str
    sql: str
    preview_html: str | None = None


GalleryItem = VizGalleryItem | QueryGalleryItem


def extract_gallery_items(turns: list[Turn]) -> list[GalleryItem]:
    items: list[GalleryItem] = []
    counter = 0

    for turn in turns:
        contents = turn.contents
        for i, content in enumerate(contents):
            if not isinstance(content, ContentToolResult):
                continue
            if content.request is None:
                continue

            tool_name = content.request.name
            args = content.request.arguments
            if not isinstance(args, dict):
                continue

            if content.error is not None:
                continue

            if tool_name == TOOL_VISUALIZE:
                item = extract_viz(counter, args, contents, i)
                if item is not None:
                    items.append(item)
                    counter += 1

            elif tool_name in (TOOL_QUERY, TOOL_UPDATE_DASHBOARD):
                item = extract_query(counter, args, content)
                if item is not None:
                    items.append(item)
                    counter += 1

    return items


def extract_viz(
    index: int,
    args: dict[str, Any],
    contents: Sequence[Content | str],
    content_index: int,
) -> VizGalleryItem | None:
    ggsql = args.get("ggsql")
    title = args.get("title", "")
    if not ggsql:
        return None

    thumbnail = find_thumbnail(contents, content_index)

    return VizGalleryItem(
        id=f"viz-{index}",
        title=title or ggsql[:MAX_TITLE_LENGTH],
        thumbnail=thumbnail,
        ggsql=ggsql,
    )


def extract_query(
    index: int, args: dict[str, Any], result: ContentToolResult
) -> QueryGalleryItem | None:
    sql = args.get("query")
    if not sql:
        return None

    title = args.get("title") or args.get("_intent") or sql[:MAX_TITLE_LENGTH]
    preview_html = build_preview_table(result.value)

    return QueryGalleryItem(
        id=f"query-{index}",
        title=title,
        sql=sql,
        preview_html=preview_html,
    )


def build_preview_table(value: object) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    first = value[0]
    if not isinstance(first, dict):
        return None

    all_cols = list(first.keys())
    cols = all_cols[:MAX_PREVIEW_COLS]
    rows = value[:MAX_PREVIEW_ROWS]

    # Values flow from query results into a raw HTML string rendered via
    # ui.HTML, so every interpolated value must be escaped.
    header = "".join(f"<th>{html.escape(str(col))}</th>" for col in cols)
    body = ""
    for row in rows:
        cells = "".join(
            f"<td>{html.escape(format_cell(row.get(col, '')))}</td>" for col in cols
        )
        body += f"<tr>{cells}</tr>"

    return (
        f'<table class="querychat-preview-table">'
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{body}</tbody>"
        f"</table>"
    )


def format_cell(value: object) -> str:
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}"
    if value is None:
        return ""
    return str(value)


def find_thumbnail(
    contents: Sequence[Content | str], content_index: int
) -> str | None:
    # chatlas expands multi-part tool results, hoisting ContentImageInline
    # out of ContentToolResult.value into the surrounding turn contents.
    # Scan forward from the tool result for the first image, stopping at
    # the next ContentToolResult.
    for item in contents[content_index + 1 :]:
        if isinstance(item, ContentToolResult):
            break
        if isinstance(item, ContentImageInline):
            return f"data:{item.image_content_type};base64,{item.data}"
    return None
