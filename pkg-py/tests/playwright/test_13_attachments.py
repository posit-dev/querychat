"""
Playwright tests for file attachment support in QueryChat's Shiny UI.

Verifies that the attach-file button is rendered and that attached text
content is forwarded through the on_user_submit handler to the LLM.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class TestAttachments:
    """Tests for file attachment support in QueryChat."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_01_hello: str, chat_01_hello: ChatController
    ) -> None:
        page.goto(app_01_hello)
        page.wait_for_selector("table", timeout=10000)
        self.page = page
        self.chat = chat_01_hello

    def test_attachment_button_is_visible_by_default(self) -> None:
        """ATTACH-01: Attach button renders when allow_attachments=True (the default)."""
        expect(self.page.locator(".shiny-chat-btn-attach").first).to_be_visible()

    def test_text_attachment_content_reaches_llm(self) -> None:
        """ATTACH-02: LLM response references content from an attached text file."""
        unique_word = "QUERYCHAT_ZEPHYR_42"

        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, prefix="querychat_attach_test_"
        ) as f:
            f.write(f"Secret word: {unique_word}\n")
            tmp_path = Path(f.name)

        try:
            with self.page.expect_file_chooser() as fc_info:
                self.page.locator(".shiny-chat-btn-attach").first.click()
            fc_info.value.set_files(str(tmp_path))

            self.chat.set_user_input(
                "What is the secret word in the attached file? Reply with only the word."
            )
            self.chat.send_user_input(method="click")

            self.chat.expect_latest_message(
                re.compile(unique_word, re.IGNORECASE),
                timeout=60000,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
