"""
Playwright tests for 05-gradio-app.py and 07-gradio-custom-app.py.

Gradio apps use different DOM structure:
- Chat messages: [data-testid="bot"] for bot messages
- Chat input: textarea with placeholder "Ask a question about your data..."
- Submit: Press Enter key
- Code blocks: code elements (basic app) or .cm-content (custom app with gr.Code)
- Tables: table elements

The basic app (05) uses gr.Chatbot which includes code blocks in messages.
The custom app (07) uses gr.Code with CodeMirror for SQL display.
Note: Custom app's .ui() does NOT auto-generate greeting (chat starts empty).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


class Test05GradioBasic:
    """Tests for 05-gradio-app.py - Basic Gradio QueryChat example."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_05_gradio: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_05_gradio)
        # Wait for Gradio app to load
        page.wait_for_selector("gradio-app", timeout=30000)
        # Wait for bot greeting message
        page.wait_for_selector('[data-testid="bot"]', timeout=30000)
        self.page = page

    # ==================== Initial Load Tests ====================

    def test_app_loads_successfully(self) -> None:
        """App loads without errors."""
        expect(self.page.locator("gradio-app")).to_be_visible()

    def test_welcome_message_appears(self) -> None:
        """Chat shows LLM greeting."""
        bot_msg = self.page.locator('[data-testid="bot"]').first
        expect(bot_msg).to_contain_text("Hello", timeout=30000)

    def test_chat_input_visible(self) -> None:
        """Chat input is visible with placeholder."""
        chat_input = self.page.locator("textarea").first
        expect(chat_input).to_be_visible()
        expect(chat_input).to_have_attribute(
            "placeholder", "Ask a question about your data..."
        )

    def test_data_table_visible(self) -> None:
        """Data table is visible."""
        table = self.page.locator("table").first
        expect(table).to_be_visible()

    def test_suggestion_links_present(self) -> None:
        """Suggestions are visible in greeting."""
        bot_msg = self.page.locator('[data-testid="bot"]').first
        expect(bot_msg).to_contain_text(
            re.compile(r"survived|class|age|passenger|filter", re.IGNORECASE),
            timeout=30000,
        )

    # ==================== Chat Input Tests ====================

    def test_type_in_chat_input(self) -> None:
        """Can type text into chat input."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("test query")
        expect(chat_input).to_have_value("test query")

    def test_submit_query_via_enter(self) -> None:
        """Submit query via Enter key."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("Show only female passengers")
        chat_input.press("Enter")

        # Wait for response - should have 2 bot messages now (greeting + response)
        bot_msgs = self.page.locator('[data-testid="bot"]')
        expect(bot_msgs).to_have_count(2, timeout=60000)

    # ==================== Query Processing Tests ====================

    def test_filter_query_updates_sql(self) -> None:
        """Filter query shows SQL in response."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("Show only female passengers")
        chat_input.press("Enter")

        # SQL should appear in code block with WHERE clause
        code = self.page.locator("code").first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE),
            timeout=60000,
        )

    def test_filter_survivors(self) -> None:
        """Filter for survivors updates SQL."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("Show survivors only")
        chat_input.press("Enter")

        # SQL should filter by survived = 1
        code = self.page.locator("code").first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*survived.*=.*1|TRUE", re.IGNORECASE), timeout=60000
        )

    def test_filter_first_class(self) -> None:
        """Filter for first class passengers."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("Show first class passengers")
        chat_input.press("Enter")

        # SQL should filter by class/pclass = 1 or 'First'
        code = self.page.locator("code").first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE),
            timeout=60000,
        )

    def test_analytical_query_in_chat(self) -> None:
        """Analytical query shows result in chat."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("How many passengers survived?")
        chat_input.press("Enter")

        # Wait for response
        bot_msgs = self.page.locator('[data-testid="bot"]')
        expect(bot_msgs).to_have_count(2, timeout=60000)

        # Response should contain survival info
        latest_msg = bot_msgs.last
        expect(latest_msg).to_contain_text(
            re.compile(r"survived|survival|\d+", re.IGNORECASE), timeout=60000
        )

    def test_filter_male_passengers(self) -> None:
        """Filter for male passengers updates SQL."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("Show male passengers only")
        chat_input.press("Enter")

        # SQL should filter by sex = 'male'
        code = self.page.locator("code").first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?male['\"]?", re.IGNORECASE),
            timeout=60000,
        )


class Test07GradioCustom:
    """
    Tests for 07-gradio-custom-app.py - Custom Gradio layout.

    Uses .ui() which creates a chat component without auto-greeting.
    SQL is displayed in a gr.Code component using CodeMirror.
    """

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_07_gradio_custom: str) -> None:
        """Navigate to the app before each test."""
        page.goto(app_07_gradio_custom)
        # Wait for Gradio app to load
        page.wait_for_selector("gradio-app", timeout=30000)
        # Wait for load callback to populate SQL and data
        page.wait_for_selector(".cm-content", timeout=30000)
        # Wait for data table to be populated (indicates load callback completed)
        page.wait_for_selector("table tbody tr", timeout=30000)
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
        chat_input = self.page.locator("textarea").first
        expect(chat_input).to_be_visible()

    def test_sql_code_visible(self) -> None:
        """SQL code block shows default query (CodeMirror)."""
        # Gradio Code component uses CodeMirror
        code = self.page.locator(".cm-content").first
        expect(code).to_contain_text("SELECT * FROM titanic")

    def test_data_table_visible(self) -> None:
        """Data table is visible."""
        table = self.page.locator("table").first
        expect(table).to_be_visible()

    def test_row_count_displayed(self) -> None:
        """Row count is displayed."""
        # Row count is in a textbox labeled "Rows"
        rows_label = self.page.get_by_label("Rows")
        expect(rows_label).to_be_visible()
        # Value should be 891 (with optional comma formatting)
        expect(rows_label).to_have_value(re.compile(r"891"))

    def test_column_count_displayed(self) -> None:
        """Column count is displayed."""
        # Column count is in a textbox labeled "Columns"
        cols_label = self.page.get_by_label("Columns")
        expect(cols_label).to_be_visible()
        # Titanic has 15 columns
        expect(cols_label).to_have_value("15")

    def test_query_title_displayed(self) -> None:
        """Query title shows 'Full Dataset' initially."""
        h3 = self.page.locator("h3").first
        expect(h3).to_contain_text("Full Dataset")

    # ==================== Query Tests ====================

    def test_filter_query_updates_sql(self) -> None:
        """Filter query updates SQL code block."""
        chat_input = self.page.locator("textarea").first
        chat_input.fill("Show only female passengers")
        chat_input.press("Enter")

        # SQL should update with WHERE clause (CodeMirror)
        code = self.page.locator(".cm-content").first
        expect(code).to_contain_text(
            re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE),
            timeout=60000,
        )

    def test_filter_query_updates_title(self) -> None:
        """Filter query updates the header title."""
        # Initial header should be "Full Dataset"
        h3 = self.page.locator("h3").first
        expect(h3).to_contain_text("Full Dataset")

        chat_input = self.page.locator("textarea").first
        chat_input.fill("Show survivors only")
        chat_input.press("Enter")

        # Header should update to reflect the filter
        expect(h3).not_to_have_text("Full Dataset", timeout=60000)
