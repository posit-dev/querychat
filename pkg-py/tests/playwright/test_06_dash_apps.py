"""
Playwright tests for 06-dash-app.py and 08-dash-custom-app.py.

Dash apps use specific element IDs for the querychat components:
- Chat history: #querychat-{table}-chat-history
- Chat input: #querychat-{table}-chat-input (INPUT element)
- Send button: #querychat-{table}-send-button
- SQL display: #querychat-{table}-sql-display
- Data table: #querychat-{table}-data-table

The basic app (06) uses .app() which auto-generates greeting.
The custom app (08) uses .ui() which does NOT auto-generate greeting.
Custom components (#sql-display, #row-count, etc.) are populated via callbacks.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


class Test06DashBasic:
    """Tests for 06-dash-app.py - Basic Dash QueryChat example."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_06_dash: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_06_dash)
        # Wait for Dash app to fully load (chat history and data table)
        page.wait_for_selector("#querychat-titanic-chat-history", timeout=30000)
        # AG Grid data table loads asynchronously - wait for it
        page.wait_for_selector("#querychat-titanic-data-table .ag-body-viewport", timeout=30000)
        # Wait for SQL display to be populated by callback
        expect(page.locator("#querychat-titanic-sql-display")).to_contain_text(
            "SELECT", timeout=30000
        )
        self.page = page

    # ==================== Initial Load Tests ====================

    def test_app_loads_successfully(self) -> None:
        """App loads without errors."""
        expect(self.page.locator("#react-entry-point")).to_be_visible()

    def test_welcome_message_appears(self) -> None:
        """Chat shows LLM greeting."""
        chat_history = self.page.locator("#querychat-titanic-chat-history")
        expect(chat_history).to_contain_text("Hello", timeout=30000)

    def test_chat_input_visible(self) -> None:
        """Chat input is visible."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        expect(chat_input).to_be_visible()

    def test_send_button_visible(self) -> None:
        """Send button is visible."""
        send_btn = self.page.locator("#querychat-titanic-send-button")
        expect(send_btn).to_be_visible()

    def test_sql_display_visible(self) -> None:
        """SQL display shows default query."""
        sql_display = self.page.locator("#querychat-titanic-sql-display")
        expect(sql_display).to_be_visible()
        expect(sql_display).to_contain_text("SELECT * FROM titanic")

    def test_data_table_visible(self) -> None:
        """Data table is visible."""
        # AG Grid uses custom DOM structure, not standard <table>
        data_table = self.page.locator("#querychat-titanic-data-table .ag-body-viewport")
        expect(data_table).to_be_visible()

    def test_suggestion_links_present(self) -> None:
        """Suggestions are visible in greeting."""
        chat_history = self.page.locator("#querychat-titanic-chat-history")
        expect(chat_history).to_contain_text(
            re.compile(r"survived|class|age|passenger|filter", re.IGNORECASE),
            timeout=30000,
        )

    # ==================== Chat Input Tests ====================

    def test_type_in_chat_input(self) -> None:
        """Can type text into chat input."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        chat_input.fill("test query")
        expect(chat_input).to_have_value("test query")

    def test_submit_query_via_button(self) -> None:
        """Submit query via send button."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        send_btn = self.page.locator("#querychat-titanic-send-button")

        chat_input.fill("Show only female passengers")
        send_btn.click()

        # SQL should update with WHERE clause
        sql_display = self.page.locator("#querychat-titanic-sql-display")
        expect(sql_display).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE),
            timeout=60000,
        )

    def test_submit_query_via_enter(self) -> None:
        """Submit query via Enter key."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")

        chat_input.fill("Show survivors only")
        chat_input.press("Enter")

        # SQL should update with survived = 1
        sql_display = self.page.locator("#querychat-titanic-sql-display")
        expect(sql_display).to_contain_text(
            re.compile(r"WHERE.*survived.*=.*(1|TRUE)", re.IGNORECASE), timeout=60000
        )

    # ==================== Query Processing Tests ====================

    def test_filter_first_class(self) -> None:
        """Filter for first class passengers."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        send_btn = self.page.locator("#querychat-titanic-send-button")

        chat_input.fill("Show first class passengers")
        send_btn.click()

        # SQL should filter by class/pclass
        sql_display = self.page.locator("#querychat-titanic-sql-display")
        expect(sql_display).to_contain_text(
            re.compile(r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE),
            timeout=60000,
        )

    def test_analytical_query_in_chat(self) -> None:
        """Analytical query shows result in chat."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        send_btn = self.page.locator("#querychat-titanic-send-button")

        chat_input.fill("How many passengers survived?")
        send_btn.click()

        # Response should contain survival info in chat history
        chat_history = self.page.locator("#querychat-titanic-chat-history")
        expect(chat_history).to_contain_text(
            re.compile(r"survived|survival|\d+", re.IGNORECASE), timeout=60000
        )

    def test_filter_male_passengers(self) -> None:
        """Filter for male passengers."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        send_btn = self.page.locator("#querychat-titanic-send-button")

        chat_input.fill("Show male passengers only")
        send_btn.click()

        # SQL should filter by sex = 'male'
        sql_display = self.page.locator("#querychat-titanic-sql-display")
        expect(sql_display).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?male['\"]?", re.IGNORECASE),
            timeout=60000,
        )


class Test08DashCustom:
    """
    Tests for 08-dash-custom-app.py - Custom Dash layout.

    Uses .ui() which creates a chat component without auto-greeting.
    Custom elements (#sql-display, #row-count, etc.) are populated via callbacks.
    """

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_08_dash_custom: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_08_dash_custom)
        # Wait for Dash app to load and callback to populate data
        page.wait_for_selector("#react-entry-point", timeout=30000)
        # Wait for the callback to populate the SQL display with actual content
        sql_display = page.locator("#sql-display")
        expect(sql_display).to_contain_text("SELECT", timeout=30000)
        self.page = page

    # ==================== Initial Load Tests ====================

    def test_page_title(self) -> None:
        """Page has correct title."""
        expect(self.page).to_have_title("Titanic Explorer")

    def test_main_heading(self) -> None:
        """Main heading is visible."""
        h1 = self.page.locator("h1")
        expect(h1).to_contain_text("Titanic Data Explorer")

    def test_chat_input_visible(self) -> None:
        """Chat input is visible."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        expect(chat_input).to_be_visible()

    def test_send_button_visible(self) -> None:
        """Send button is visible."""
        send_btn = self.page.locator("#querychat-titanic-send-button")
        expect(send_btn).to_be_visible()
        expect(send_btn).to_contain_text("Send")

    def test_sql_display_visible(self) -> None:
        """SQL display shows default query."""
        sql_display = self.page.locator("#sql-display")
        expect(sql_display).to_contain_text("SELECT * FROM titanic")

    def test_row_count_visible(self) -> None:
        """Row count is visible."""
        row_count = self.page.locator("#row-count")
        expect(row_count).to_contain_text("891")

    def test_column_count_visible(self) -> None:
        """Column count is visible."""
        col_count = self.page.locator("#col-count")
        expect(col_count).to_contain_text("15")

    def test_query_title_visible(self) -> None:
        """Query title shows 'Full Dataset' initially."""
        title = self.page.locator("#query-title")
        expect(title).to_contain_text("Full Dataset")

    def test_data_table_visible(self) -> None:
        """Data table is visible."""
        data_table = self.page.locator("#data-table table")
        expect(data_table).to_be_visible()

    # ==================== Query Tests ====================

    def test_filter_query_updates_sql(self) -> None:
        """Filter query updates SQL display."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        send_btn = self.page.locator("#querychat-titanic-send-button")

        chat_input.fill("Show only female passengers")
        send_btn.click()

        # SQL should update with WHERE clause
        sql_display = self.page.locator("#sql-display")
        expect(sql_display).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE),
            timeout=60000,
        )

    def test_filter_query_updates_title(self) -> None:
        """Filter query updates the header title."""
        # Initial title
        title = self.page.locator("#query-title")
        expect(title).to_contain_text("Full Dataset")

        chat_input = self.page.locator("#querychat-titanic-chat-input")
        send_btn = self.page.locator("#querychat-titanic-send-button")

        chat_input.fill("Show survivors only")
        send_btn.click()

        # Title should update
        expect(title).not_to_have_text("Full Dataset", timeout=60000)

    def test_filter_query_updates_row_count(self) -> None:
        """Filter query updates row count."""
        chat_input = self.page.locator("#querychat-titanic-chat-input")
        send_btn = self.page.locator("#querychat-titanic-send-button")

        chat_input.fill("Show only female passengers")
        send_btn.click()

        # Row count should change from 891 to something smaller
        row_count = self.page.locator("#row-count")
        expect(row_count).not_to_have_text("891", timeout=60000)
