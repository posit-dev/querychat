/* Generated file. Source: js/src/viz-r.ts. Do not edit directly. */

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

  // src/viz-r.ts
  function findGgsqlVizElement(widgetId) {
    const container = document.getElementById(widgetId);
    if (!container) {
      return null;
    }
    const tagName = container.tagName.toLowerCase();
    if (tagName === "ggsql-vega" || tagName === "ggsql-viz") {
      return container;
    }
    return container.querySelector("ggsql-vega, ggsql-viz");
  }
  function triggerDownload(url, filename) {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  }
  function exportFromView(vizElement, format, filename) {
    const view = vizElement._view;
    if (!view) {
      return;
    }
    if (format === "png") {
      view.toImageURL("png").then((url) => {
        triggerDownload(url, `${filename}.png`);
      }).catch((error) => {
        console.error("querychat: failed to export PNG:", error);
      });
      return;
    }
    view.toSVG().then((svg) => {
      const blob = new Blob([svg], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      triggerDownload(url, `${filename}.svg`);
      URL.revokeObjectURL(url);
    }).catch((error) => {
      console.error("querychat: failed to export SVG:", error);
    });
  }
  installVizFooter({
    exportPlot(widgetId, format, filename) {
      const vizElement = findGgsqlVizElement(widgetId);
      if (!vizElement) {
        return;
      }
      exportFromView(vizElement, format, filename);
    }
  });
})();
