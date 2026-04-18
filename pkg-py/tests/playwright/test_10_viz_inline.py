"""
Playwright tests for inline visualization and fullscreen behavior.

These tests verify that:
1. The visualize_query tool renders Altair charts inline in tool result cards
2. The fullscreen toggle button appears on visualization tool results
3. Fullscreen mode works (expand and collapse via button and Escape key)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class TestInlineVisualization:
    """Tests for inline chart rendering in tool result cards."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_10_viz: str, chat_10_viz: ChatController
    ) -> None:
        """Navigate to the viz app before each test."""
        page.goto(app_10_viz)
        page.wait_for_selector("shiny-chat-container", timeout=30000)
        self.page = page
        self.chat = chat_10_viz

    def test_viz_tool_renders_inline_chart(self) -> None:
        """VIZ-INLINE: Visualization tool result contains an inline chart widget."""
        self.chat.set_user_input(
            "Create a scatter plot of age vs fare for the titanic passengers"
        )
        self.chat.send_user_input(method="click")

        # Wait for a tool result card with full-screen attribute (viz results have it)
        tool_card = self.page.locator(".shiny-tool-result:has(.tool-fullscreen-toggle)")
        expect(tool_card).to_be_visible(timeout=90000)

        # The card should contain the viz container (Altair chart via shinywidgets)
        viz_container = tool_card.locator(".querychat-viz-container")
        expect(viz_container).to_be_visible(timeout=10000)

    def test_fullscreen_button_visible_on_viz_card(self) -> None:
        """VIZ-FS-BTN: Fullscreen toggle button appears on visualization cards."""
        self.chat.set_user_input(
            "Make a bar chart showing count of passengers by class"
        )
        self.chat.send_user_input(method="click")

        # Wait for viz tool result
        tool_card = self.page.locator(".shiny-tool-result:has(.tool-fullscreen-toggle)")
        expect(tool_card).to_be_visible(timeout=90000)

        # Fullscreen toggle should be visible
        fs_button = tool_card.locator(".tool-fullscreen-toggle")
        expect(fs_button).to_be_visible()

    def test_fullscreen_toggle_expands_card(self) -> None:
        """VIZ-FS-EXPAND: Clicking fullscreen button expands the card."""
        self.chat.set_user_input(
            "Plot a histogram of passenger ages from the titanic data"
        )
        self.chat.send_user_input(method="click")

        # Wait for viz tool result
        tool_result = self.page.locator(".shiny-tool-result:has(.tool-fullscreen-toggle)")
        expect(tool_result).to_be_visible(timeout=90000)

        # Click fullscreen toggle
        fs_button = tool_result.locator(".tool-fullscreen-toggle")
        fs_button.click()

        # The .shiny-tool-card inside should now have fullscreen attribute
        card = tool_result.locator(".shiny-tool-card[fullscreen]")
        expect(card).to_be_visible()

    def test_escape_closes_fullscreen(self) -> None:
        """VIZ-FS-ESC: Pressing Escape closes fullscreen mode."""
        self.chat.set_user_input(
            "Create a visualization of survival rate by passenger class"
        )
        self.chat.send_user_input(method="click")

        # Wait for viz tool result
        tool_result = self.page.locator(".shiny-tool-result:has(.tool-fullscreen-toggle)")
        expect(tool_result).to_be_visible(timeout=90000)

        # Enter fullscreen
        fs_button = tool_result.locator(".tool-fullscreen-toggle")
        fs_button.click()

        card = tool_result.locator(".shiny-tool-card[fullscreen]")
        expect(card).to_be_visible()

        # Press Escape
        self.page.keyboard.press("Escape")

        # Fullscreen should be removed
        expect(card).not_to_be_visible()

    def test_non_viz_tool_results_have_no_fullscreen(self) -> None:
        """VIZ-NO-FS: Non-visualization tool results don't have fullscreen."""
        self.chat.set_user_input("Show me passengers who survived")
        self.chat.send_user_input(method="click")

        # Wait for a tool result (any)
        tool_result = self.page.locator(".shiny-tool-result").first
        expect(tool_result).to_be_visible(timeout=90000)

        # Non-viz tool results should NOT have fullscreen toggle
        fs_results = self.page.locator(".shiny-tool-result:has(.tool-fullscreen-toggle)")
        expect(fs_results).to_have_count(0)
