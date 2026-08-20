from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


HANDOFF_JS = (
    Path(__file__).parents[2] / "src" / "querychat" / "static" / "js" / "handoff.js"
)


def install_handoff_runtime(page: Page, body: str) -> None:
    page.set_content(body)
    page.evaluate(
        """
        window.handoffHandlers = {};
        window.Shiny = {
          addCustomMessageHandler(name, handler) {
            window.handoffHandlers[name] = handler;
          },
          setInputValue() {}
        };
        """
    )
    page.add_script_tag(path=str(HANDOFF_JS))


def test_panel_messages_update_only_the_target_module(page: Page) -> None:
    install_handoff_runtime(
        page,
        """
        <div id="first-handoff_root" class="querychat-handoff-root">
          <div class="querychat-handoff-backdrop"></div>
          <div class="querychat-handoff-panel">
            <span class="querychat-handoff-header-spinner"></span>
            <bslib-code-editor id="first-handoff_source_editor"></bslib-code-editor>
            <a id="first-handoff_download" title="Download"></a>
          </div>
        </div>
        <div id="second-handoff_root" class="querychat-handoff-root">
          <div class="querychat-handoff-backdrop"></div>
          <div class="querychat-handoff-panel">
            <span class="querychat-handoff-header-spinner"></span>
            <bslib-code-editor id="second-handoff_source_editor"></bslib-code-editor>
            <a id="second-handoff_download" title="Download"></a>
          </div>
        </div>
        """,
    )

    page.evaluate(
        """
        window.handoffHandlers["querychat-handoff-panel-toggle"]({
          root_id: "second-handoff_root",
          open: true
        });
        window.handoffHandlers["querychat-handoff-streaming"]({
          root_id: "second-handoff_root",
          active: true
        });
        window.handoffHandlers["querychat-handoff-source-update"]({
          root_id: "second-handoff_root",
          id: "second-handoff_source_editor",
          value: "print(1)",
          language: "python",
          download_available: false
        });
        """
    )

    first_panel = page.locator("#first-handoff_root .querychat-handoff-panel")
    second_panel = page.locator("#second-handoff_root .querychat-handoff-panel")
    expect(first_panel).not_to_have_class("querychat-handoff-panel open streaming")
    expect(second_panel).to_have_class("querychat-handoff-panel open streaming")
    expect(page.locator("#first-handoff_download")).to_have_attribute(
        "title",
        "Download",
    )
    expect(page.locator("#second-handoff_download")).to_have_attribute(
        "aria-disabled",
        "true",
    )
    expect(page.locator("#second-handoff_download")).to_have_attribute(
        "title",
        "Download unavailable: data snapshot is no longer available",
    )


def test_panel_clicks_update_only_the_clicked_module(page: Page) -> None:
    install_handoff_runtime(
        page,
        """
        <div id="first-handoff_root" class="querychat-handoff-root">
          <button class="querychat-handoff-revise-toggle"></button>
          <div class="querychat-handoff-revise-drawer">
            <textarea></textarea>
          </div>
        </div>
        <div id="second-handoff_root" class="querychat-handoff-root">
          <button class="querychat-handoff-revise-toggle"></button>
          <div class="querychat-handoff-revise-drawer">
            <textarea></textarea>
          </div>
        </div>
        """,
    )

    page.locator("#second-handoff_root .querychat-handoff-revise-toggle").click()

    expect(
        page.locator("#first-handoff_root .querychat-handoff-revise-drawer")
    ).not_to_have_class("querychat-handoff-revise-drawer open")
    expect(
        page.locator("#second-handoff_root .querychat-handoff-revise-drawer")
    ).to_have_class("querychat-handoff-revise-drawer open")


