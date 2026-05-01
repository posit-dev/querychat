/* Generated file. Source: js/src/viz-r.ts. Do not edit directly. */

"use strict";
(() => {
  // src/viz-core.ts
  function findWidgetContainer(widgetId) {
    return document.getElementById(widgetId);
  }
  function findVegaAction(container, format) {
    return container.querySelector(
      `.vega-actions a[download$=".${format}"]`
    );
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
  var openSaveMenu = null;
  function closeSaveMenu(menu) {
    menu.classList.remove("querychat-save-menu--visible");
    if (openSaveMenu === menu) {
      openSaveMenu = null;
    }
  }
  function closeOpenSaveMenu() {
    if (openSaveMenu) {
      closeSaveMenu(openSaveMenu);
    }
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
    if (!menu) {
      return;
    }
    if (openSaveMenu && openSaveMenu !== menu) {
      closeSaveMenu(openSaveMenu);
    }
    if (menu.classList.contains("querychat-save-menu--visible")) {
      closeSaveMenu(menu);
    } else {
      menu.classList.add("querychat-save-menu--visible");
      openSaveMenu = menu;
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
      closeSaveMenu(menu);
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
        closeOpenSaveMenu();
        return;
      }
      const actionElement = target.closest("[data-querychat-action]");
      const action = actionElement?.dataset.querychatAction;
      if (!action || !actionElement) {
        closeOpenSaveMenu();
        return;
      }
      switch (action) {
        case "show-query":
          handleShowQuery(event, actionElement);
          return;
        case "save-toggle":
          handleSaveToggle(event, actionElement);
          return;
        case "save-png":
          handleSaveExport(event, actionElement, "png", adapter);
          return;
        case "save-svg":
          handleSaveExport(event, actionElement, "svg", adapter);
          return;
        case "copy":
          handleCopy(event, actionElement);
          return;
      }
    });
  }
  function createVegaActionAdapter() {
    return {
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
    };
  }

  // src/viz-r.ts
  installVizFooter(createVegaActionAdapter());
})();
