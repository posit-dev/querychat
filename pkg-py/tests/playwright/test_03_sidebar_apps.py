"""
Playwright tests for 03-sidebar-express-app.py and 03-sidebar-core-app.py.

These examples use qc.sidebar() for a custom layout with:
- Chat in sidebar
- Reactive title in card header
- Data table in main content
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class Test03SidebarExpress:
    """Tests for 03-sidebar-express-app.py - Shiny Express with sidebar layout."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_03_express: str, chat_03_express: ChatController
    ) -> None:
        """Navigate to the app before each test."""
        page.goto(app_03_express)
        # Wait for data table to be visible
        page.wait_for_selector("table tbody tr", timeout=15000)
        self.page = page
        self.chat = chat_03_express
        # Card header selector (first .card-header div, not buttons)
        self.card_header = page.locator(".card-header").first

    # ==================== Initial Load Tests ====================

    def test_page_title(self) -> None:
        """Page has correct title."""
        expect(self.page).to_have_title("Titanic Dataset Explorer")

    def test_welcome_message_appears(self) -> None:
        """Chat shows LLM greeting."""
        expect(self.chat.loc_messages).to_contain_text("Hello", timeout=30000)

    def test_card_header_initial(self) -> None:
        """Card header shows 'Titanic Dataset' initially."""
        expect(self.card_header).to_contain_text("Titanic Dataset")

    def test_data_table_visible(self) -> None:
        """Data table is visible with rows."""
        table = self.page.locator("table")
        expect(table).to_be_visible()
        rows = self.page.locator("table tbody tr")
        expect(rows.first).to_be_visible()

    def test_chat_input_visible(self) -> None:
        """Chat input is visible with placeholder."""
        expect(self.chat.loc_input).to_be_visible()
        expect(self.chat.loc_input).to_have_attribute(
            "placeholder", "Enter a message..."
        )

    def test_sidebar_layout(self) -> None:
        """Page uses sidebar layout."""
        sidebar = self.page.locator(".bslib-sidebar-layout")
        expect(sidebar).to_be_visible()

    # ==================== Query Tests ====================

    def test_filter_query_updates_title(self) -> None:
        """Filter query updates the card header title."""
        # Verify initial title
        expect(self.card_header).to_contain_text("Titanic Dataset")

        # Submit a filter query
        self.chat.set_user_input("Show only female passengers")
        self.chat.send_user_input(method="click")

        # Title should update to reflect the filter
        expect(self.card_header).not_to_have_text("Titanic Dataset", timeout=60000)

    def test_filter_query_updates_table(self) -> None:
        """Filter query updates the data table."""
        # Submit a filter query
        self.chat.set_user_input("Show only first class passengers")
        self.chat.send_user_input(method="click")

        # Wait for response in chat
        self.chat.expect_latest_message(
            re.compile(r"first|class|filter", re.IGNORECASE), timeout=60000
        )

        # Table should still be visible (with filtered data)
        table = self.page.locator("table")
        expect(table).to_be_visible()

    def test_analytical_query_in_chat(self) -> None:
        """Analytical query shows result in chat."""
        self.chat.set_user_input("How many passengers survived?")
        self.chat.send_user_input(method="click")

        # Response should contain survival info
        self.chat.expect_latest_message(
            re.compile(r"survived|survival|\d+", re.IGNORECASE), timeout=60000
        )


class Test03SidebarCore:
    """Tests for 03-sidebar-core-app.py - Shiny Core with sidebar layout."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_03_core: str, chat_03_core: ChatController
    ) -> None:
        """Navigate to the app before each test."""
        page.goto(app_03_core)
        # Wait for Shiny data frame to be ready (uses shiny-data-frame custom element)
        page.wait_for_selector("shiny-data-frame table", timeout=15000)
        self.page = page
        self.chat = chat_03_core
        # Card header selector (first .card-header div, not buttons)
        self.card_header = page.locator(".card-header").first

    # ==================== Initial Load Tests ====================

    def test_welcome_message_appears(self) -> None:
        """Chat shows LLM greeting."""
        expect(self.chat.loc_messages).to_contain_text("Hello", timeout=30000)

    def test_card_header_initial(self) -> None:
        """Card header shows 'Titanic Dataset' initially."""
        expect(self.card_header).to_contain_text("Titanic Dataset")

    def test_data_table_visible(self) -> None:
        """Data table is visible with rows."""
        table = self.page.locator("table")
        expect(table).to_be_visible()
        rows = self.page.locator("table tbody tr")
        expect(rows.first).to_be_visible()

    def test_chat_input_visible(self) -> None:
        """Chat input is visible with placeholder."""
        expect(self.chat.loc_input).to_be_visible()
        expect(self.chat.loc_input).to_have_attribute(
            "placeholder", "Enter a message..."
        )

    def test_sidebar_layout(self) -> None:
        """Page uses sidebar layout."""
        sidebar = self.page.locator(".bslib-sidebar-layout")
        expect(sidebar).to_be_visible()

    # ==================== Query Tests ====================

    def test_filter_query_updates_title(self) -> None:
        """Filter query updates the card header title."""
        # Verify initial title
        expect(self.card_header).to_contain_text("Titanic Dataset")

        # Submit a filter query
        self.chat.set_user_input("Show survivors only")
        self.chat.send_user_input(method="click")

        # Title should update to reflect the filter
        expect(self.card_header).not_to_have_text("Titanic Dataset", timeout=60000)

    def test_filter_query_updates_table(self) -> None:
        """Filter query updates the data table."""
        # Submit a filter query
        self.chat.set_user_input("Show male passengers only")
        self.chat.send_user_input(method="click")

        # Wait for response in chat
        self.chat.expect_latest_message(
            re.compile(r"male|filter|showing", re.IGNORECASE), timeout=60000
        )

        # Table should still be visible (with filtered data)
        table = self.page.locator("table")
        expect(table).to_be_visible()

    def test_analytical_query_in_chat(self) -> None:
        """Analytical query shows result in chat."""
        self.chat.set_user_input("What is the average fare?")
        self.chat.send_user_input(method="click")

        # Response should contain fare info
        self.chat.expect_latest_message(
            re.compile(r"average|fare|\d+\.?\d*", re.IGNORECASE), timeout=60000
        )
