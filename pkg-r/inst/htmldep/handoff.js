/* Generated file. Source: js/src/handoff.ts. Do not edit directly. */

"use strict";
(() => {
  // src/handoff-core.ts
  function handoffMessageName(action) {
    return `querychat-handoff-${action}`;
  }
  function getHandoffRoot(rootId) {
    return document.getElementById(rootId);
  }
  function getElementInRoot(root, id) {
    const element = document.getElementById(id);
    if (!element || !root.contains(element)) return null;
    return element;
  }
  function updateGenerateButton(modal) {
    const generateBtn = modal.querySelector(
      "[id$='handoff_generate']"
    );
    if (!generateBtn) return;
    const gallery = modal.querySelector(".querychat-handoff-gallery");
    if (gallery && gallery.classList.contains("loading")) {
      generateBtn.disabled = true;
      return;
    }
    const selectedCount = modal.querySelectorAll(
      ".querychat-handoff-gallery-item.selected"
    ).length;
    const activePill = modal.querySelector(
      ".querychat-handoff-type-pill.active"
    );
    const isOther = activePill?.getAttribute("data-handoff-type") === "other";
    const freeformInput = modal.querySelector(
      ".querychat-handoff-freeform-input input"
    );
    const hasFreeformText = !isOther || (freeformInput?.value.trim().length ?? 0) > 0;
    const hasLanguage = Boolean(
      modal.querySelector(".querychat-handoff-language-radio:checked")
    );
    generateBtn.disabled = selectedCount === 0 || !hasFreeformText || !hasLanguage;
  }
  function updateLanguagePills(modal, activeFormatPill) {
    const langsAttr = activeFormatPill?.getAttribute("data-languages") ?? "python,r";
    const supported = new Set(
      langsAttr.split(",").map((s) => s.trim()).filter(Boolean)
    );
    const selector = modal.querySelector(
      ".querychat-handoff-language-selector"
    );
    if (!selector) return;
    const radios = Array.from(
      selector.querySelectorAll(".querychat-handoff-language-radio")
    );
    radios.forEach((radio) => {
      const lang = radio.getAttribute("data-language") ?? "";
      const ok = supported.has(lang);
      radio.classList.toggle("disabled", !ok);
      radio.disabled = !ok;
      radio.closest(".querychat-handoff-language-option")?.classList.toggle(
        "disabled",
        !ok
      );
    });
    if (!radios.some((radio) => radio.checked && !radio.disabled)) {
      const firstSupported = radios.find((radio) => !radio.disabled);
      if (firstSupported) firstSupported.checked = true;
    }
  }
  function handleDocumentClick(event, shiny) {
    const target = event.target;
    const genBtn = target.closest(
      "[id$='handoff_generate']"
    );
    if (genBtn) {
      if (genBtn.disabled) return;
      const modal = genBtn.closest(
        ".querychat-handoff-modal"
      );
      if (!modal) return;
      const selected_ids = Array.from(
        modal.querySelectorAll(".querychat-handoff-gallery-item.selected")
      ).map((el) => el.dataset.itemId).filter((id) => Boolean(id));
      const activeType = modal.querySelector(
        ".querychat-handoff-type-pill.active"
      );
      const type = activeType?.getAttribute("data-handoff-type") ?? "";
      const activeLang = modal.querySelector(
        ".querychat-handoff-language-radio:checked"
      );
      const language = activeLang?.getAttribute("data-language") ?? "";
      const freeformInput = modal.querySelector(
        ".querychat-handoff-freeform-input input"
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
      ".querychat-handoff-revise-toggle"
    );
    if (reviseToggle) {
      const root = reviseToggle.closest(".querychat-handoff-root");
      const drawer = root?.querySelector(".querychat-handoff-revise-drawer");
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
      ".querychat-handoff-pill"
    );
    if (pill) {
      const inputId = pill.getAttribute("data-input-id");
      const handoffId = pill.getAttribute("data-handoff-id");
      if (inputId && handoffId) {
        shiny.setInputValue(inputId, handoffId, { priority: "event" });
      }
      return;
    }
    const typePill = target.closest(
      ".querychat-handoff-type-pill"
    );
    if (typePill) {
      const modal = typePill.closest(
        ".querychat-handoff-modal"
      );
      if (!modal) return;
      const selector = typePill.parentElement;
      if (selector) {
        selector.querySelectorAll(".querychat-handoff-type-pill").forEach((p) => {
          p.classList.remove("active");
        });
        typePill.classList.add("active");
        const typeId = typePill.getAttribute("data-handoff-type");
        const freeformWrapper = modal.querySelector(
          ".querychat-handoff-freeform-input"
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
      updateLanguagePills(modal, typePill);
      updateGenerateButton(modal);
      return;
    }
    const item = target.closest(
      ".querychat-handoff-gallery-item"
    );
    if (item) {
      item.classList.toggle("selected");
      const modal = item.closest(
        ".querychat-handoff-modal"
      );
      if (modal) updateGenerateButton(modal);
      return;
    }
  }
  function handleDocumentInput(event) {
    const target = event.target;
    const freeformWrapper = target.closest(".querychat-handoff-freeform-input");
    if (freeformWrapper) {
      const modal = freeformWrapper.closest(
        ".querychat-handoff-modal"
      );
      if (modal) updateGenerateButton(modal);
    }
  }
  function handleDocumentChange(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement) || !target.matches(".querychat-handoff-language-radio")) {
      return;
    }
    const modal = target.closest(
      ".querychat-handoff-modal"
    );
    if (modal) updateGenerateButton(modal);
  }
  function handleBackdropClick(event) {
    const target = event.target;
    if (!target.classList.contains("querychat-handoff-backdrop")) return;
    const root = target.closest(".querychat-handoff-root");
    const closeBtn = root?.querySelector(
      ".querychat-handoff-panel-header [id$='handoff_close']"
    );
    if (closeBtn) closeBtn.click();
  }
  function handleRecommend(msg, shiny) {
    const modal = getHandoffRoot(msg.root_id);
    if (!modal) return;
    const selectedIds = new Set(msg.selected_ids);
    const gallery = modal.querySelector(".querychat-handoff-gallery");
    if (gallery) {
      gallery.classList.remove("loading");
    }
    modal.querySelectorAll(".querychat-handoff-gallery-item").forEach((el) => {
      const itemId = el.dataset.itemId;
      if (itemId && selectedIds.has(itemId)) {
        el.classList.add("selected");
      } else {
        el.classList.remove("selected");
      }
    });
    if (msg.format_id) {
      const selector = modal.querySelector(
        ".querychat-handoff-type-selector"
      );
      if (selector) {
        const targetPill = selector.querySelector(
          `[data-handoff-type="${msg.format_id}"]`
        );
        if (targetPill) {
          selector.querySelectorAll(".querychat-handoff-type-pill").forEach((p) => {
            p.classList.remove("active");
          });
          targetPill.classList.add("active");
          updateLanguagePills(modal, targetPill);
        }
      }
    }
    const directionsWrapper = modal.querySelector(
      ".querychat-handoff-directions-wrapper"
    );
    if (directionsWrapper) {
      directionsWrapper.classList.remove("loading");
    }
    const directionsEl = getElementInRoot(
      modal,
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
    const subtitle = modal.querySelector(
      ".querychat-handoff-directions-subtitle"
    );
    if (subtitle) {
      subtitle.classList.remove("hidden");
    }
    const status = modal.querySelector(".querychat-handoff-loading-status");
    if (status) {
      status.classList.add("hidden");
    }
    updateGenerateButton(modal);
  }
  function handleRecommendError(msg) {
    const modal = getHandoffRoot(msg.root_id);
    if (!modal) return;
    const gallery = modal.querySelector(".querychat-handoff-gallery");
    if (gallery) {
      gallery.classList.remove("loading");
    }
    const directionsWrapper = modal.querySelector(
      ".querychat-handoff-directions-wrapper"
    );
    if (directionsWrapper) {
      directionsWrapper.classList.remove("loading");
    }
    const directionsEl = modal.querySelector(
      ".querychat-handoff-directions-wrapper textarea"
    );
    if (directionsEl) {
      directionsEl.disabled = false;
    }
    const status = modal.querySelector(".querychat-handoff-loading-status");
    if (status) {
      status.classList.remove("hidden");
      status.classList.add("error");
      status.textContent = msg.error ? `Couldn't auto-suggest results: ${msg.error}. Select and configure manually.` : "Couldn't auto-suggest results. Select and configure manually.";
    }
    updateGenerateButton(modal);
  }
  function handleSourceUpdate(msg) {
    const root = getHandoffRoot(msg.root_id);
    if (!root) return;
    const el = getElementInRoot(root, msg.id);
    if (el) {
      if (msg.language) {
        el.language = msg.language;
      }
      el.value = msg.append ? el.value + msg.value : msg.value;
    }
    if (msg.download_available !== void 0) {
      const downloadBtn = root.querySelector(
        "[id$='handoff_download']"
      );
      if (downloadBtn) {
        downloadBtn.classList.toggle("disabled", !msg.download_available);
        downloadBtn.setAttribute("aria-disabled", String(!msg.download_available));
        downloadBtn.tabIndex = msg.download_available ? 0 : -1;
        downloadBtn.title = msg.download_available ? "Download" : "Download unavailable: data snapshot is no longer available";
      }
    }
  }
  function getPanel(root) {
    return root.querySelector(".querychat-handoff-panel");
  }
  function handleStreaming(msg) {
    const root = getHandoffRoot(msg.root_id);
    if (!root) return;
    const panel = getPanel(root);
    if (panel) panel.classList.toggle("streaming", msg.active);
  }
  function handlePanelToggle(msg) {
    const root = getHandoffRoot(msg.root_id);
    if (!root) return;
    const panel = getPanel(root);
    const backdrop = root.querySelector(".querychat-handoff-backdrop");
    if (panel) panel.classList.toggle("open", msg.open);
    if (backdrop) backdrop.classList.toggle("open", msg.open);
    if (!msg.open) {
      const drawer = root.querySelector(".querychat-handoff-revise-drawer");
      const toggle = root.querySelector(".querychat-handoff-revise-toggle");
      if (drawer) drawer.classList.remove("open");
      if (toggle) toggle.classList.remove("active");
    }
  }
  function installHandoff(shiny) {
    document.addEventListener(
      "click",
      (event) => handleDocumentClick(event, shiny)
    );
    document.addEventListener("input", handleDocumentInput);
    document.addEventListener("change", handleDocumentChange);
    document.addEventListener("click", handleBackdropClick);
    shiny.addCustomMessageHandler(
      handoffMessageName("recommend"),
      (msg) => handleRecommend(msg, shiny)
    );
    shiny.addCustomMessageHandler(
      handoffMessageName("recommend-error"),
      handleRecommendError
    );
    shiny.addCustomMessageHandler(
      handoffMessageName("source-update"),
      handleSourceUpdate
    );
    shiny.addCustomMessageHandler(
      handoffMessageName("streaming"),
      handleStreaming
    );
    shiny.addCustomMessageHandler(
      handoffMessageName("panel-toggle"),
      handlePanelToggle
    );
  }

  // src/handoff.ts
  var Shiny = window.Shiny;
  if (Shiny) installHandoff(Shiny);
})();
