"""Results palette: everything the session produced, draggable onto the canvas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from ._artifact_gallery import QueryGalleryItem, VizGalleryItem
from ._dashboard_state import CardSpec

if TYPE_CHECKING:
    from ._artifact_gallery import GalleryItem
    from ._dashboard_state import DashboardSpec


@dataclass(frozen=True)
class PaletteItem:
    id: str
    kind: Literal["chart", "table"]
    title: str
    source: str  # ggsql for charts, sql for tables
    thumbnail: str | None
    preview_html: str | None
    on_canvas: bool


def palette_from_gallery(
    items: list[GalleryItem], spec: DashboardSpec
) -> list[PaletteItem]:
    # Strip when comparing: LLM tool calls sometimes carry stray whitespace,
    # which would otherwise leave a placed item looking "not on canvas".
    canvas_sources = {c.source.strip() for c in spec.on_canvas()}
    out: list[PaletteItem] = []
    for item in items:
        if isinstance(item, VizGalleryItem):
            out.append(
                PaletteItem(
                    id=item.id, kind="chart", title=item.title,
                    source=item.ggsql, thumbnail=item.thumbnail,
                    preview_html=None,
                    on_canvas=item.ggsql.strip() in canvas_sources,
                )
            )
        elif isinstance(item, QueryGalleryItem):
            out.append(
                PaletteItem(
                    id=item.id, kind="table", title=item.title,
                    source=item.sql, thumbnail=None,
                    preview_html=item.preview_html,
                    on_canvas=item.sql.strip() in canvas_sources,
                )
            )
    return out


def card_for_palette_item(item: PaletteItem, taken_names: set[str]) -> CardSpec:
    base = slugify(item.title)
    name = base
    suffix = 2
    while name in taken_names:
        # Truncate base so that "{base}_{suffix}" fits within 40 chars
        suffix_str = f"_{suffix}"
        truncated_base = base[: 40 - len(suffix_str)]
        name = f"{truncated_base}{suffix_str}"
        suffix += 1
    if item.kind == "chart":
        return CardSpec(name=name, type="chart", title=item.title, ggsql=item.source)
    return CardSpec(name=name, type="table", title=item.title, sql=item.source)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    # Remove any leading non-alpha characters (pattern requires first char to be [a-z])
    slug = re.sub(r"^[^a-z]+", "", slug) or "card"
    return slug[:40]
