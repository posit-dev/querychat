from __future__ import annotations

from querychat._artifact_gallery import QueryGalleryItem, VizGalleryItem
from querychat._dashboard_palette import (
    PaletteItem,
    card_for_palette_item,
    palette_from_gallery,
)
from querychat._dashboard_state import CardLayout, CardSpec, DashboardSpec


def gallery():
    return [
        VizGalleryItem(id="viz-0", title="MPG trend", thumbnail=None,
                       ggsql="SELECT 1 VISUALISE x AS x DRAW line"),
        QueryGalleryItem(id="query-1", title="Top cars", sql="SELECT * FROM mtcars",
                         preview_html="<table></table>"),
    ]


class TestPaletteFromGallery:
    def test_maps_gallery_kinds(self):
        items = palette_from_gallery(gallery(), DashboardSpec())
        assert [i.kind for i in items] == ["chart", "table"]
        assert items[0].source.startswith("SELECT 1")
        assert not items[0].on_canvas

    def test_on_canvas_flag_matches_by_source(self):
        spec = DashboardSpec(cards=[
            CardSpec(name="mpg_trend", type="chart", title="MPG trend",
                     ggsql="SELECT 1 VISUALISE x AS x DRAW line",
                     layout=CardLayout(x=0, y=0, w=6, h=4)),
        ])
        items = palette_from_gallery(gallery(), spec)
        assert items[0].on_canvas
        assert not items[1].on_canvas


class TestCardForPaletteItem:
    def test_chart_item_becomes_chart_card(self):
        item = PaletteItem(id="viz-0", kind="chart", title="MPG trend!",
                           source="SELECT 1 VISUALISE x AS x DRAW line",
                           thumbnail=None, preview_html=None, on_canvas=False)
        card = card_for_palette_item(item, taken_names=set())
        assert card.type == "chart"
        assert card.ggsql == item.source
        assert card.name == "mpg_trend"  # slugified title

    def test_name_collisions_get_suffix(self):
        item = PaletteItem(id="q", kind="table", title="Top cars",
                           source="SELECT 1", thumbnail=None,
                           preview_html=None, on_canvas=False)
        card = card_for_palette_item(item, taken_names={"top_cars"})
        assert card.name == "top_cars_2"

    def test_long_title_produces_valid_name(self):
        title = "a" * 50  # 50-char title, slug would exceed 40
        item = PaletteItem(id="x", kind="table", title=title,
                           source="SELECT 1", thumbnail=None,
                           preview_html=None, on_canvas=False)
        card = card_for_palette_item(item, taken_names=set())
        assert len(card.name) <= 40

    def test_long_title_with_collision_stays_within_40(self):
        title = "a" * 50
        item = PaletteItem(id="x", kind="table", title=title,
                           source="SELECT 1", thumbnail=None,
                           preview_html=None, on_canvas=False)
        base = "a" * 40
        card = card_for_palette_item(item, taken_names={base})
        assert len(card.name) <= 40

    def test_all_symbols_title_falls_back_to_card(self):
        item = PaletteItem(id="x", kind="table", title="!!! ???",
                           source="SELECT 1", thumbnail=None,
                           preview_html=None, on_canvas=False)
        card = card_for_palette_item(item, taken_names=set())
        assert card.name == "card"
