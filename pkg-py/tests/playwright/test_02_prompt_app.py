"""
Playwright tests for 02-prompt-app.py - Custom prompt example.

Tests the example that uses custom greeting and data description files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class Test02PromptApp:
    """Tests for 02-prompt-app.py - Custom prompt example."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_02_prompt: str, chat_02_prompt: ChatController
    ) -> None:
        """Navigate to the app before each test."""
        page.goto(app_02_prompt)
        page.wait_for_selector("table", timeout=10000)
        self.page = page
        self.chat = chat_02_prompt

    def test_app_loads_successfully(self) -> None:
        """INIT-01: App loads without errors."""
        expect(self.page.locator("body")).to_be_visible()
        expect(self.page.locator("table")).to_be_visible()

    def test_custom_greeting_appears(self) -> None:
        """INIT-02: Custom greeting from greeting.md is shown."""
        # The custom greeting should contain content from greeting.md
        expect(self.chat.loc_messages).to_contain_text("Hello", timeout=30000)

    def test_default_sql_query_shown(self) -> None:
        """INIT-03: SQL panel shows default query."""
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text("SELECT * FROM titanic")

    def test_chat_input_visible(self) -> None:
        """INIT-04: Chat input is visible."""
        expect(self.chat.loc_input).to_be_visible()
