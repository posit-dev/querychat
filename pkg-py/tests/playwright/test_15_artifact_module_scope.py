from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


ARTIFACT_JS = (
    Path(__file__).parents[2] / "src" / "querychat" / "static" / "js" / "artifact.js"
)


def install_artifact_runtime(page: Page, body: str) -> None:
    page.set_content(body)
    page.evaluate(
        """
        window.artifactHandlers = {};
        window.Shiny = {
          addCustomMessageHandler(name, handler) {
            window.artifactHandlers[name] = handler;
          },
          setInputValue() {}
        };
        """
    )
    page.add_script_tag(path=str(ARTIFACT_JS))


def test_panel_messages_update_only_the_target_module(page: Page) -> None:
    install_artifact_runtime(
        page,
        """
        <div id="first-artifact_root" class="querychat-artifact-root">
          <div class="querychat-artifact-backdrop"></div>
          <div class="querychat-artifact-panel">
            <span class="querychat-artifact-header-spinner"></span>
            <bslib-code-editor id="first-artifact_source_editor"></bslib-code-editor>
            <a id="first-artifact_download" title="Download"></a>
          </div>
        </div>
        <div id="second-artifact_root" class="querychat-artifact-root">
          <div class="querychat-artifact-backdrop"></div>
          <div class="querychat-artifact-panel">
            <span class="querychat-artifact-header-spinner"></span>
            <bslib-code-editor id="second-artifact_source_editor"></bslib-code-editor>
            <a id="second-artifact_download" title="Download"></a>
          </div>
        </div>
        """,
    )

    page.evaluate(
        """
        window.artifactHandlers["querychat-artifact-panel-toggle"]({
          root_id: "second-artifact_root",
          open: true
        });
        window.artifactHandlers["querychat-artifact-streaming"]({
          root_id: "second-artifact_root",
          active: true
        });
        window.artifactHandlers["querychat-artifact-source-update"]({
          root_id: "second-artifact_root",
          id: "second-artifact_source_editor",
          value: "print(1)",
          language: "python",
          download_available: false
        });
        """
    )

    first_panel = page.locator("#first-artifact_root .querychat-artifact-panel")
    second_panel = page.locator("#second-artifact_root .querychat-artifact-panel")
    expect(first_panel).not_to_have_class("querychat-artifact-panel open streaming")
    expect(second_panel).to_have_class("querychat-artifact-panel open streaming")
    expect(page.locator("#first-artifact_download")).to_have_attribute(
        "title",
        "Download",
    )
    expect(page.locator("#second-artifact_download")).to_have_attribute(
        "aria-disabled",
        "true",
    )
    expect(page.locator("#second-artifact_download")).to_have_attribute(
        "title",
        "Download unavailable: data snapshot is no longer available",
    )


def test_panel_clicks_update_only_the_clicked_module(page: Page) -> None:
    install_artifact_runtime(
        page,
        """
        <div id="first-artifact_root" class="querychat-artifact-root">
          <button class="querychat-artifact-revise-toggle"></button>
          <div class="querychat-artifact-revise-drawer">
            <textarea></textarea>
          </div>
        </div>
        <div id="second-artifact_root" class="querychat-artifact-root">
          <button class="querychat-artifact-revise-toggle"></button>
          <div class="querychat-artifact-revise-drawer">
            <textarea></textarea>
          </div>
        </div>
        """,
    )

    page.locator("#second-artifact_root .querychat-artifact-revise-toggle").click()

    expect(
        page.locator("#first-artifact_root .querychat-artifact-revise-drawer")
    ).not_to_have_class("querychat-artifact-revise-drawer open")
    expect(
        page.locator("#second-artifact_root .querychat-artifact-revise-drawer")
    ).to_have_class("querychat-artifact-revise-drawer open")


