"""
Minimal reproduction of the broken Apply Filter button in Shiny apps.

Root cause: querychat.js sends { query, title } on button click but omits `table`.
The Shiny server handler needs `table` to find the right table state; without it
the update is silently ignored (update.get("table", "") returns "", which is falsy).

Steps:
  1. Submit one filter query to get the LLM to call update_dashboard.
     The filter is applied immediately AND the Apply Filter button appears in the chat.
  2. Reset the filter directly via Shiny's JS API (no second LLM call).
  3. Click the Apply Filter button.
  4. Assert the filter is re-applied — this assertion FAILS with the current code,
     confirming the bug.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from shinychat.playwright import ChatController

_CHAT_INPUT_ID = "querychat_titanic-chat_update"


class TestFilterButtonRepro:
    """Reproduction: Apply Filter button does not re-apply the filter."""

    @pytest.fixture(autouse=True)
    def setup(
        self, page: Page, app_01_hello: str, chat_01_hello: ChatController
    ) -> None:
        page.goto(app_01_hello)
        page.wait_for_selector("table", timeout=10000)
        self.page = page
        self.chat = chat_01_hello

    def test_apply_filter_button_re_applies_filter(self) -> None:
        # --- Step 1: one LLM call to get a filter applied + button rendered ---
        self.chat.set_user_input("Show only first class passengers")
        self.chat.send_user_input(method="click")

        # Wait until the SQL panel reflects the filter
        sql_code = self.page.locator("pre code").first
        expect(sql_code).to_contain_text(
            re.compile(r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE),
            timeout=60000,
        )

        # The Apply Filter button should now be visible in the chat
        apply_btn = self.page.locator(".querychat-update-dashboard-btn").first
        expect(apply_btn).to_be_visible(timeout=10000)

        # Sanity check: button carries the expected data attributes
        assert apply_btn.get_attribute("data-table") == "titanic"
        assert apply_btn.get_attribute("data-query") not in (None, "")

        # --- Step 2: reset the filter via Shiny JS (no second LLM call) ---
        self.page.evaluate(
            f"""
            window.Shiny.setInputValue(
                '{_CHAT_INPUT_ID}',
                {{table: 'titanic', query: '', title: ''}},
                {{priority: 'event'}}
            );
            """
        )
        # Wait for the full unfiltered dataset (891 rows)
        expect(self.page.locator("text=891")).to_be_visible(timeout=10000)

        # --- Step 3: click Apply Filter ---
        apply_btn.click()

        # With the bug: the click sends {{query, title}} but not `table`, so the
        # Shiny handler ignores it and the row count stays at 891.
        # With the fix: the filter is re-applied and the count drops below 891.
        expect(self.page.locator("text=891")).not_to_be_visible(timeout=5000)
