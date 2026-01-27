"""
Playwright tests for visualization tabs (Filter Plot, Query Plot).

These tests verify that the visualization tabs are present and show
appropriate placeholder messages when no visualization has been created.

Since the visualization tools require real LLM interaction to create charts,
these tests focus on:
1. Tab presence and accessibility
2. Placeholder messages
3. Tab switching functionality
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


# Shiny Tests
class TestShinyVisualizationTabs:
    """Tests for visualization tabs in Shiny app (01-hello-app.py)."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_01_hello: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_01_hello)
        page.wait_for_selector("table", timeout=30000)
        self.page = page

    def test_three_tabs_present(self) -> None:
        """VIZ-SHINY-01: Three tabs are visible (Data, Filter Plot, Query Plot)."""
        tabs = self.page.locator('[role="tab"]')
        expect(tabs).to_have_count(3)

        expect(self.page.get_by_role("tab", name="Data")).to_be_visible()
        expect(self.page.get_by_role("tab", name="Filter Plot")).to_be_visible()
        expect(self.page.get_by_role("tab", name="Query Plot")).to_be_visible()

    def test_filter_plot_tab_clickable(self) -> None:
        """VIZ-SHINY-02: Filter Plot tab can be clicked."""
        filter_tab = self.page.locator('text="Filter Plot"')
        filter_tab.click()

        # Should show placeholder message
        expect(self.page.locator("text=No filter visualization")).to_be_visible(
            timeout=5000
        )

    def test_query_plot_tab_clickable(self) -> None:
        """VIZ-SHINY-03: Query Plot tab can be clicked."""
        query_tab = self.page.locator('text="Query Plot"')
        query_tab.click()

        # Should show placeholder message
        expect(self.page.locator("text=No query visualization")).to_be_visible(
            timeout=5000
        )

    def test_filter_plot_shows_placeholder(self) -> None:
        """VIZ-SHINY-04: Filter Plot tab shows placeholder when empty."""
        filter_tab = self.page.locator('text="Filter Plot"')
        filter_tab.click()

        placeholder = self.page.locator("text=Use the chat to create one")
        expect(placeholder).to_be_visible(timeout=5000)

    def test_query_plot_shows_placeholder(self) -> None:
        """VIZ-SHINY-05: Query Plot tab shows placeholder when empty."""
        query_tab = self.page.locator('text="Query Plot"')
        query_tab.click()

        placeholder = self.page.locator("text=Use the chat to create one")
        expect(placeholder).to_be_visible(timeout=5000)

    def test_can_switch_between_tabs(self) -> None:
        """VIZ-SHINY-06: Can switch between all three tabs."""
        # Start on Data tab (default)
        expect(self.page.locator("table")).to_be_visible()

        # Switch to Filter Plot
        self.page.locator('text="Filter Plot"').click()
        expect(self.page.locator("text=No filter visualization")).to_be_visible(
            timeout=5000
        )

        # Switch to Query Plot
        self.page.locator('text="Query Plot"').click()
        expect(self.page.locator("text=No query visualization")).to_be_visible(
            timeout=5000
        )

        # Switch back to Data
        self.page.locator('[role="tab"]:has-text("Data")').click()
        expect(self.page.locator("table")).to_be_visible()


