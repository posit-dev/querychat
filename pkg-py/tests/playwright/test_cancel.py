"""
Playwright tests for stream cancellation.

Verifies that the stop button appears during streaming and that
clicking it cancels the response.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class TestStreamCancellation:
    """Tests for stream cancellation in querychat."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_cancel: str, chat_cancel: ChatController
    ) -> None:
        """Navigate to the app before each test."""
        page.goto(app_cancel)
        self.page = page
        self.chat = chat_cancel
        # Wait for greeting to appear
        expect(self.chat.loc_messages).to_contain_text("Titanic", timeout=30000)

    def test_stop_button_appears_during_streaming(self) -> None:
        """The stop button should be visible while the LLM is streaming."""
        self.chat.set_user_input(
            "Write a very long and detailed paragraph about every column "
            "in this dataset. Be extremely thorough and verbose."
        )
        self.chat.send_user_input(method="click")

        stop_btn = self.page.locator(".shiny-chat-btn-cancel")
        expect(stop_btn).to_be_visible(timeout=30000)

    def test_cancel_stops_response(self) -> None:
        """Clicking the stop button should cancel the stream."""
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
        """After cancelling, the user should be able to send another message."""
        # First message — cancel it
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

        # Second message — let it complete
        self.chat.set_user_input("How many rows are in the dataset?")
        self.chat.send_user_input(method="click")

        # The send button (not stop) should reappear after the stream finishes
        send_btn = self.page.locator(
            ".shiny-chat-btn-send:not(.shiny-chat-btn-cancel)"
        )
        expect(send_btn).to_be_visible(timeout=60000)
