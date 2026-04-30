/* Generated file. Source: js/src/viz-py.ts. Do not edit directly. */

"use strict";
(() => {
  // src/viz-core.ts
  function closeAllSaveMenus() {
    document.querySelectorAll(".querychat-save-menu--visible").forEach((menu) => {
      menu.classList.remove("querychat-save-menu--visible");
    });
  }
  function handleShowQuery(event, button) {
    event.stopPropagation();
    const targetId = button.dataset.target;
    if (!targetId) {
      return;
    }
    const section = document.getElementById(targetId);
    if (!section) {
      return;
    }
    const isVisible = section.classList.toggle("querychat-query-section--visible");
    const label = button.querySelector(".querychat-query-label");
    const chevron = button.querySelector(".querychat-query-chevron");
    if (label) {
      label.textContent = isVisible ? "Hide Query" : "Show Query";
    }
    if (chevron) {
      chevron.classList.toggle("querychat-query-chevron--expanded", isVisible);
    }
  }
  function handleSaveToggle(event, button) {
    event.stopPropagation();
    const menu = button.parentElement?.querySelector(
      ".querychat-save-menu"
    );
    if (menu) {
      menu.classList.toggle("querychat-save-menu--visible");
    }
  }
  function handleSaveExport(event, button, format, adapter) {
    event.stopPropagation();
    const widgetId = button.dataset.widgetId;
    if (!widgetId) {
      return;
    }
    const filename = button.dataset.title || "chart";
    const menu = button.closest(".querychat-save-menu");
    if (menu) {
      menu.classList.remove("querychat-save-menu--visible");
    }
    adapter.exportPlot(widgetId, format, filename);
  }
  function handleCopy(event, button) {
    event.stopPropagation();
    const query = button.dataset.query;
    if (!query) {
      return;
    }
    navigator.clipboard.writeText(query).then(() => {
      const original = button.textContent;
      button.textContent = "Copied!";
      setTimeout(() => {
        button.textContent = original;
      }, 2e3);
    }).catch((error) => {
      console.error("Failed to copy:", error);
    });
  }
  function installVizFooter(adapter) {
    window.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        closeAllSaveMenus();
        return;
      }
      const showQueryButton = target.closest(".querychat-show-query-btn");
      if (showQueryButton) {
        handleShowQuery(event, showQueryButton);
        return;
      }
      const savePngButton = target.closest(".querychat-save-png-btn");
      if (savePngButton) {
        handleSaveExport(event, savePngButton, "png", adapter);
        return;
      }
      const saveSvgButton = target.closest(".querychat-save-svg-btn");
      if (saveSvgButton) {
        handleSaveExport(event, saveSvgButton, "svg", adapter);
        return;
      }
      const copyButton = target.closest(".querychat-copy-btn");
      if (copyButton) {
        handleCopy(event, copyButton);
        return;
      }
      const saveButton = target.closest(".querychat-save-btn");
      if (saveButton) {
        handleSaveToggle(event, saveButton);
        return;
      }
      closeAllSaveMenus();
    });
  }

  // src/viz-py.ts
  function findVegaAction(container, extension) {
    return container.querySelector(
      `.vega-actions a[download$=".${extension}"]`
    );
  }
  function findWidgetContainer(widgetId) {
    return document.getElementById(widgetId) || document.querySelector(`[id$="${CSS.escape(widgetId)}"]`);
  }
  function triggerVegaAction(link, filename) {
    link.download = filename;
    if (link.href && link.href !== "#" && !link.href.endsWith("#")) {
      link.click();
      return;
    }
    const observer = new MutationObserver(() => {
      if (link.href && link.href !== "#" && !link.href.endsWith("#")) {
        observer.disconnect();
        clearTimeout(timeoutId);
        link.click();
      }
    });
    observer.observe(link, {
      attributes: true,
      attributeFilter: ["href"]
    });
    const timeoutId = window.setTimeout(() => {
      observer.disconnect();
      console.error("Timed out waiting for vega-embed to generate image");
    }, 5e3);
    link.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  }
  installVizFooter({
    exportPlot(widgetId, format, filename) {
      const container = findWidgetContainer(widgetId);
      if (!container) {
        return;
      }
      const link = findVegaAction(container, format);
      if (!link) {
        return;
      }
      triggerVegaAction(link, `${filename}.${format}`);
    }
  });
})();
