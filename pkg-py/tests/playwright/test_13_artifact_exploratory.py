"""
Exploratory Playwright tests for the artifact modal redesign.

Verifies: auto-recommend lifecycle, checkbox visuals, loading states,
section headers, directions pre-fill, Generate enable/disable logic.
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


class TestAutoRecommendLifecycle(ArtifactModalActions):
    """Tests the full auto-recommend flow: loading → complete → interactions."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        chat_artifact.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )
        self.page = page
        self.chat = chat_artifact

    def test_loading_status_line_visible_during_recommend(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        status = self.page.locator(".querychat-artifact-loading-status")
        expect(status).to_be_visible()
        expect(status).to_contain_text("Analyzing")

        spinner = status.locator(".spinner")
        expect(spinner).to_be_visible()

    def test_loading_status_hidden_after_recommend_completes(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        status = self.page.locator(".querychat-artifact-loading-status")
        expect(status).to_be_hidden()

    def test_generate_disabled_during_loading(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_disabled()

    def test_generate_enabled_after_recommend(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_enabled(timeout=5000)

    def test_directions_textarea_disabled_during_loading(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        textarea = self.page.locator(".modal textarea")
        expect(textarea).to_be_disabled()

    def test_directions_textarea_enabled_after_recommend(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        textarea = self.page.locator(".modal textarea")
        expect(textarea).to_be_enabled(timeout=5000)

    def test_directions_prefilled_after_recommend(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        textarea = self.page.locator(".modal textarea")
        value = textarea.input_value()
        assert len(value) > 0, "Directions should be pre-filled by recommend"

    def test_prefilled_subtitle_shown_after_recommend(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        subtitle = self.page.locator(".querychat-artifact-directions-subtitle")
        expect(subtitle).to_be_visible()
        expect(subtitle).to_contain_text("Pre-filled by AI")

    def test_at_least_one_item_preselected(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        selected = self.page.locator(".querychat-artifact-gallery-item.selected")
        assert selected.count() >= 1, "Recommend should pre-select at least one item"

    def test_selected_items_have_visible_checkmarks(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        selected = self.page.locator(".querychat-artifact-gallery-item.selected").first
        checkbox = selected.locator(".gallery-checkbox")
        expect(checkbox).to_be_visible()

    def test_deselecting_all_items_disables_generate(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        items = self.page.locator(".querychat-artifact-gallery-item")
        for i in range(items.count()):
            item = items.nth(i)
            if "selected" in (item.get_attribute("class") or ""):
                item.click()

        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_disabled()

    def test_reselecting_item_enables_generate(self):
        self._send_query_and_wait("Show only female passengers")
        self._open_artifact_modal()

        gallery = self.page.locator(".querychat-artifact-gallery")
        expect(gallery).not_to_have_class(re.compile(r"\bloading\b"), timeout=60000)

        items = self.page.locator(".querychat-artifact-gallery-item")
        for i in range(items.count()):
            item = items.nth(i)
            if "selected" in (item.get_attribute("class") or ""):
                item.click()

        btn = self.page.locator(".modal button:has-text('Generate')")
        expect(btn).to_be_disabled()

        items.first.click()
        expect(btn).to_be_enabled()


class TestModalLayoutRedesign(ArtifactModalActions):
    """Verifies the reorganized modal layout: section headers, order, no Recommend button."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_artifact: str, chat_artifact: ChatController):
        page.goto(app_artifact)
        page.wait_for_selector("table", timeout=15000)
        chat_artifact.expect_latest_message(
            re.compile(r"Hello|Welcome", re.IGNORECASE), timeout=30000
        )
        self.page = page
        self.chat = chat_artifact

    def test_no_recommend_button_exists(self):
        self._open_artifact_modal()
        recommend = self.page.locator(".modal button:has-text('Recommend')")
        expect(recommend).to_have_count(0)

    def test_results_section_label_exists(self):
        self._open_artifact_modal()
        label = self.page.locator(".querychat-artifact-section-label")
        texts = [label.nth(i).text_content() for i in range(label.count())]
        assert any("Results to include" in (t or "") for t in texts)

    def test_output_format_label_exists(self):
        self._open_artifact_modal()
        label = self.page.locator(".querychat-artifact-section-label")
        texts = [label.nth(i).text_content() for i in range(label.count())]
        assert any("Output format" in (t or "") for t in texts)

    def test_generation_notes_label_exists(self):
        self._open_artifact_modal()
        label = self.page.locator(".querychat-artifact-section-label")
        texts = [label.nth(i).text_content() for i in range(label.count())]
        assert any("Generation notes" in (t or "") for t in texts)

    def test_type_pills_still_work(self):
        self._open_artifact_modal()
        pills = self.page.locator(".querychat-artifact-type-pill")
        assert pills.count() >= 2

        pills.nth(1).click()
        expect(pills.nth(1)).to_have_class(re.compile(r"\bactive\b"))
        expect(pills.nth(0)).not_to_have_class(re.compile(r"\bactive\b"))

    def test_no_dismiss_button(self):
        self._open_artifact_modal()
        dismiss = self.page.locator(".modal button:has-text('Dismiss')")
        expect(dismiss).to_have_count(0)

    def test_empty_modal_no_loading_status(self):
        self._open_artifact_modal()
        status = self.page.locator(".querychat-artifact-loading-status")
        expect(status).to_be_hidden()

    def test_empty_modal_textarea_not_disabled(self):
        self._open_artifact_modal()
        textarea = self.page.locator(".modal textarea")
        expect(textarea).to_be_enabled()
