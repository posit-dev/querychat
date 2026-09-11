"""
Playwright tests for 03-page-express-app.py and 03-page-core-app.py.

These examples use qc.page() for a chat-first layout with:
- Chat owning the full browser window
- Reactive title and data table on a secondary "Data" navigation page
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect
from shinychat.playwright import PageChatController

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shiny.run import ShinyAppProc
    from shinychat.playwright import ChatController


class PageAppSmoke:
    """Shared smoke tests for the chat-first page examples."""

    page: Page
    chat: ChatController
    page_shell: PageChatController

    def test_page_title(self) -> None:
        """Page has correct title."""
        expect(self.page).to_have_title("Titanic Explorer")

    def test_chat_is_mounted(self) -> None:
        """Chat container is visible on the home page."""
        expect(self.chat.loc).to_be_visible()

    def test_data_nav_panel(self) -> None:
        """Navigating to the Data page reveals the reactive data view."""
        self.page_shell.select_page("Data")
        self.page_shell.expect_active_page("data")
        expect(self.page.locator(".card-header")).to_contain_text("Titanic Dataset")
        self.page.wait_for_selector("table tbody tr", timeout=15000)

        # ... and the chat remains mounted after returning home
        self.page_shell.return_home()
        expect(self.chat.loc).to_be_visible()

    def test_extras_footer_is_collapsed(self) -> None:
        """The footer carrying querychat's deps/handoff panel adds no vertical space."""
        footer = self.page.locator(
            ".shiny-chat-footer", has=self.page.locator(".querychat-extras")
        )
        expect(footer).to_be_attached()
        expect(footer).to_have_css("padding-top", "0px")


class Test03PageExpress(PageAppSmoke):
    """Tests for 03-page-express-app.py - Shiny Express with chat-first page."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        page: Page,
        app_03_page_express: ShinyAppProc,
        chat_03_page_express: ChatController,
    ) -> None:
        page.goto(app_03_page_express.url)
        self.page = page
        self.chat = chat_03_page_express
        self.page_shell = PageChatController(page, "querychat_titanic-chat")


class Test03PageCore(PageAppSmoke):
    """Tests for 03-page-core-app.py - Shiny Core with chat-first page."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        page: Page,
        app_03_page_core: ShinyAppProc,
        chat_03_page_core: ChatController,
    ) -> None:
        page.goto(app_03_page_core.url)
        self.page = page
        self.chat = chat_03_page_core
        self.page_shell = PageChatController(page, "querychat_titanic-chat")