def test_recommendation_updates_only_the_target_modal(page: Page) -> None:
    install_artifact_runtime(
        page,
        """
        <div id="first-artifact_modal_root" class="querychat-artifact-modal">
          <div class="querychat-artifact-gallery">
            <button class="querychat-artifact-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-artifact-type-selector">
            <button class="querychat-artifact-type-pill active" data-artifact-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-artifact-type-pill" data-artifact-type="shiny-app" data-languages="python,r"></button>
          </div>
          <div class="querychat-artifact-language-selector"></div>
          <div class="querychat-artifact-directions-wrapper loading">
            <textarea id="first-artifact_directions" disabled></textarea>
          </div>
          <span class="querychat-artifact-directions-subtitle hidden"></span>
          <span class="querychat-artifact-loading-status"></span>
          <button id="first-artifact_generate" disabled></button>
        </div>
        <div id="second-artifact_modal_root" class="querychat-artifact-modal">
          <div class="querychat-artifact-gallery loading">
            <button class="querychat-artifact-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-artifact-type-selector">
            <button class="querychat-artifact-type-pill active" data-artifact-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-artifact-type-pill" data-artifact-type="shiny-app" data-languages="python,r"></button>
          </div>
          <div class="querychat-artifact-language-selector"></div>
          <div class="querychat-artifact-directions-wrapper loading">
            <textarea id="second-artifact_directions" disabled></textarea>
          </div>
          <span class="querychat-artifact-directions-subtitle hidden"></span>
          <span class="querychat-artifact-loading-status"></span>
          <button id="second-artifact_generate" disabled></button>
        </div>
        """,
    )

    page.evaluate(
        """
        window.artifactHandlers["querychat-artifact-recommend"]({
          root_id: "second-artifact_modal_root",
          selected_ids: ["query-0"],
          format_id: "shiny-app",
          directions: "Use a compact layout.",
          directions_id: "second-artifact_directions"
        });
        """
    )

    expect(
        page.locator("#first-artifact_modal_root .querychat-artifact-gallery-item")
    ).not_to_have_class("querychat-artifact-gallery-item selected")
    expect(
        page.locator("#second-artifact_modal_root .querychat-artifact-gallery-item")
    ).to_have_class("querychat-artifact-gallery-item selected")
    expect(page.locator("#first-artifact_directions")).to_have_value("")
    expect(page.locator("#second-artifact_directions")).to_have_value(
        "Use a compact layout."
    )


def test_modal_inputs_update_only_the_clicked_module(page: Page) -> None:
    install_artifact_runtime(
        page,
        """
        <div id="first-artifact_modal_root" class="querychat-artifact-modal">
          <div class="querychat-artifact-gallery">
            <button class="querychat-artifact-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-artifact-type-selector">
            <button class="querychat-artifact-type-pill active" data-artifact-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-artifact-type-pill" data-artifact-type="other" data-languages="python,r"></button>
          </div>
          <div class="querychat-artifact-language-selector"></div>
          <div class="querychat-artifact-freeform-input hidden">
            <input>
          </div>
          <button id="first-artifact_generate" disabled></button>
        </div>
        <div id="second-artifact_modal_root" class="querychat-artifact-modal">
          <div class="querychat-artifact-gallery">
            <button class="querychat-artifact-gallery-item" data-item-id="query-0"></button>
          </div>
          <div class="querychat-artifact-type-selector">
            <button class="querychat-artifact-type-pill active" data-artifact-type="quarto-dashboard" data-languages="python,r"></button>
            <button class="querychat-artifact-type-pill" data-artifact-type="other" data-languages="python,r"></button>
          </div>
          <div class="querychat-artifact-language-selector"></div>
          <div class="querychat-artifact-freeform-input hidden">
            <input>
          </div>
          <button id="second-artifact_generate" disabled></button>
        </div>
        """,
    )

    second_modal = page.locator("#second-artifact_modal_root")
    second_modal.locator('[data-artifact-type="other"]').click()
    second_modal.locator(".querychat-artifact-gallery-item").click()
    second_modal.locator(".querychat-artifact-freeform-input input").fill("HTML")

    expect(
        page.locator("#first-artifact_modal_root .querychat-artifact-freeform-input")
    ).to_have_class("querychat-artifact-freeform-input hidden")
    expect(
        page.locator("#second-artifact_modal_root .querychat-artifact-freeform-input")
    ).to_have_class("querychat-artifact-freeform-input")
    expect(page.locator("#first-artifact_generate")).to_be_disabled()
    expect(page.locator("#second-artifact_generate")).to_be_enabled()
