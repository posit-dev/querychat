"""
Playwright tests for 01-hello-app.py - Basic QueryChat example.

This tests the simplest querychat example with the Titanic dataset.
Uses shinychat.playwright.ChatController for chat interactions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class Test01HelloApp:
    """Tests for 01-hello-app.py - Basic QueryChat example."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_01_hello: str, chat_01_hello: ChatController
    ) -> None:
        """Navigate to the app before each test."""
        page.goto(app_01_hello)
        page.wait_for_selector("table", timeout=10000)
        self.page = page
        self.chat = chat_01_hello

    # ==================== Initial Load Tests ====================

    def test_app_loads_successfully(self) -> None:
        """INIT-01: App loads without errors."""
        expect(self.page.locator("body")).to_be_visible()
        expect(self.page.locator("table")).to_be_visible()

    def test_welcome_message_appears(self) -> None:
        """INIT-02: Chat shows LLM greeting."""
        greeting = self.chat.loc.locator(".shiny-chat-greeting")
        expect(greeting).to_contain_text("Hello", timeout=30000)

    def test_default_sql_query_shown(self) -> None:
        """INIT-03: SQL panel shows default query."""
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text("SELECT * FROM titanic")

    def test_data_table_populated(self) -> None:
        """INIT-04: Table shows data rows."""
        rows = self.page.locator("table tbody tr")
        expect(rows.first).to_be_visible()

    def test_row_count_displayed(self) -> None:
        """INIT-05: Row count indicator visible."""
        expect(self.page.locator("text=Viewing rows")).to_be_visible()
        expect(self.page.locator("text=891")).to_be_visible()

    def test_chat_input_visible(self) -> None:
        """INIT-06: Chat input is visible with placeholder."""
        expect(self.chat.loc_input).to_be_visible()
        expect(self.chat.loc_input).to_have_attribute(
            "data-placeholder", "Enter a message..."
        )

    def test_suggestion_links_present(self) -> None:
        """INIT-07: Suggestions are visible in greeting."""
        greeting = self.chat.loc.locator(".shiny-chat-greeting")
        expect(greeting).to_contain_text(
            re.compile(r"survived|class|age", re.IGNORECASE), timeout=30000
        )

    # ==================== Chat Input Tests ====================

    def test_type_in_chat_input(self) -> None:
        """CHAT-01: Can type text into chat input."""
        self.chat.set_user_input("test query")
        self.chat.expect_user_input("test query")

    def test_submit_via_send_button(self) -> None:
        """CHAT-02: Submit query via send button."""
        self.chat.set_user_input("Show only female passengers")
        self.chat.send_user_input(method="click")

        # SQL should filter by sex = 'female'
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE),
            timeout=60000,
        )

    def test_submit_via_click_survivors(self) -> None:
        """CHAT-03: Submit another query via click button."""
        self.chat.set_user_input("Show survivors only")
        self.chat.send_user_input(method="click")

        # SQL should filter by survived = 1 (or TRUE)
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*survived.*=.*(1|TRUE)", re.IGNORECASE), timeout=60000
        )

    # ==================== Query Processing Tests ====================

    def test_filter_query(self) -> None:
        """QUERY-01: Filter query updates SQL and data."""
        self.chat.set_user_input("Show passengers who survived")
        self.chat.send_user_input(method="click")

        # SQL should filter by survived = 1 (or TRUE)
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*survived.*=.*(1|TRUE)", re.IGNORECASE), timeout=60000
        )

    def test_aggregation_query(self) -> None:
        """QUERY-02: Aggregation query result appears in chat."""
        self.chat.set_user_input("What is the average age of passengers?")
        self.chat.send_user_input(method="click")

        # Analytical queries show results in chat, not SQL panel
        # Response should contain the average age (a number)
        self.chat.expect_latest_message(
            re.compile(r"average|age|\d+\.?\d*", re.IGNORECASE), timeout=60000
        )

    def test_group_by_query(self) -> None:
        """QUERY-03: Group by query result appears in chat."""
        self.chat.set_user_input("Count passengers by class")
        self.chat.send_user_input(method="click")

        # Analytical queries show results in chat, not SQL panel
        # Response should mention class or count
        self.chat.expect_latest_message(
            re.compile(r"class|count|first|second|third|\d+", re.IGNORECASE),
            timeout=60000,
        )

    def test_latest_message_after_query(self) -> None:
        """CHAT-05: Response appears in chat after query."""
        self.chat.set_user_input("Show first class passengers")
        self.chat.send_user_input(method="click")

        # SQL should filter by class/pclass = 1 or 'First'
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE),
            timeout=60000,
        )

        # Response should mention the query topic
        self.chat.expect_latest_message(
            re.compile(r"(first|class|passenger)", re.IGNORECASE), timeout=60000
        )

    # ==================== Data Table Tests ====================

    def test_column_headers_visible(self) -> None:
        """DATA-01: All expected columns shown."""
        headers = self.page.locator("table thead th")
        expect(headers.first).to_be_visible()

        # Check for key columns
        expect(self.page.locator("th:has-text('survived')")).to_be_visible()
        expect(self.page.locator("th:has-text('pclass')")).to_be_visible()
        expect(self.page.locator("th:has-text('sex')")).to_be_visible()

    def test_table_updates_on_query(self) -> None:
        """DATA-04: Table updates after filter query."""
        # Get initial row count text
        initial_count = self.page.locator("text=Viewing rows").text_content()

        self.chat.set_user_input("Show only passengers from first class")
        self.chat.send_user_input(method="click")

        # SQL should filter by class/pclass = 1 or 'First'
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE),
            timeout=60000,
        )

        # Row count should change (fewer than 891)
        expect(self.page.locator("text=Viewing rows")).not_to_have_text(
            initial_count, timeout=60000
        )

    # ==================== SQL Panel Tests ====================

    def test_sql_updates_on_query(self) -> None:
        """SQL-03: SQL panel updates after query."""
        self.chat.set_user_input("Show male passengers only")
        self.chat.send_user_input(method="click")

        # SQL should filter by sex = 'male'
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?male['\"]?", re.IGNORECASE), timeout=60000
        )

    # ==================== Filter Button Tests ====================

    def test_apply_filter_button_re_applies_filter(self) -> None:
        """FILTER-01: Apply Filter button re-applies the filter after a reset."""
        self.chat.set_user_input("Show only first class passengers")
        self.chat.send_user_input(method="click")

        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE),
            timeout=60000,
        )

        apply_btn = self.page.locator(".querychat-update-dashboard-btn").first
        expect(apply_btn).to_be_visible(timeout=10000)
        assert apply_btn.get_attribute("data-table") == "titanic"
        assert apply_btn.get_attribute("data-query") not in (None, "")

        # Reset the filter directly via Shiny JS (no second LLM call)
        self.page.evaluate(
            """
            window.Shiny.setInputValue(
                'querychat_titanic-chat_update',
                {table: 'titanic', query: '', title: ''},
                {priority: 'event'}
            );
            """
        )
        expect(self.page.locator("text=891")).to_be_visible(timeout=10000)

        apply_btn.click()

        expect(self.page.locator("text=891")).not_to_be_visible(timeout=5000)

    # ==================== Stream Cancellation Tests ====================

    def test_stop_button_appears_during_streaming(self) -> None:
        """CANCEL-01: The stop button should be visible while the LLM is streaming."""
        self.chat.set_user_input(
            "Write a very long and detailed paragraph about every column "
            "in this dataset. Be extremely thorough and verbose."
        )
        self.chat.send_user_input(method="click")

        stop_btn = self.page.locator(".shiny-chat-btn-cancel")
        expect(stop_btn).to_be_visible(timeout=30000)

    def test_cancel_stops_response(self) -> None:
        """CANCEL-02: Clicking the stop button should cancel the stream."""
        self.chat.set_user_input(
            "Write a very long and detailed paragraph about every column "
            "in this dataset. Be extremely thorough and verbose."
        )
        self.chat.send_user_input(method="click")

        stop_btn = self.page.locator(".shiny-chat-btn-cancel")
        expect(stop_btn).to_be_visible(timeout=30000)
        stop_btn.click()

        cancelled = self.page.locator(".shiny-chat-message-cancelled")
        expect(cancelled).to_be_visible(timeout=15000)
        expect(cancelled).to_have_text("Response cancelled")

    def test_can_send_after_cancel(self) -> None:
        """CANCEL-03: After cancelling, the user should be able to send another message."""
        self.chat.set_user_input(
            "Write a very long and detailed paragraph about every column "
            "in this dataset. Be extremely thorough and verbose."
        )
        self.chat.send_user_input(method="click")

        stop_btn = self.page.locator(".shiny-chat-btn-cancel")
        expect(stop_btn).to_be_visible(timeout=30000)
        stop_btn.click()

        cancelled = self.page.locator(".shiny-chat-message-cancelled")
        expect(cancelled).to_be_visible(timeout=15000)

        self.chat.set_user_input("How many rows are in the dataset?")
        self.chat.send_user_input(method="click")

        send_btn = self.page.locator(
            ".shiny-chat-btn-send:not(.shiny-chat-btn-cancel)"
        )
        expect(send_btn).to_be_visible(timeout=60000)
