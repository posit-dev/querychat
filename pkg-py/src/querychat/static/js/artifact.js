/* Generated file. Source: js/src/artifact.ts. Do not edit directly. */

"use strict";
(() => {
  // src/artifact-core.ts
  function updateGenerateButton() {
    const modal = document.querySelector(".modal");
    if (!modal) return;
    const generateBtn = modal.querySelector(
      "[id$='artifact_generate']"
    );
    if (!generateBtn) return;
    const gallery = modal.querySelector(".querychat-artifact-gallery");
    if (gallery && gallery.classList.contains("loading")) {
      generateBtn.disabled = true;
      return;
    }
    const selectedCount = modal.querySelectorAll(
      ".querychat-artifact-gallery-item.selected"
    ).length;
    const activePill = modal.querySelector(
      ".querychat-artifact-type-pill.active"
    );
    const isOther = activePill?.getAttribute("data-artifact-type") === "other";
    const freeformInput = modal.querySelector(
      ".querychat-artifact-freeform-input input"
    );
    const hasFreeformText = !isOther || (freeformInput?.value.trim().length ?? 0) > 0;
    generateBtn.disabled = selectedCount === 0 || !hasFreeformText;
  }
  function updateLanguagePills(activeFormatPill) {
    const langsAttr = activeFormatPill?.getAttribute("data-languages") ?? "python,r";
    const supported = new Set(
      langsAttr.split(",").map((s) => s.trim()).filter(Boolean)
    );
    const selector = document.querySelector(
      ".querychat-artifact-language-selector"
    );
    if (!selector) return;
    let resetNeeded = false;
    selector.querySelectorAll(".querychat-artifact-language-pill").forEach((p) => {
      const lang = p.getAttribute("data-language") ?? "";
      const ok = lang === "" || supported.has(lang);
      p.classList.toggle("disabled", !ok);
      p.disabled = !ok;
      if (!ok && p.classList.contains("active")) {
        p.classList.remove("active");
        resetNeeded = true;
      }
    });
    if (resetNeeded) {
      const noPref = selector.querySelector(
        '.querychat-artifact-language-pill[data-language=""]'
      );
      if (noPref) {
        noPref.classList.add("active");
      }
    }
  }
  function handleDocumentClick(event, shiny) {
    const target = event.target;
    const genBtn = target.closest(
      "[id$='artifact_generate']"
    );
    if (genBtn) {
      if (genBtn.disabled) return;
      const modal = document.querySelector(".modal");
      if (!modal) return;
      const selected_ids = Array.from(
        modal.querySelectorAll(".querychat-artifact-gallery-item.selected")
      ).map((el) => el.dataset.itemId).filter((id) => Boolean(id));
      const activeType = modal.querySelector(
        ".querychat-artifact-type-pill.active"
      );
      const type = activeType?.getAttribute("data-artifact-type") ?? "";
      const activeLang = modal.querySelector(
        ".querychat-artifact-language-pill.active"
      );
      const language = activeLang?.getAttribute("data-language") ?? "";
      const freeformInput = modal.querySelector(
        ".querychat-artifact-freeform-input input"
      );
      const freeform = freeformInput?.value.trim() ?? "";
      shiny.setInputValue(
        genBtn.id,
        { selected_ids, type, language, freeform },
        { priority: "event" }
      );
      return;
    }
    const reviseToggle = target.closest(
      ".querychat-artifact-revise-toggle"
    );
    if (reviseToggle) {
      const drawer = document.querySelector(".querychat-artifact-revise-drawer");
      if (drawer) {
        const isOpen = drawer.classList.toggle("open");
        reviseToggle.classList.toggle("active", isOpen);
        if (isOpen) {
          const textarea = drawer.querySelector(
            "textarea"
          );
          if (textarea) textarea.focus();
        }
      }
      return;
    }
    const pill = target.closest(
      ".querychat-artifact-pill"
    );
    if (pill) {
      const inputId = pill.getAttribute("data-input-id");
      const artifactId = pill.getAttribute("data-artifact-id");
      if (inputId && artifactId) {
        shiny.setInputValue(inputId, artifactId, { priority: "event" });
      }
      return;
    }
    const typePill = target.closest(
      ".querychat-artifact-type-pill"
    );
    if (typePill) {
      const selector = typePill.parentElement;
      if (selector) {
        selector.querySelectorAll(".querychat-artifact-type-pill").forEach((p) => {
          p.classList.remove("active");
        });
        typePill.classList.add("active");
        const typeId = typePill.getAttribute("data-artifact-type");
        const freeformWrapper = document.querySelector(
          ".querychat-artifact-freeform-input"
        );
        if (freeformWrapper) {
          if (typeId === "other") {
            freeformWrapper.classList.remove("hidden");
            const textInput = freeformWrapper.querySelector(
              "input"
            );
            if (textInput) textInput.focus();
          } else {
            freeformWrapper.classList.add("hidden");
          }
        }
      }
      updateLanguagePills(typePill);
      updateGenerateButton();
      return;
    }
    const langPill = target.closest(
      ".querychat-artifact-language-pill"
    );
    if (langPill) {
      if (langPill.disabled) return;
      const selector = langPill.parentElement;
      if (selector) {
        selector.querySelectorAll(".querychat-artifact-language-pill").forEach((p) => p.classList.remove("active"));
        langPill.classList.add("active");
      }
      return;
    }
    const item = target.closest(
      ".querychat-artifact-gallery-item"
    );
    if (item) {
      item.classList.toggle("selected");
      updateGenerateButton();
      return;
    }
  }
  function handleDocumentInput(event) {
    const target = event.target;
    const freeformWrapper = target.closest(".querychat-artifact-freeform-input");
    if (freeformWrapper) {
      updateGenerateButton();
    }
  }
  function handleBackdropClick(event) {
    const target = event.target;
    if (!target.classList.contains("querychat-artifact-backdrop")) return;
    const closeBtn = document.querySelector(
      ".querychat-artifact-panel-header [id$='artifact_close']"
    );
    if (closeBtn) closeBtn.click();
  }
  function handleRecommend(msg, shiny) {
    const selectedIds = new Set(msg.selected_ids);
    const gallery = document.querySelector(".querychat-artifact-gallery");
    if (gallery) {
      gallery.classList.remove("loading");
    }
    document.querySelectorAll(".querychat-artifact-gallery-item").forEach((el) => {
      const itemId = el.dataset.itemId;
      if (itemId && selectedIds.has(itemId)) {
        el.classList.add("selected");
      } else {
        el.classList.remove("selected");
      }
    });
    if (msg.format_id) {
      const selector = document.querySelector(
        ".querychat-artifact-type-selector"
      );
      if (selector) {
        const targetPill = selector.querySelector(
          `[data-artifact-type="${msg.format_id}"]`
        );
        if (targetPill) {
          selector.querySelectorAll(".querychat-artifact-type-pill").forEach((p) => {
            p.classList.remove("active");
          });
          targetPill.classList.add("active");
          updateLanguagePills(targetPill);
        }
      }
    }
    const directionsWrapper = document.querySelector(
      ".querychat-artifact-directions-wrapper"
    );
    if (directionsWrapper) {
      directionsWrapper.classList.remove("loading");
    }
    const directionsEl = document.getElementById(
      msg.directions_id
    );
    if (directionsEl) {
      directionsEl.disabled = false;
      if (msg.directions) {
        directionsEl.value = msg.directions;
        directionsEl.dispatchEvent(new Event("input", { bubbles: true }));
        shiny.setInputValue(msg.directions_id, msg.directions);
      }
    }
    const subtitle = document.querySelector(
      ".querychat-artifact-directions-subtitle"
    );
    if (subtitle) {
      subtitle.classList.remove("hidden");
    }
    const status = document.querySelector(".querychat-artifact-loading-status");
    if (status) {
      status.classList.add("hidden");
    }
    updateGenerateButton();
  }
  function handleRecommendError(msg) {
    const gallery = document.querySelector(".querychat-artifact-gallery");
    if (gallery) {
      gallery.classList.remove("loading");
    }
    const directionsWrapper = document.querySelector(
      ".querychat-artifact-directions-wrapper"
    );
    if (directionsWrapper) {
      directionsWrapper.classList.remove("loading");
    }
    const directionsEl = document.querySelector(
      ".querychat-artifact-directions-wrapper textarea"
    );
    if (directionsEl) {
      directionsEl.disabled = false;
    }
    const status = document.querySelector(".querychat-artifact-loading-status");
    if (status) {
      status.classList.remove("hidden");
      status.classList.add("error");
      status.textContent = msg.error ? `Couldn't auto-suggest results: ${msg.error}. Select and configure manually.` : "Couldn't auto-suggest results. Select and configure manually.";
    }
    updateGenerateButton();
  }
  function handleSourceUpdate(msg) {
    const el = document.getElementById(msg.id);
    if (el) {
      if (msg.language) {
        el.language = msg.language;
      }
      el.value = msg.value;
    }
  }
  function getPanel() {
    return document.querySelector(".querychat-artifact-panel");
  }
  function handleStreaming(msg) {
    const panel = getPanel();
    if (panel) panel.classList.toggle("streaming", msg.active);
  }
  function handleVersionUpdate(msg) {
    const panel = getPanel();
    if (!panel) return;
    const nav = panel.querySelector(".querychat-artifact-version-nav");
    if (nav) nav.classList.toggle("show", msg.total > 1);
    const labelEl = panel.querySelector(".querychat-artifact-version-label");
    if (labelEl) labelEl.textContent = msg.label;
    const prevBtn = panel.querySelector(
      "[id$='artifact_version_prev']"
    );
    const nextBtn = panel.querySelector(
      "[id$='artifact_version_next']"
    );
    if (prevBtn) prevBtn.disabled = msg.prev_disabled;
    if (nextBtn) nextBtn.disabled = msg.next_disabled;
  }
  function handlePanelToggle(msg) {
    const panel = getPanel();
    const backdrop = document.querySelector(".querychat-artifact-backdrop");
    if (panel) panel.classList.toggle("open", msg.open);
    if (backdrop) backdrop.classList.toggle("open", msg.open);
    if (!msg.open) {
      const drawer = document.querySelector(".querychat-artifact-revise-drawer");
      const toggle = document.querySelector(".querychat-artifact-revise-toggle");
      if (drawer) drawer.classList.remove("open");
      if (toggle) toggle.classList.remove("active");
    }
  }
  function installArtifact(shiny) {
    document.addEventListener(
      "click",
      (event) => handleDocumentClick(event, shiny)
    );
    document.addEventListener("input", handleDocumentInput);
    document.addEventListener("click", handleBackdropClick);
    shiny.addCustomMessageHandler(
      "querychat-artifact-recommend",
      (msg) => handleRecommend(msg, shiny)
    );
    shiny.addCustomMessageHandler(
      "querychat-artifact-recommend-error",
      handleRecommendError
    );
    shiny.addCustomMessageHandler(
      "querychat-artifact-source-update",
      handleSourceUpdate
    );
    shiny.addCustomMessageHandler(
      "querychat-artifact-streaming",
      handleStreaming
    );
    shiny.addCustomMessageHandler(
      "querychat-artifact-version-update",
      handleVersionUpdate
    );
    shiny.addCustomMessageHandler(
      "querychat-artifact-panel-toggle",
      handlePanelToggle
    );
  }

  // src/artifact.ts
  var Shiny = window.Shiny;
  if (Shiny) installArtifact(Shiny);
})();
