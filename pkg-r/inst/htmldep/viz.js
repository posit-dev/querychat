(function () {
  // Helper: find the ggsql widget element by the output element ID used in
  // R/Shiny. The current widget is rendered as <ggsql-vega>, but older markup
  // may still wrap a nested custom element.
  function findGgsqlVizElement(widgetId) {
    var container = document.getElementById(widgetId);
    if (!container) return null;
    var tagName = container.tagName && container.tagName.toLowerCase();
    if (tagName === "ggsql-vega" || tagName === "ggsql-viz") return container;
    return container.querySelector("ggsql-vega, ggsql-viz");
  }

  // Helper: download a chart from a <ggsql-viz> element using the Vega View API.
  // <ggsql-viz> stores the Vega View instance as `._view` after vegaEmbed renders.
  function downloadFromView(vizEl, format, filename) {
    if (!vizEl || !vizEl._view) return;
    var view = vizEl._view;

    if (format === "png") {
      view.toImageURL("png").then(function (url) {
        triggerDownload(url, filename + ".png");
      }).catch(function (err) {
        console.error("querychat: failed to export PNG:", err);
      });
    } else if (format === "svg") {
      view.toSVG().then(function (svg) {
        var blob = new Blob([svg], { type: "image/svg+xml" });
        var url = URL.createObjectURL(blob);
        triggerDownload(url, filename + ".svg");
        URL.revokeObjectURL(url);
      }).catch(function (err) {
        console.error("querychat: failed to export SVG:", err);
      });
    }
  }

  function triggerDownload(url, filename) {
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  function closeAllSaveMenus() {
    document.querySelectorAll(".querychat-save-menu--visible").forEach(function (menu) {
      menu.classList.remove("querychat-save-menu--visible");
    });
  }

  function handleShowQuery(event, btn) {
    event.stopPropagation();
    var targetId = btn.dataset.target;
    var section = document.getElementById(targetId);
    if (!section) return;
    var isVisible = section.classList.toggle("querychat-query-section--visible");
    var label = btn.querySelector(".querychat-query-label");
    var chevron = btn.querySelector(".querychat-query-chevron");
    if (label) label.textContent = isVisible ? "Hide Query" : "Show Query";
    if (chevron) chevron.classList.toggle("querychat-query-chevron--expanded", isVisible);
  }

  function handleSaveToggle(event, btn) {
    event.stopPropagation();
    var menu = btn.parentElement.querySelector(".querychat-save-menu");
    if (menu) menu.classList.toggle("querychat-save-menu--visible");
  }

  function handleSaveExport(event, btn, format) {
    event.stopPropagation();
    var widgetId = btn.dataset.widgetId;
    var title = btn.dataset.title || "chart";
    var menu = btn.closest(".querychat-save-menu");
    if (menu) menu.classList.remove("querychat-save-menu--visible");

    var vizEl = findGgsqlVizElement(widgetId);
    if (!vizEl) return;
    downloadFromView(vizEl, format, title);
  }

  function handleCopy(event, btn) {
    event.stopPropagation();
    var query = btn.dataset.query;
    if (!query) return;
    navigator.clipboard.writeText(query).then(function () {
      var original = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(function () { btn.textContent = original; }, 2000);
    }).catch(function (err) {
      console.error("Failed to copy:", err);
    });
  }

  // Single delegated click handler for all querychat viz footer buttons.
  window.addEventListener("click", function (event) {
    var target = event.target;

    var btn = target.closest(".querychat-show-query-btn");
    if (btn) { handleShowQuery(event, btn); return; }

    btn = target.closest(".querychat-save-png-btn");
    if (btn) { handleSaveExport(event, btn, "png"); return; }

    btn = target.closest(".querychat-save-svg-btn");
    if (btn) { handleSaveExport(event, btn, "svg"); return; }

    btn = target.closest(".querychat-copy-btn");
    if (btn) { handleCopy(event, btn); return; }

    btn = target.closest(".querychat-save-btn");
    if (btn) { handleSaveToggle(event, btn); return; }

    // Click outside any button — close open save menus
    closeAllSaveMenus();
  });
})();
