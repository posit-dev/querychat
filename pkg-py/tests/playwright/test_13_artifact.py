"""
Playwright tests for the artifact feature.

Tests the /artifact slash command, modal wizard UI, gallery interactions,
artifact generation, panel display, and pill click navigation.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

from .conftest import ArtifactModalActions

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController


class TestArtifactAppLoads:
    """Verifies the app starts correctly with the artifact panel in the DOM."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        self.page = page
        self.chat = chat_artifact

    def test_app_loads(self):
        expect(self.page.locator("body")).to_be_visible()
        expect(self.page.locator("table")).to_be_visible()

    def test_panel_in_dom_but_hidden(self):
        panel = self.page.locator(".querychat-artifact-panel")
        expect(panel).to_be_attached()
        expect(panel).not_to_have_class(re.compile(r"\bopen\b"))

    def test_panel_has_code_editor_container(self):
        body = self.page.locator(".querychat-artifact-panel-body")
        expect(body).to_be_attached()

    def test_panel_has_download_button(self):
        btn = self.page.locator(
            ".querychat-artifact-panel-header [id$='artifact_download']"
        )
        expect(btn.first).to_be_attached()

    def test_panel_has_close_button(self):
        btn = self.page.locator(
            ".querychat-artifact-panel-header button[aria-label='Close']"
        )
        expect(btn).to_be_attached()

    def test_panel_has_revise_textarea(self):
        textarea = self.page.locator(
            ".querychat-artifact-revise-drawer textarea"
        )
        expect(textarea).to_be_attached()

    def test_panel_has_revise_button(self):
        btn = self.page.locator(".querychat-artifact-revise-toggle")
        expect(btn).to_be_attached()


