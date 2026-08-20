import re

from querychat._artifact_gallery import VizGalleryItem
from querychat._artifact_modal import (
    build_language_selector,
    build_modal_ui,
    build_type_selector,
    build_viz_card,
)


def ns(x: str) -> str:
    return f"ns-{x}"


class TestLanguageSelector:
    def test_renders_r_and_python_languages(self):
        html = str(build_language_selector())
        assert 'data-language="r"' in html
        assert 'data-language="python"' in html


class TestTypeSelectorLanguages:
    def test_type_selector_reads_languages_from_registry(self):
        html = str(build_type_selector())
        assert 'data-artifact-type="marimo-notebook"' in html
        assert 'data-languages="python"' in html
        assert 'data-artifact-type="shiny-app"' in html
        assert 'data-languages="python,r"' in html

    def test_marimo_pill_is_python_only(self):
        html = str(build_type_selector())
        assert re.search(
            r'data-artifact-type="marimo-notebook"[^>]*data-languages="python"',
            html,
        )

    def test_multilingual_pill_supports_both(self):
        html = str(build_type_selector())
        assert 'data-languages="python,r"' in html


def test_modal_body_has_namespaced_artifact_root():
    html = str(build_modal_ui(ns, []))
    assert 'id="ns-artifact_modal_root"' in html
    assert 'class="modal-body querychat-artifact-modal"' in html


def test_visualization_thumbnail_cannot_be_dragged():
    card = build_viz_card(
        VizGalleryItem(
            id="viz-1",
            title="Sales",
            thumbnail="data:image/png;base64,abc",
            ggsql="SELECT 1",
        )
    )

    assert 'draggable="false"' in str(card)
