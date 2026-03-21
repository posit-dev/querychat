"""
Playwright tests for visualization tab behavior based on tools config.

These tests verify that the Query Plot tab is only present when the
visualize_query tool is enabled. With default tools ("update", "query"),
only the Data tab should appear.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


# Shiny Tests
class TestShinyVisualizationTabs:
    """Tests for tab behavior in Shiny app with default tools (no viz)."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_01_hello: str) -> None:
        page.goto(app_01_hello)
        page.wait_for_selector("table", timeout=30000)
        self.page = page

    def test_only_data_tab_present_without_viz_tools(self) -> None:
        """With default tools, only the Data tab should be visible."""
        tabs = self.page.locator('[role="tab"]')
        expect(tabs).to_have_count(1)
        expect(self.page.get_by_role("tab", name="Data")).to_be_visible()

    def test_no_query_plot_tab(self) -> None:
        """Query Plot tab should not exist without visualize_query tool."""
        expect(self.page.get_by_role("tab", name="Query Plot")).to_have_count(0)
