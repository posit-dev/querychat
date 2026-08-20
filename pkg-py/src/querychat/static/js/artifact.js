/* Generated file. Source: js/src/artifact.ts. Do not edit directly. */

"use strict";
(() => {
  // src/artifact-core.ts
  function artifactMessageName(action) {
    return `querychat-artifact-${action}`;
  }
  function getArtifactRoot(rootId) {
    return document.getElementById(rootId);
  }
  function getElementInRoot(root, id) {
    const element = document.getElementById(id);
    if (!element || !root.contains(element)) return null;
    return element;
  }
  function updateGenerateButton(modal) {
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
    const hasLanguage = Boolean(
      modal.querySelector(".querychat-artifact-language-pill.active")
    );
    generateBtn.disabled = selectedCount === 0 || !hasFreeformText || !hasLanguage;
  }
  function updateLanguagePills(modal, activeFormatPill) {
    const langsAttr = activeFormatPill?.getAttribute("data-languages") ?? "python,r";
    const supported = new Set(
      langsAttr.split(",").map((s) => s.trim()).filter(Boolean)
    );
    const selector = modal.querySelector(
      ".querychat-artifact-language-selector"
    );
    if (!selector) return;
    selector.querySelectorAll(".querychat-artifact-language-pill").forEach((p) => {
      const lang = p.getAttribute("data-language") ?? "";
      const ok = supported.has(lang);
      p.classList.toggle("disabled", !ok);
      p.disabled = !ok;
      if (!ok && p.classList.contains("active")) {
        p.classList.remove("active");
      }
    });
  }
  function handleDocumentClick(event, shiny) {
    const target = event.target;
    const genBtn = target.closest(
      "[id$='artifact_generate']"
    );
    if (genBtn) {
      if (genBtn.disabled) return;
      const modal = genBtn.closest(
        ".querychat-artifact-modal"
      );
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
      const root = reviseToggle.closest(".querychat-artifact-root");
      const drawer = root?.querySelector(".querychat-artifact-revise-drawer");
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
      const modal = typePill.closest(
        ".querychat-artifact-modal"
      );
      if (!modal) return;
      const selector = typePill.parentElement;
      if (selector) {
        selector.querySelectorAll(".querychat-artifact-type-pill").forEach((p) => {
          p.classList.remove("active");
        });
        typePill.classList.add("active");
        const typeId = typePill.getAttribute("data-artifact-type");
        const freeformWrapper = modal.querySelector(
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
      updateLanguagePills(modal, typePill);
      updateGenerateButton(modal);
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
      const modal = langPill.closest(
        ".querychat-artifact-modal"
      );
      if (modal) updateGenerateButton(modal);
      return;
    }
    const item = target.closest(
      ".querychat-artifact-gallery-item"
    );
    if (item) {
      item.classList.toggle("selected");
      const modal = item.closest(
        ".querychat-artifact-modal"
      );
      if (modal) updateGenerateButton(modal);
      return;
    }
  }
  function handleDocumentInput(event) {
    const target = event.target;
    const freeformWrapper = target.closest(".querychat-artifact-freeform-input");
    if (freeformWrapper) {
      const modal = freeformWrapper.closest(
        ".querychat-artifact-modal"
      );
      if (modal) updateGenerateButton(modal);
    }
  }
  function handleBackdropClick(event) {
    const target = event.target;
    if (!target.classList.contains("querychat-artifact-backdrop")) return;
    const root = target.closest(".querychat-artifact-root");
    const closeBtn = root?.querySelector(
      ".querychat-artifact-panel-header [id$='artifact_close']"
    );
    if (closeBtn) closeBtn.click();
  }
  function handleRecommend(msg, shiny) {
    const modal = getArtifactRoot(msg.root_id);
    if (!modal) return;
    const selectedIds = new Set(msg.selected_ids);
    const gallery = modal.querySelector(".querychat-artifact-gallery");
    if (gallery) {
      gallery.classList.remove("loading");
    }
    modal.querySelectorAll(".querychat-artifact-gallery-item").forEach((el) => {
      const itemId = el.dataset.itemId;
      if (itemId && selectedIds.has(itemId)) {
        el.classList.add("selected");
      } else {
        el.classList.remove("selected");
      }
    });
    if (msg.format_id) {
      const selector = modal.querySelector(
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
          updateLanguagePills(modal, targetPill);
        }
      }
    }
    const directionsWrapper = modal.querySelector(
      ".querychat-artifact-directions-wrapper"
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
      ".querychat-artifact-directions-subtitle"
    );
    if (subtitle) {
      subtitle.classList.remove("hidden");
    }
    const status = modal.querySelector(".querychat-artifact-loading-status");
    if (status) {
      status.classList.add("hidden");
    }
    updateGenerateButton(modal);
  }
  function handleRecommendError(msg) {
    const modal = getArtifactRoot(msg.root_id);
    if (!modal) return;
    const gallery = modal.querySelector(".querychat-artifact-gallery");
    if (gallery) {
      gallery.classList.remove("loading");
    }
    const directionsWrapper = modal.querySelector(
      ".querychat-artifact-directions-wrapper"
    );
    if (directionsWrapper) {
      directionsWrapper.classList.remove("loading");
    }
    const directionsEl = modal.querySelector(
      ".querychat-artifact-directions-wrapper textarea"
    );
    if (directionsEl) {
      directionsEl.disabled = false;
    }
    const status = modal.querySelector(".querychat-artifact-loading-status");
    if (status) {
      status.classList.remove("hidden");
      status.classList.add("error");
      status.textContent = msg.error ? `Couldn't auto-suggest results: ${msg.error}. Select and configure manually.` : "Couldn't auto-suggest results. Select and configure manually.";
    }
    updateGenerateButton(modal);
  }
  function handleSourceUpdate(msg) {
    const root = getArtifactRoot(msg.root_id);
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
        "[id$='artifact_download']"
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
    return root.querySelector(".querychat-artifact-panel");
  }
  function handleStreaming(msg) {
    const root = getArtifactRoot(msg.root_id);
    if (!root) return;
    const panel = getPanel(root);
    if (panel) panel.classList.toggle("streaming", msg.active);
  }
  function handlePanelToggle(msg) {
    const root = getArtifactRoot(msg.root_id);
    if (!root) return;
    const panel = getPanel(root);
    const backdrop = root.querySelector(".querychat-artifact-backdrop");
    if (panel) panel.classList.toggle("open", msg.open);
    if (backdrop) backdrop.classList.toggle("open", msg.open);
    if (!msg.open) {
      const drawer = root.querySelector(".querychat-artifact-revise-drawer");
      const toggle = root.querySelector(".querychat-artifact-revise-toggle");
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
      artifactMessageName("recommend"),
      (msg) => handleRecommend(msg, shiny)
    );
    shiny.addCustomMessageHandler(
      artifactMessageName("recommend-error"),
      handleRecommendError
    );
    shiny.addCustomMessageHandler(
      artifactMessageName("source-update"),
      handleSourceUpdate
    );
    shiny.addCustomMessageHandler(
      artifactMessageName("streaming"),
      handleStreaming
    );
    shiny.addCustomMessageHandler(
      artifactMessageName("panel-toggle"),
      handlePanelToggle
    );
  }

  // src/artifact.ts
  var Shiny = window.Shiny;
  if (Shiny) installArtifact(Shiny);
})();