class TestArtifactModal(ArtifactModalActions):
    """Tests the /artifact modal wizard: opening, type selector, gallery, and buttons."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        # Wait for greeting to load so chat is ready for input
        chat_artifact.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )
        self.page = page
        self.chat = chat_artifact

    def test_slash_command_opens_modal(self):
        self._open_artifact_modal()
        modal = self.page.locator(".modal")
        expect(modal).to_be_visible()
        expect(modal).to_contain_text("Create Artifact")

    def test_modal_has_type_selector(self):
        self._open_artifact_modal()
        pills = self.page.locator(".querychat-artifact-type-pill")
        count = pills.count()
        assert count >= 2, f"Expected at least 2 type pills, got {count}"
        expect(pills.nth(0)).to_contain_text("Quarto")

    def test_first_type_pill_is_active_by_default(self):
        self._open_artifact_modal()
        first_pill = self.page.locator(".querychat-artifact-type-pill").first
        expect(first_pill).to_have_class(re.compile(r"\bactive\b"))

    def test_type_pill_toggle(self):
        self._open_artifact_modal()
        pills = self.page.locator(".querychat-artifact-type-pill")

        pills.nth(2).click()
        expect(pills.nth(2)).to_have_class(re.compile(r"\bactive\b"))
        expect(pills.nth(0)).not_to_have_class(re.compile(r"\bactive\b"))

        pills.nth(0).click()
        expect(pills.nth(0)).to_have_class(re.compile(r"\bactive\b"))
        expect(pills.nth(2)).not_to_have_class(re.compile(r"\bactive\b"))

    def test_empty_gallery_message(self):
        self._open_artifact_modal()
        empty = self.page.locator(".querychat-artifact-gallery-empty")
        expect(empty).to_be_visible()
        expect(empty).to_contain_text("No results yet")

    def test_generate_button_disabled_when_no_items(self):
        self._open_artifact_modal()
        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_visible()
        expect(btn).to_be_disabled()

    def test_directions_textarea_present(self):
        self._open_artifact_modal()
        textarea = self.page.locator(".modal textarea")
        expect(textarea).to_be_visible()
        expect(textarea).to_have_attribute(
            "placeholder",
            re.compile(r"dark theme"),
        )

class TestArtifactGalleryWithResults(ArtifactModalActions):
    """Tests the modal gallery after sending a query to populate it."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        chat_artifact.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )
        self.page = page
        self.chat = chat_artifact

    def test_gallery_shows_query_result(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        items = self.page.locator(".querychat-artifact-gallery-item")
        expect(items.first).to_be_visible(timeout=5000)

    def test_gallery_item_toggle_selection(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        # Wait for auto-recommend to complete (loading class removed)
        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        item = self.page.locator(".querychat-artifact-gallery-item").first
        expect(item).to_be_visible(timeout=5000)

        # Auto-recommend pre-selects items, so first click deselects
        item.click()
        expect(item).not_to_have_class(re.compile(r"\bselected\b"))

        # Second click re-selects
        item.click()
        expect(item).to_have_class(re.compile(r"\bselected\b"))

    def test_generate_enabled_with_gallery_items(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        # Wait for auto-recommend to complete
        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        items = self.page.locator(".querychat-artifact-gallery-item")
        expect(items.first).to_be_visible(timeout=5000)

        btn = self.page.locator(".modal button:has-text('Generate')")
        # After recommend, at least one item should be selected, enabling Generate
        expect(btn).not_to_be_disabled(timeout=5000)

    def test_gallery_starts_in_loading_state(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        # Gallery should start with loading class (auto-recommend in flight)
        expect(gallery).to_have_class(re.compile(r"\bloading\b"), timeout=5000)

        # Loading status line should be visible
        status = self.page.locator(".querychat-artifact-loading-status")
        expect(status).to_be_visible()
        expect(status).to_contain_text("Analyzing")

    def test_gallery_items_have_checkboxes(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        # Wait for loading to complete
        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        checkbox = self.page.locator(".querychat-artifact-gallery-item .gallery-checkbox").first
        expect(checkbox).to_be_visible()


class TestArtifactLanguageSelector(ArtifactModalActions):
    """Tests the modal's Language selector: defaults, per-format disabling, reset."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        chat_artifact.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )
        self.page = page
        self.chat = chat_artifact

    def test_language_section_defaults_to_no_preference(self):
        self._open_artifact_modal()
        pills = self.page.locator(".querychat-artifact-language-pill")
        expect(pills).to_have_count(3)
        no_pref = self.page.locator(
            '.querychat-artifact-language-pill[data-language=""]'
        )
        expect(no_pref).to_have_class(re.compile(r"\bactive\b"))

    def test_python_only_format_disables_r(self):
        self._open_artifact_modal()
        self.page.locator(
            '.querychat-artifact-type-pill[data-artifact-type="marimo-notebook"]'
        ).click()
        r_pill = self.page.locator(
            '.querychat-artifact-language-pill[data-language="r"]'
        )
        expect(r_pill).to_have_class(re.compile(r"\bdisabled\b"))

    def test_switching_to_python_only_format_resets_active_language(self):
        self._open_artifact_modal()
        # Choose R explicitly
        r_pill = self.page.locator(
            '.querychat-artifact-language-pill[data-language="r"]'
        )
        r_pill.click()
        expect(r_pill).to_have_class(re.compile(r"\bactive\b"))

        # Switch to a Python-only format; R must disable and selection reset
        self.page.locator(
            '.querychat-artifact-type-pill[data-artifact-type="marimo-notebook"]'
        ).click()
        expect(r_pill).to_have_class(re.compile(r"\bdisabled\b"))
        expect(r_pill).not_to_have_class(re.compile(r"\bactive\b"))
        no_pref = self.page.locator(
            '.querychat-artifact-language-pill[data-language=""]'
        )
        expect(no_pref).to_have_class(re.compile(r"\bactive\b"))


class TestArtifactGeneration(ArtifactModalActions):
    """Tests the full artifact generation flow: generate, panel, pill, close."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        chat_artifact.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )
        self.page = page
        self.chat = chat_artifact

    def _generate_artifact(self):
        """Send a query, open modal, wait for recommend, generate."""
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        # Wait for auto-recommend to complete
        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        # Recommend should have pre-selected at least one item
        selected = self.page.locator(".querychat-artifact-gallery-item.selected")
        expect(selected.first).to_be_visible(timeout=5000)

        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_enabled()
        btn.click()

    def test_generate_opens_panel(self):
        self._generate_artifact()

        panel = self.page.locator(".querychat-artifact-panel")
        expect(panel).to_have_class(re.compile(r"\bopen\b"), timeout=60000)

    def test_generate_populates_editor(self):
        self._generate_artifact()

        editor = self.page.locator(
            ".querychat-artifact-panel-body textarea"
        )
        expect(editor).to_be_visible(timeout=60000)
        expect(editor).not_to_have_value("", timeout=120000)

    def test_generate_creates_pill_in_chat(self):
        self._generate_artifact()

        pill = self.page.locator(".querychat-artifact-pill")
        expect(pill).to_be_visible(timeout=120000)
        expect(pill).to_contain_text("Quarto")

    def test_close_button_hides_panel(self):
        self._generate_artifact()

        panel = self.page.locator(".querychat-artifact-panel")
        expect(panel).to_have_class(re.compile(r"\bopen\b"), timeout=120000)

        close_btn = self.page.locator(
            ".querychat-artifact-panel-header button[aria-label='Close']"
        )
        close_btn.click()
        expect(panel).not_to_have_class(re.compile(r"\bopen\b"), timeout=5000)

    def test_pill_click_reopens_panel(self):
        self._generate_artifact()

        pill = self.page.locator(".querychat-artifact-pill")
        expect(pill).to_be_visible(timeout=120000)

        close_btn = self.page.locator(
            ".querychat-artifact-panel-header button[aria-label='Close']"
        )
        close_btn.click()

        panel = self.page.locator(".querychat-artifact-panel")
        expect(panel).not_to_have_class(re.compile(r"\bopen\b"), timeout=5000)

        pill.click()
        expect(panel).to_have_class(re.compile(r"\bopen\b"), timeout=5000)


class TestArtifactToolRequest(ArtifactModalActions):
    """The LLM's request_artifact tool opens the modal after the turn completes."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        chat_artifact.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )
        self.page = page
        self.chat = chat_artifact

    def test_natural_language_request_opens_modal(self):
        # Give the model something to package, then ask for an artifact.
        self._send_query_and_wait("Show only female passengers")
        self.chat.set_user_input(
            "Please turn this analysis into a standalone Quarto report I can share."
        )
        self.chat.send_user_input(method="click")

        # The modal must not open mid-stream; it waits for the turn to finish.
        expect(self.page.locator(".modal")).not_to_be_visible(timeout=500)

        # The modal must not appear until the assistant turn finishes; once it
        # does, the deferred submit fires "/artifact" and the modal opens.
        modal = self.page.locator(".modal")
        expect(modal).to_be_visible(timeout=120000)
        expect(modal).to_contain_text("Create Artifact")