# Streamlit Tests
class TestStreamlitVisualizationTabs:
    """Tests for visualization tabs in Streamlit app (04-streamlit-app.py)."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_04_streamlit: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_04_streamlit)
        page.wait_for_selector('[data-testid="stApp"]', timeout=30000)
        page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
        self.page = page

    def test_three_tabs_present(self) -> None:
        """VIZ-STREAMLIT-01: Three tabs are visible."""
        tabs = self.page.locator('[data-baseweb="tab"]')
        expect(tabs).to_have_count(3)

    def test_filter_plot_tab_clickable(self) -> None:
        """VIZ-STREAMLIT-02: Filter Plot tab can be clicked."""
        tabs = self.page.locator('[data-baseweb="tab"]')
        tabs.nth(1).click()  # Filter Plot is second tab

        # Should show info message about no visualization
        expect(self.page.locator("text=No filter visualization")).to_be_visible(
            timeout=5000
        )

    def test_query_plot_tab_clickable(self) -> None:
        """VIZ-STREAMLIT-03: Query Plot tab can be clicked."""
        tabs = self.page.locator('[data-baseweb="tab"]')
        tabs.nth(2).click()  # Query Plot is third tab

        # Should show info message about no visualization
        expect(self.page.locator("text=No query visualization")).to_be_visible(
            timeout=5000
        )

    def test_filter_plot_mentions_tool(self) -> None:
        """VIZ-STREAMLIT-04: Filter Plot placeholder mentions the tool."""
        tabs = self.page.locator('[data-baseweb="tab"]')
        tabs.nth(1).click()

        expect(self.page.locator("text=visualize_dashboard")).to_be_visible(
            timeout=5000
        )

    def test_query_plot_mentions_tool(self) -> None:
        """VIZ-STREAMLIT-05: Query Plot placeholder mentions the tool."""
        tabs = self.page.locator('[data-baseweb="tab"]')
        tabs.nth(2).click()

        expect(self.page.locator("text=visualize_query")).to_be_visible(timeout=5000)


# Gradio Tests
class TestGradioVisualizationTabs:
    """Tests for visualization tabs in Gradio app (05-gradio-app.py)."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_05_gradio: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_05_gradio)
        page.wait_for_selector("gradio-app", timeout=30000)
        page.wait_for_selector('[data-testid="bot"]', timeout=30000)
        self.page = page

    def test_three_tabs_present(self) -> None:
        """VIZ-GRADIO-01: Three tabs are visible."""
        tabs = self.page.locator('[role="tab"]')
        expect(tabs).to_have_count(3)

    def test_filter_plot_tab_clickable(self) -> None:
        """VIZ-GRADIO-02: Filter Plot tab can be clicked."""
        filter_tab = self.page.locator('button[role="tab"]:has-text("Filter Plot")')
        filter_tab.click()

        # Should show placeholder message
        expect(self.page.locator("text=No filter visualization")).to_be_visible(
            timeout=5000
        )

    def test_query_plot_tab_clickable(self) -> None:
        """VIZ-GRADIO-03: Query Plot tab can be clicked."""
        query_tab = self.page.locator('button[role="tab"]:has-text("Query Plot")')
        query_tab.click()

        # Should show placeholder message
        expect(self.page.locator("text=No query visualization")).to_be_visible(
            timeout=5000
        )

    def test_filter_plot_has_plot_area(self) -> None:
        """VIZ-GRADIO-04: Filter Plot tab has plot and ggsql spec areas."""
        filter_tab = self.page.locator('button[role="tab"]:has-text("Filter Plot")')
        filter_tab.click()

        # Should have Plot label
        expect(self.page.locator('text="Plot"')).to_be_visible(timeout=5000)
        # Should have ggsql spec label
        expect(self.page.locator('text="ggsql spec"')).to_be_visible(timeout=5000)

    def test_query_plot_has_plot_area(self) -> None:
        """VIZ-GRADIO-05: Query Plot tab has plot and ggsql query areas."""
        query_tab = self.page.locator('button[role="tab"]:has-text("Query Plot")')
        query_tab.click()

        # Should have Plot label
        expect(self.page.locator('text="Plot"')).to_be_visible(timeout=5000)
        # Should have ggsql query label
        expect(self.page.locator('text="ggsql query"')).to_be_visible(timeout=5000)


# Dash Tests
class TestDashVisualizationTabs:
    """Tests for visualization tabs in Dash app (06-dash-app.py)."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_06_dash: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_06_dash)
        page.wait_for_selector("#querychat-titanic-chat-history", timeout=30000)
        # Wait for greeting
        expect(page.locator("#querychat-titanic-chat-history")).to_contain_text(
            "Hello", timeout=30000
        )
        self.page = page

    def test_three_tabs_present(self) -> None:
        """VIZ-DASH-01: Three tabs are visible."""
        tabs = self.page.locator('[role="tab"]')
        expect(tabs).to_have_count(3)

        expect(self.page.get_by_role("tab", name="Data")).to_be_visible()
        expect(self.page.get_by_role("tab", name="Filter Plot")).to_be_visible()
        expect(self.page.get_by_role("tab", name="Query Plot")).to_be_visible()

    def test_filter_plot_tab_clickable(self) -> None:
        """VIZ-DASH-02: Filter Plot tab can be clicked."""
        filter_tab = self.page.get_by_role("tab", name="Filter Plot")
        filter_tab.click()

        # Should show placeholder in iframe
        filter_plot = self.page.locator("#querychat-titanic-filter-plot")
        expect(filter_plot).to_be_visible(timeout=5000)

    def test_query_plot_tab_clickable(self) -> None:
        """VIZ-DASH-03: Query Plot tab can be clicked."""
        query_tab = self.page.get_by_role("tab", name="Query Plot")
        query_tab.click()

        # Should show placeholder in iframe
        query_plot = self.page.locator("#querychat-titanic-query-plot")
        expect(query_plot).to_be_visible(timeout=5000)

    def test_data_tab_shows_table(self) -> None:
        """VIZ-DASH-04: Data tab shows the data table."""
        # Data tab is default, should show AG Grid. The table wrapper is present
        # but the grid may have height: 0 until data loads.
        # Check that rows are rendered instead.
        data_rows = self.page.locator(".ag-row")
        expect(data_rows.first).to_be_visible(timeout=15000)

    def test_can_switch_between_tabs(self) -> None:
        """VIZ-DASH-05: Can switch between all three tabs."""
        # Start on Data tab (default)
        expect(self.page.locator("#querychat-titanic-sql-display")).to_be_visible()

        # Switch to Filter Plot
        self.page.get_by_role("tab", name="Filter Plot").click()
        expect(self.page.locator("#querychat-titanic-filter-plot")).to_be_visible(
            timeout=5000
        )

        # Switch to Query Plot
        self.page.get_by_role("tab", name="Query Plot").click()
        expect(self.page.locator("#querychat-titanic-query-plot")).to_be_visible(
            timeout=5000
        )

        # Switch back to Data
        self.page.get_by_role("tab", name="Data").click()
        expect(self.page.locator("#querychat-titanic-sql-display")).to_be_visible(
            timeout=5000
        )
