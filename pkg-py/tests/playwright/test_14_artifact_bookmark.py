"""
Playwright tests for artifact bookmark restore behavior.

A revision streams into the editor without appending a chat message, so
shinychat's message-driven auto-bookmark never fires for it. These tests verify
that the revise step explicitly re-triggers bookmarking, so the bookmark holds
the revised version and a fresh session restores the most-recent version.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from collections.abc import Generator

    from playwright.sync_api import BrowserContext, Page
    from shinychat.playwright import ChatController as ChatControllerType

# conftest.py is not importable directly; add the test directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))
from conftest import (
    ArtifactModalActions,
    _create_chat_controller,
    _find_free_port,
    _start_server_with_retry,
    _start_shiny_app_threaded,
    _stop_shiny_server,
)

APPS_DIR = Path(__file__).parent / "apps"
GEN_TIMEOUT = 120_000


@pytest.fixture(scope="module")
def app_artifact_bookmark() -> Generator[str, None, None]:
    """Start the artifact bookmark test app with server-side bookmarking."""
    app_path = str(APPS_DIR / "artifact_bookmark_app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    def shiny_cleanup(_thread, server):
        _stop_shiny_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, shiny_cleanup, timeout=30.0
    )
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_artifact_bookmark(page: Page) -> ChatControllerType:
    return _create_chat_controller(page, "titanic")


class TestArtifactBookmarkRestore(ArtifactModalActions):
    @pytest.fixture(autouse=True)
    def setup(
        self,
        page: Page,
        app_artifact_bookmark: str,
        chat_artifact_bookmark: ChatControllerType,
    ) -> None:
        self.page = page
        self.chat = chat_artifact_bookmark
        page.goto(app_artifact_bookmark)
        page.wait_for_selector("table", timeout=15000)
        chat_artifact_bookmark.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )

    def _generate_artifact(self) -> None:
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)
        selected = self.page.locator(".querychat-artifact-gallery-item.selected")
        expect(selected.first).to_be_visible(timeout=5000)

        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_enabled()
        btn.click()

        editor = self.page.locator(".querychat-artifact-panel-body textarea")
        expect(editor).not_to_have_value("", timeout=GEN_TIMEOUT)
        expect(self.page.locator(".querychat-artifact-pill")).to_be_visible(
            timeout=GEN_TIMEOUT
        )

    def _revise_artifact(self) -> None:
        self.page.locator(".querychat-artifact-revise-toggle").click()
        textarea = self.page.locator(".querychat-artifact-revise-drawer textarea")
        expect(textarea).to_be_visible(timeout=5000)
        textarea.fill("Add a comment at the very top that says HELLO_REVISION.")
        textarea.press("Enter")

        # The revision is complete once a second version exists.
        label = self.page.locator(".querychat-artifact-version-label")
        expect(label).to_contain_text("2 of 2", timeout=GEN_TIMEOUT)

    def test_revision_updates_bookmark_and_restores_latest(
        self, context: BrowserContext
    ) -> None:
        self._generate_artifact()

        # Generation appends a chat pill, so shinychat auto-bookmarks; wait for
        # the server-store state id to land in the URL before revising.
        self.page.wait_for_function(
            "() => window.location.search.includes('_state_id_=')",
            timeout=30_000,
        )
        post_generate_url = self.page.url

        self._revise_artifact()

        # The fix: the revise step re-triggers bookmarking, so the URL's state id
        # changes even though no chat message was appended.
        self.page.wait_for_function(
            "(prev) => window.location.href !== prev",
            arg=post_generate_url,
            timeout=30_000,
        )
        bookmark_url = self.page.url
        assert bookmark_url != post_generate_url

        # Restore in a fresh session: the pill returns and opens the latest (v2).
        new_page = context.new_page()
        new_page.goto(bookmark_url)
        new_page.wait_for_selector("shiny-chat-container", timeout=30_000)

        pill = new_page.locator(".querychat-artifact-pill")
        expect(pill.first).to_be_visible(timeout=30_000)
        pill.first.click()

        panel = new_page.locator(".querychat-artifact-panel")
        expect(panel).to_have_class(re.compile(r"\bopen\b"), timeout=10_000)

        label = new_page.locator(".querychat-artifact-version-label")
        expect(label).to_contain_text("2 of 2", timeout=10_000)

        new_page.close()