def test_recommendation_updates_only_the_target_modal(page: Page) -> None:
    install_handoff_runtime(
        page,
        """
        <div id="first-handoff_modal_root" class="querychat-handoff-modal">
          <div class="querychat-handoff-gallery">
            <button class="querychat-handoff-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-handoff-type-selector">
            <button class="querychat-handoff-type-pill active" data-handoff-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-handoff-type-pill" data-handoff-type="shiny-app" data-languages="python,r"></button>
          </div>
          <div class="querychat-handoff-language-selector"></div>
          <div class="querychat-handoff-directions-wrapper loading">
            <textarea id="first-handoff_directions" disabled></textarea>
          </div>
          <span class="querychat-handoff-directions-subtitle hidden"></span>
          <span class="querychat-handoff-loading-status"></span>
          <button id="first-handoff_generate" disabled></button>
        </div>
        <div id="second-handoff_modal_root" class="querychat-handoff-modal">
          <div class="querychat-handoff-gallery loading">
            <button class="querychat-handoff-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-handoff-type-selector">
            <button class="querychat-handoff-type-pill active" data-handoff-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-handoff-type-pill" data-handoff-type="shiny-app" data-languages="python,r"></button>
          </div>
          <div class="querychat-handoff-language-selector"></div>
          <div class="querychat-handoff-directions-wrapper loading">
            <textarea id="second-handoff_directions" disabled></textarea>
          </div>
          <span class="querychat-handoff-directions-subtitle hidden"></span>
          <span class="querychat-handoff-loading-status"></span>
          <button id="second-handoff_generate" disabled></button>
        </div>
        """,
    )

    page.evaluate(
        """
        window.handoffHandlers["querychat-handoff-recommend"]({
          root_id: "second-handoff_modal_root",
          selected_ids: ["query-0"],
          format_id: "shiny-app",
          directions: "Use a compact layout.",
          directions_id: "second-handoff_directions"
        });
        """
    )

    expect(
        page.locator("#first-handoff_modal_root .querychat-handoff-gallery-item")
    ).not_to_have_class("querychat-handoff-gallery-item selected")
    expect(
        page.locator("#second-handoff_modal_root .querychat-handoff-gallery-item")
    ).to_have_class("querychat-handoff-gallery-item selected")
    expect(page.locator("#first-handoff_directions")).to_have_value("")
    expect(page.locator("#second-handoff_directions")).to_have_value(
        "Use a compact layout."
    )


def test_modal_inputs_update_only_the_clicked_module(page: Page) -> None:
    install_handoff_runtime(
        page,
        """
        <div id="first-handoff_modal_root" class="querychat-handoff-modal">
          <div class="querychat-handoff-gallery">
            <button class="querychat-handoff-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-handoff-type-selector">
            <button class="querychat-handoff-type-pill active" data-handoff-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-handoff-type-pill" data-handoff-type="other" data-languages="python,r"></button>
          </div>
          <div class="querychat-handoff-language-selector"></div>
          <div class="querychat-handoff-freeform-input hidden">
            <input>
          </div>
          <button id="first-handoff_generate" disabled></button>
        </div>
        <div id="second-handoff_modal_root" class="querychat-handoff-modal">
          <div class="querychat-handoff-gallery">
            <button class="querychat-handoff-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-handoff-type-selector">
            <button class="querychat-handoff-type-pill active" data-handoff-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-handoff-type-pill" data-handoff-type="other" data-languages="python,r"></button>
          </div>
          <div class="querychat-handoff-language-selector"></div>
          <div class="querychat-handoff-freeform-input hidden">
            <input>
          </div>
          <button id="second-handoff_generate" disabled></button>
        </div>
        """,
    )

    second_modal = page.locator("#second-handoff_modal_root")
    second_modal.locator('[data-handoff-type="other"]').click()
    second_modal.locator(".querychat-handoff-gallery-item").click()
    second_modal.locator(".querychat-handoff-freeform-input input").fill("HTML")

    expect(
        page.locator("#first-handoff_modal_root .querychat-handoff-freeform-input")
    ).to_have_class("querychat-handoff-freeform-input hidden")
    expect(
        page.locator("#second-handoff_modal_root .querychat-handoff-freeform-input")
    ).to_have_class("querychat-handoff-freeform-input")
    expect(page.locator("#first-handoff_generate")).to_be_disabled()
    expect(page.locator("#second-handoff_generate")).to_be_enabled()
