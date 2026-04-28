"""
Playwright tests for visualization bookmark restore behavior.

These tests verify that when a user creates a visualization and then
restores from a bookmark URL, the chart widget is properly re-rendered
(not just the empty HTML shell).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from collections.abc import Generator

    from playwright.sync_api import BrowserContext, Page
    from shinychat.playwright import ChatController as ChatControllerType

import sys

# conftest.py is not importable directly; add the test directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))
from conftest import (
    _create_chat_controller,
    _find_free_port,
    _start_server_with_retry,
    _start_shiny_app_threaded,
    _stop_shiny_server,
)

VIZ_PROMPT = "Use the visualize tool to create a scatter plot of age vs fare"
TOOL_RESULT_TIMEOUT = 90_000
APPS_DIR = Path(__file__).parent / "apps"


@pytest.fixture(scope="module")
def app_viz_bookmark() -> Generator[str, None, None]:
    """Start the viz bookmark test app with server-side bookmarking."""
    app_path = str(APPS_DIR / "viz_bookmark_app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    def shiny_cleanup(_thread, server):
        _stop_shiny_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, shiny_cleanup, timeout=30.0
    )
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_viz_bookmark(page: Page) -> ChatControllerType:
    return _create_chat_controller(page, "titanic")


class TestVizBookmarkRestore:
    """Tests for visualization restoration from bookmark URLs."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_viz_bookmark: str, chat_viz_bookmark: ChatControllerType
    ) -> None:
        """Navigate to the viz app and create a viz before each test."""
        self.app_url = app_viz_bookmark
        self.page = page
        self.chat = chat_viz_bookmark

        page.goto(app_viz_bookmark)
        page.wait_for_selector("shiny-chat-container", timeout=30_000)

        # Wait for the greeting bookmark URL to be set first
        # (bookmark_on="response" auto-bookmarks after greeting)
        page.wait_for_function(
            "() => window.location.search.includes('_state_id_=')",
            timeout=30_000,
        )
        self.greeting_url = page.url

        # Create a visualization
        chat_viz_bookmark.set_user_input(VIZ_PROMPT)
        chat_viz_bookmark.send_user_input(method="click")

        # Wait for the viz tool result to fully render
        page.locator(".shiny-tool-result:has(.tool-fullscreen-toggle)").wait_for(
            state="visible", timeout=TOOL_RESULT_TIMEOUT
        )
        page.locator(".querychat-footer-buttons").wait_for(
            state="visible", timeout=10_000
        )

    def _wait_for_viz_bookmark_url(self) -> str:
        """Wait for the URL to update from the greeting bookmark to the viz bookmark."""
        greeting_search = self.greeting_url.split("?", 1)[1] if "?" in self.greeting_url else ""
        self.page.wait_for_function(
            "(greetingSearch) => window.location.search.includes('_state_id_=') && window.location.search !== '?' + greetingSearch",
            arg=greeting_search,
            timeout=30_000,
        )
        return self.page.url

    def test_bookmark_url_updates_after_viz(self) -> None:
        """BOOKMARK-VIZ-URL: URL should update with new state ID after viz is created."""
        url = self._wait_for_viz_bookmark_url()
        assert url != self.greeting_url, "URL should have changed after viz bookmarking"

    def test_viz_widget_renders_on_bookmark_restore(self, context: BrowserContext) -> None:
        """BOOKMARK-VIZ-RESTORE: Restored bookmark should re-render the chart widget, not just the HTML shell."""
        bookmark_url = self._wait_for_viz_bookmark_url()

        # Open the bookmark URL in a new page (new session)
        new_page = context.new_page()
        new_page.goto(bookmark_url)
        new_page.wait_for_selector("shiny-chat-container", timeout=30_000)

        # The viz container HTML should be restored (shinychat restores message HTML)
        viz_container = new_page.locator(".querychat-viz-container")
        expect(viz_container).to_be_visible(timeout=30_000)

        # The critical check: the widget should actually render a chart,
        # not just be an empty output_widget div. A rendered Vega-Lite chart
        # will have a canvas or SVG inside a .vega-embed container.
        chart_element = viz_container.locator("canvas, svg, .vega-embed")
        expect(chart_element.first).to_be_visible(timeout=30_000)

        new_page.close()
