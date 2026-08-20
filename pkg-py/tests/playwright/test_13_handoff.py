"""
Playwright tests for the handoff feature.

Tests the /handoff slash command, modal wizard UI, gallery interactions,
handoff generation, panel display, and pill click navigation.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

from .conftest import HandoffModalActions

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class TestHandoffAppLoads:
    """Verifies the app starts with the handoff panel closed."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_handoff: str, chat_handoff: ChatController):
        page.goto(app_handoff)
        page.wait_for_selector("table", timeout=15000)
        self.page = page
        self.chat = chat_handoff

    def test_app_loads_with_closed_handoff_panel(self):
        expect(self.page.locator("body")).to_be_visible()
        expect(self.page.locator("table")).to_be_visible()
        panel = self.page.locator(".querychat-handoff-panel")
        expect(panel).to_be_attached()
        expect(panel).not_to_have_class(re.compile(r"\bopen\b"))


class TestHandoffModal(HandoffModalActions):
    """Tests the /handoff modal wizard: opening, type selector, gallery, and buttons."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_handoff: str, chat_handoff: ChatController):
        page.goto(app_handoff)
        page.wait_for_selector("table", timeout=15000)
        expect(chat_handoff.loc_input).to_be_enabled(timeout=30000)
        self.page = page
        self.chat = chat_handoff

    def test_slash_command_opens_modal(self):
        self._open_handoff_modal()
        modal = self.page.locator(".modal")
        expect(modal).to_be_visible()
        expect(modal).to_contain_text("Prepare Handoff")

    def test_slash_palette_describes_only_handoff_command(self):
        self.chat.set_user_input("/")
        palette = self.page.locator(".shiny-chat-slash-palette")
        expect(palette).to_be_visible()
        expect(
            palette.locator(".shiny-chat-slash-palette-item", has_text="/handoff")
        ).to_contain_text("Prepare a shareable handoff")
        expect(
            palette.locator(".shiny-chat-slash-palette-item", has_text="/artifact")
        ).to_have_count(0)

    def test_modal_has_type_selector(self):
        self._open_handoff_modal()
        pills = self.page.locator(".querychat-handoff-type-pill")
        count = pills.count()
        assert count >= 2, f"Expected at least 2 type pills, got {count}"
        expect(pills.nth(0)).to_contain_text("Quarto")

    def test_first_type_pill_is_active_by_default(self):
        self._open_handoff_modal()
        first_pill = self.page.locator(".querychat-handoff-type-pill").first
        expect(first_pill).to_have_class(re.compile(r"\bactive\b"))

    def test_type_pill_toggle(self):
        self._open_handoff_modal()
        pills = self.page.locator(".querychat-handoff-type-pill")

        pills.nth(2).click()
        expect(pills.nth(2)).to_have_class(re.compile(r"\bactive\b"))
        expect(pills.nth(0)).not_to_have_class(re.compile(r"\bactive\b"))

        pills.nth(0).click()
        expect(pills.nth(0)).to_have_class(re.compile(r"\bactive\b"))
        expect(pills.nth(2)).not_to_have_class(re.compile(r"\bactive\b"))

    def test_empty_gallery_message(self):
        self._open_handoff_modal()
        empty = self.page.locator(".querychat-handoff-gallery-empty")
        expect(empty).to_be_visible()
        expect(empty).to_contain_text("No results yet")

    def test_generate_button_disabled_when_no_items(self):
        self._open_handoff_modal()
        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_visible()
        expect(btn).to_be_disabled()

    def test_directions_textarea_present(self):
        self._open_handoff_modal()
        textarea = self.page.locator(".modal textarea")
        expect(textarea).to_be_visible()
        expect(textarea).to_have_attribute(
            "placeholder",
            re.compile(r"dark theme"),
        )


class TestHandoffGalleryWithResults(HandoffModalActions):
    """Tests the modal gallery after sending a query to populate it."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_handoff: str, chat_handoff: ChatController):
        page.goto(app_handoff)
        page.wait_for_selector("table", timeout=15000)
        expect(chat_handoff.loc_input).to_be_enabled(timeout=30000)
        self.page = page
        self.chat = chat_handoff

    def test_gallery_shows_query_result(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_handoff_modal()

        items = self.page.locator(".querychat-handoff-gallery-item")
        expect(items.first).to_be_visible(timeout=5000)

    def test_gallery_item_toggle_selection(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_handoff_modal()

        # Wait for auto-recommend to complete (loading class removed)
        gallery = self.page.locator(".querychat-handoff-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        item = self.page.locator(".querychat-handoff-gallery-item").first
        expect(item).to_be_visible(timeout=5000)

        # Auto-recommend pre-selects items, so first click deselects
        item.click()
        expect(item).not_to_have_class(re.compile(r"\bselected\b"))

        # Second click re-selects
        item.click()
        expect(item).to_have_class(re.compile(r"\bselected\b"))

    def test_recommendation_transitions_modal_to_ready(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_handoff_modal()

        gallery = self.page.locator(".querychat-handoff-gallery")
        expect(gallery).to_have_class(re.compile(r"\bloading\b"), timeout=5000)
        status = self.page.locator(".querychat-handoff-loading-status")
        expect(status).to_be_visible()
        expect(status).to_contain_text("Analyzing")
        generate = self.page.locator(".modal button:has-text('Generate')")
        directions = self.page.locator(".modal textarea")
        expect(generate).to_be_disabled()
        expect(directions).to_be_disabled()

        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)
        expect(status).to_be_hidden()
        expect(directions).to_be_enabled()
        expect(directions).not_to_have_value("")
        expect(
            self.page.locator(".querychat-handoff-directions-subtitle")
        ).to_be_visible()
        expect(
            self.page.locator(".querychat-handoff-gallery-item.selected").first
        ).to_be_visible()


class TestHandoffLanguageSelector(HandoffModalActions):
    """Tests the modal's Language selector and per-format availability."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_handoff: str, chat_handoff: ChatController):
        page.goto(app_handoff)
        page.wait_for_selector("table", timeout=15000)
        expect(chat_handoff.loc_input).to_be_enabled(timeout=30000)
        self.page = page
        self.chat = chat_handoff

    def test_python_only_format_disables_r(self):
        self._open_handoff_modal()
        self.page.locator(
            '.querychat-handoff-type-pill[data-handoff-type="marimo-notebook"]'
        ).click()
        r_pill = self.page.locator(
            '.querychat-handoff-language-pill[data-language="r"]'
        )
        expect(r_pill).to_have_class(re.compile(r"\bdisabled\b"))

class TestHandoffGeneration(HandoffModalActions):
    """Tests the full handoff generation flow: generate, panel, pill, close."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_handoff: str, chat_handoff: ChatController):
        page.goto(app_handoff)
        page.wait_for_selector("table", timeout=15000)
        expect(chat_handoff.loc_input).to_be_enabled(timeout=30000)
        self.page = page
        self.chat = chat_handoff

    def _generate_quarto_handoff(self):
        """Send a query, open modal, wait for recommend, generate."""
        self._send_query_and_wait("Show only female passengers")
        self._open_handoff_modal()

        # Wait for auto-recommend to complete
        gallery = self.page.locator(".querychat-handoff-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        # Recommend should have pre-selected at least one item
        selected = self.page.locator(".querychat-handoff-gallery-item.selected")
        expect(selected.first).to_be_visible(timeout=5000)

        self.page.locator(
            '.querychat-handoff-type-pill[data-handoff-type="quarto-dashboard"]'
        ).click()
        self.page.locator(
            '.querychat-handoff-language-pill[data-language="python"]'
        ).click()
        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_enabled()
        btn.click()

    def _revise_handoff(self):
        self.page.locator(".querychat-handoff-revise-toggle").click()
        textarea = self.page.locator(".querychat-handoff-revise-drawer textarea")
        expect(textarea).to_be_visible(timeout=5000)
        textarea.fill("Add a comment at the top that says BROWSER_HISTORY.")
        textarea.press("Enter")

        editor = self.page.locator(".querychat-handoff-panel-body textarea")
        expect(editor).to_have_value(re.compile("BROWSER_HISTORY"), timeout=120000)

    def test_generated_handoff_can_be_closed_and_reopened(self):
        self._generate_quarto_handoff()

        panel = self.page.locator(".querychat-handoff-panel")
        expect(panel).to_have_class(re.compile(r"\bopen\b"), timeout=60000)
        editor = self.page.locator(".querychat-handoff-panel-body textarea")
        expect(editor).to_be_visible(timeout=60000)
        expect(editor).not_to_have_value("", timeout=120000)
        pill = self.page.locator(".querychat-handoff-pill")
        expect(pill).to_be_visible(timeout=120000)
        expect(pill).to_contain_text("Quarto")

        close_btn = self.page.locator(
            ".querychat-handoff-panel-header button[aria-label='Close']"
        )
        close_btn.click()
        expect(panel).not_to_have_class(re.compile(r"\bopen\b"), timeout=5000)

        pill.click()
        expect(panel).to_have_class(re.compile(r"\bopen\b"), timeout=5000)

    def test_revision_restores_after_browser_history_reload(self):
        self._generate_quarto_handoff()
        pill = self.page.locator(".querychat-handoff-pill")
        expect(pill).to_be_visible(timeout=120000)

        self._revise_handoff()
        assert "_state_id_=" not in self.page.url

        self.page.reload()
        self.page.wait_for_selector("shiny-chat-container", timeout=30000)

        pill = self.page.locator(".querychat-handoff-pill")
        expect(pill.first).to_be_visible(timeout=30000)
        pill.first.click()

        editor = self.page.locator(".querychat-handoff-panel-body textarea")
        expect(editor).to_have_value(re.compile("BROWSER_HISTORY"), timeout=10000)


class TestHandoffToolRequest(HandoffModalActions):
    """The LLM's request_handoff tool opens the modal after the turn completes."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_handoff: str, chat_handoff: ChatController):
        page.goto(app_handoff)
        page.wait_for_selector("table", timeout=15000)
        expect(chat_handoff.loc_input).to_be_enabled(timeout=30000)
        self.page = page
        self.chat = chat_handoff

    def test_natural_language_request_opens_modal(self):
        # Give the model something to package, then ask for a handoff.
        self._send_query_and_wait("Show only female passengers")
        self.chat.set_user_input(
            "Please turn this analysis into a standalone Quarto report I can share."
        )
        self.chat.send_user_input(method="click")

        # The modal must not open mid-stream; it waits for the turn to finish.
        expect(self.page.locator(".modal")).not_to_be_visible(timeout=500)

        # The modal must not appear until the assistant turn finishes; once it
        # does, the deferred submit fires "/handoff" and the modal opens.
        modal = self.page.locator(".modal")
        expect(modal).to_be_visible(timeout=120000)
        expect(modal).to_contain_text("Prepare Handoff")
