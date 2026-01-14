"""
Playwright tests for 04-streamlit-app.py and 09-streamlit-custom-app.py.

Streamlit apps use different DOM structure than Shiny:
- Chat input: [data-testid="stChatInputTextArea"]
- Submit button: [data-testid="stChatInputSubmitButton"]
- Chat messages: [data-testid="stChatMessage"]
- DataFrame: [data-testid="stDataFrame"]
- Code blocks: [data-testid="stCode"]

"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


class Test04StreamlitBasic:
    """Tests for 04-streamlit-app.py - Basic Streamlit QueryChat example."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_04_streamlit: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_04_streamlit)
        # Wait for Streamlit app to load
        page.wait_for_selector('[data-testid="stApp"]', timeout=30000)
        # Wait for chat message (greeting) to appear
        page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
        # Wait for DataFrame to be rendered
        page.wait_for_selector('[data-testid="stDataFrame"]', timeout=30000)
        self.page = page

    # ==================== Initial Load Tests ====================

    def test_app_loads_successfully(self) -> None:
        """App loads without errors."""
        expect(self.page.locator('[data-testid="stApp"]')).to_be_visible()

    def test_welcome_message_appears(self) -> None:
        """Chat shows LLM greeting."""
        messages = self.page.locator('[data-testid="stChatMessage"]')
        expect(messages.first).to_contain_text("Hello", timeout=30000)

    def test_data_frame_visible(self) -> None:
        """Data frame is visible."""
        df = self.page.locator('[data-testid="stDataFrame"]')
        expect(df).to_be_visible()

    def test_sql_code_visible(self) -> None:
        """SQL code block is visible with default query."""
        code = self.page.locator('[data-testid="stCode"]')
        expect(code).to_be_visible()
        expect(code).to_contain_text("SELECT * FROM titanic")

    def test_chat_input_visible(self) -> None:
        """Chat input is visible."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        expect(chat_input).to_be_visible()

    def test_suggestion_links_present(self) -> None:
        """Suggestions are visible in greeting."""
        messages = self.page.locator('[data-testid="stChatMessage"]')
        expect(messages.first).to_contain_text(
            re.compile(r"survived|class|age|passenger", re.IGNORECASE), timeout=30000
        )

    # ==================== Chat Input Tests ====================

    def test_type_in_chat_input(self) -> None:
        """Can type text into chat input."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        chat_input.fill("test query")
        expect(chat_input).to_have_value("test query")

    def test_submit_query_via_button(self) -> None:
        """Submit query via send button updates SQL."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("Show only female passengers")
        submit_btn.click()

        # SQL should update to include WHERE clause with sex = 'female'
        # Use .first because there may be multiple code blocks (one in chat, one in main)
        code = self.page.locator('[data-testid="stCode"]').first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE),
            timeout=60000,
        )

    def test_submit_query_via_enter(self) -> None:
        """Submit query via Enter key updates SQL."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')

        chat_input.fill("Show survivors only")
        chat_input.press("Enter")

        # SQL should update to include WHERE clause with survived = 1
        code = self.page.locator('[data-testid="stCode"]').first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*survived.*=.*1|TRUE", re.IGNORECASE), timeout=60000
        )

    # ==================== Query Processing Tests ====================

    def test_filter_query_updates_sql(self) -> None:
        """Filter query updates SQL panel."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("Show first class passengers")
        submit_btn.click()

        # SQL should filter by class/pclass = 1 or 'First'
        code = self.page.locator('[data-testid="stCode"]').first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE),
            timeout=60000,
        )

    def test_analytical_query_in_chat(self) -> None:
        """Analytical query shows result in chat."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("How many passengers survived?")
        submit_btn.click()

        # Wait for new assistant message with response
        messages = self.page.locator('[data-testid="stChatMessage"]')
        # Should have more than just the greeting now
        expect(messages).to_have_count(3, timeout=60000)  # greeting + user + assistant

        # Latest message should contain survival info
        latest_msg = messages.last
        expect(latest_msg).to_contain_text(
            re.compile(r"survived|survival|\d+", re.IGNORECASE), timeout=60000
        )

    def test_response_appears_in_chat(self) -> None:
        """Response appears in chat after query."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("Show male passengers only")
        submit_btn.click()

        # SQL should update with sex = 'male'
        code = self.page.locator('[data-testid="stCode"]').first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?male['\"]?", re.IGNORECASE),
            timeout=60000,
        )


class Test09StreamlitCustom:
    """Tests for 09-streamlit-custom-app.py - Custom Streamlit layout."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_09_streamlit_custom: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_09_streamlit_custom)
        # Wait for Streamlit app to load
        page.wait_for_selector('[data-testid="stApp"]', timeout=30000)
        # Wait for main content to load
        page.wait_for_selector('[data-testid="stDataFrame"]', timeout=30000)
        self.page = page

    # ==================== Initial Load Tests ====================

    def test_page_title(self) -> None:
        """Page has correct title."""
        expect(self.page).to_have_title("Titanic Explorer")

    def test_main_heading(self) -> None:
        """Main heading is visible."""
        h1 = self.page.locator("h1")
        expect(h1).to_contain_text("Titanic Data Explorer")

    def test_welcome_message_in_sidebar(self) -> None:
        """Chat shows LLM greeting in sidebar."""
        sidebar = self.page.locator('[data-testid="stSidebar"]')
        messages = sidebar.locator('[data-testid="stChatMessage"]')
        expect(messages.first).to_contain_text("Hello", timeout=30000)

    def test_data_frame_visible(self) -> None:
        """Data frame is visible in main area."""
        df = self.page.locator('[data-testid="stDataFrame"]')
        expect(df).to_be_visible()

    def test_sql_code_visible(self) -> None:
        """SQL code block is visible with default query."""
        code = self.page.locator('[data-testid="stCode"]')
        expect(code).to_be_visible()
        expect(code).to_contain_text("SELECT * FROM titanic")

    def test_metrics_visible(self) -> None:
        """Quick stats metrics are visible."""
        metrics = self.page.locator('[data-testid="stMetricValue"]')
        expect(metrics).to_have_count(2)  # Total Rows and Total Columns
        # Check row count (891)
        expect(metrics.first).to_contain_text("891")

    def test_chat_input_in_sidebar(self) -> None:
        """Chat input is visible in sidebar."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        expect(chat_input).to_be_visible()

    def test_section_headers(self) -> None:
        """Section headers are visible."""
        expect(self.page.locator("h3:has-text('Current Query')")).to_be_visible()
        expect(self.page.locator("h3:has-text('Quick Stats')")).to_be_visible()
        expect(self.page.locator("h3:has-text('Data Preview')")).to_be_visible()

    # ==================== Query Tests ====================

    def test_filter_query_updates_sql(self) -> None:
        """Filter query updates SQL code block."""
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("Show only female passengers")
        submit_btn.click()

        # SQL should update with sex = 'female'
        # Use .first because there may be multiple code blocks after query
        code = self.page.locator('[data-testid="stCode"]').first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE),
            timeout=60000,
        )

    def test_filter_query_updates_title(self) -> None:
        """Filter query updates the header title."""
        # Initial header should be "Full Dataset"
        h2 = self.page.locator("h2")
        expect(h2).to_contain_text("Full Dataset")

        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("Show survivors only")
        submit_btn.click()

        # Header should update to reflect the filter
        expect(h2).not_to_have_text("Full Dataset", timeout=60000)

    def test_filter_query_updates_metrics(self) -> None:
        """Filter query updates the row count metric."""
        metrics = self.page.locator('[data-testid="stMetricValue"]')
        # Initial row count is 891
        expect(metrics.first).to_contain_text("891")

        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("Show first class passengers only")
        submit_btn.click()

        # Row count should decrease (fewer than 891)
        expect(metrics.first).not_to_have_text("891", timeout=60000)

    def test_analytical_query_in_chat(self) -> None:
        """Analytical query shows result in chat."""
        sidebar = self.page.locator('[data-testid="stSidebar"]')
        chat_input = self.page.locator('[data-testid="stChatInputTextArea"]')
        submit_btn = self.page.locator('[data-testid="stChatInputSubmitButton"]')

        chat_input.fill("What is the average age?")
        submit_btn.click()

        # Wait for response in sidebar chat
        messages = sidebar.locator('[data-testid="stChatMessage"]')
        expect(messages).to_have_count(3, timeout=60000)  # greeting + user + assistant

        # Response should contain age info
        latest_msg = messages.last
        expect(latest_msg).to_contain_text(
            re.compile(r"average|age|\d+\.?\d*", re.IGNORECASE), timeout=60000
        )
