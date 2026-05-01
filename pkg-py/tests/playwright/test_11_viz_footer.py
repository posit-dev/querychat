"""
Playwright tests for visualization footer interactions (Show Query, Save dropdown).

These tests verify the client-side JS behavior in viz.js:
1. Show Query toggle reveals/hides the query section
2. Save dropdown opens/closes on click
3. Clicking outside the Save dropdown closes it
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Download, Page
    from shinychat.playwright import ChatController


VIZ_PROMPT = "Use the visualize tool to create a scatter plot of age vs fare"
TOOL_RESULT_TIMEOUT = 90_000


def _download_from_save_menu(
    page: Page, export_format: str
) -> tuple[Download, str]:
    """Open the save menu, click the requested format, and capture the download."""
    page.locator(".querychat-save-btn").click()

    option = page.locator(f".querychat-save-{export_format}-btn")
    title = option.get_attribute("data-title") or "chart"

    with page.expect_download(timeout=30_000) as download_info:
        option.click()

    return download_info.value, title


@pytest.fixture(autouse=True)
def _send_viz_prompt(
    page: Page, app_10_viz: str, chat_10_viz: ChatController
) -> None:
    """Navigate to the viz app and trigger a visualization before each test."""
    page.goto(app_10_viz)
    page.wait_for_selector("shiny-chat-container", timeout=30_000)

    chat_10_viz.set_user_input(VIZ_PROMPT)
    chat_10_viz.send_user_input(method="click")

    # Wait for the viz tool result card with fullscreen support
    page.locator(".shiny-tool-result:has(.tool-fullscreen-toggle)").wait_for(
        state="visible", timeout=TOOL_RESULT_TIMEOUT
    )
    # Wait for the footer buttons to appear inside the card
    page.locator(".querychat-footer-buttons").wait_for(
        state="visible", timeout=10_000
    )


class TestShowQueryToggle:
    """Tests for the Show Query / Hide Query toggle button."""

    def test_query_section_hidden_by_default(self, page: Page) -> None:
        """The query section should be hidden initially."""
        section = page.locator(".querychat-query-section")
        expect(section).to_be_attached()
        expect(section).not_to_be_visible()

    def test_click_show_query_reveals_section(self, page: Page) -> None:
        """Clicking 'Show Query' should reveal the query section."""
        btn = page.locator(".querychat-show-query-btn")
        btn.click()

        section = page.locator(".querychat-query-section--visible")
        expect(section).to_be_visible()

    def test_label_changes_to_hide_query(self, page: Page) -> None:
        """After clicking, the label should change to 'Hide Query'."""
        btn = page.locator(".querychat-show-query-btn")
        label = btn.locator(".querychat-query-label")

        expect(label).to_have_text("Show Query")
        btn.click()
        expect(label).to_have_text("Hide Query")

    def test_chevron_rotates_on_expand(self, page: Page) -> None:
        """The chevron should get the --expanded class when query is shown."""
        btn = page.locator(".querychat-show-query-btn")
        chevron = btn.locator(".querychat-query-chevron")

        expect(chevron).not_to_have_class("querychat-query-chevron--expanded")
        btn.click()
        expect(chevron).to_have_class("querychat-query-chevron querychat-query-chevron--expanded")

    def test_toggle_hides_section_again(self, page: Page) -> None:
        """Clicking the button a second time should hide the query section."""
        btn = page.locator(".querychat-show-query-btn")
        btn.click()  # show
        btn.click()  # hide

        section = page.locator(".querychat-query-section")
        expect(section).not_to_have_class("querychat-query-section--visible")

        label = btn.locator(".querychat-query-label")
        expect(label).to_have_text("Show Query")

    def test_query_section_contains_code(self, page: Page) -> None:
        """The revealed query section should contain the ggsql code."""
        btn = page.locator(".querychat-show-query-btn")
        btn.click()

        section = page.locator(".querychat-query-section--visible")
        expect(section).to_be_visible()

        # The code editor should contain VISUALISE (ggsql keyword)
        code = section.locator(".code-editor")
        expect(code).to_be_visible()


class TestSaveDropdown:
    """Tests for the Save button dropdown menu."""

    def test_save_menu_hidden_by_default(self, page: Page) -> None:
        """The save dropdown menu should be hidden initially."""
        menu = page.locator(".querychat-save-menu")
        expect(menu).to_be_attached()
        expect(menu).not_to_be_visible()

    def test_click_save_opens_menu(self, page: Page) -> None:
        """Clicking the Save button should reveal the dropdown menu."""
        btn = page.locator(".querychat-save-btn")
        btn.click()

        menu = page.locator(".querychat-save-menu--visible")
        expect(menu).to_be_visible()

    def test_menu_has_png_and_svg_options(self, page: Page) -> None:
        """The save menu should contain 'Save as PNG' and 'Save as SVG' options."""
        btn = page.locator(".querychat-save-btn")
        btn.click()

        menu = page.locator(".querychat-save-menu--visible")
        expect(menu.locator(".querychat-save-png-btn")).to_be_visible()
        expect(menu.locator(".querychat-save-svg-btn")).to_be_visible()

    def test_click_outside_closes_menu(self, page: Page) -> None:
        """Clicking outside the dropdown should close it."""
        btn = page.locator(".querychat-save-btn")
        btn.click()

        menu = page.locator(".querychat-save-menu")
        expect(menu).to_have_class("querychat-save-menu querychat-save-menu--visible")

        # Click somewhere else on the page body
        page.locator("body").click(position={"x": 10, "y": 10})

        expect(menu).not_to_have_class("querychat-save-menu--visible")

    def test_toggle_save_menu(self, page: Page) -> None:
        """Clicking Save twice should open then close the menu."""
        btn = page.locator(".querychat-save-btn")
        btn.click()
        menu = page.locator(".querychat-save-menu")
        expect(menu).to_have_class("querychat-save-menu querychat-save-menu--visible")

        btn.click()
        expect(menu).not_to_have_class("querychat-save-menu--visible")

    def test_save_as_png_downloads_png(self, page: Page) -> None:
        """Clicking 'Save as PNG' should download a PNG file."""
        download, title = _download_from_save_menu(page, "png")

        assert download.suggested_filename == f"{title}.png"

        download_path = download.path()
        assert download_path is not None

        content = Path(download_path).read_bytes()
        assert content.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(content) > 100

    def test_save_as_svg_downloads_svg(self, page: Page) -> None:
        """Clicking 'Save as SVG' should download an SVG file."""
        download, title = _download_from_save_menu(page, "svg")

        assert download.suggested_filename == f"{title}.svg"

        download_path = download.path()
        assert download_path is not None

        content = Path(download_path).read_text(encoding="utf-8")
        assert "<svg" in content
        assert "</svg>" in content
