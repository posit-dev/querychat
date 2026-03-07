// Helper: get the real click target, even inside Shadow DOM.
// event.target is retargeted to the shadow host when the click originates
// inside a shadow tree, so .closest() fails. composedPath() gives the
// full path including shadow-internal elements.
function deepTarget(event) {
  return event.composedPath()[0] || event.target;
}

// Helper: find a widget container by its base ID.
// Shiny module namespacing may prefix the ID (e.g. "mod-querychat_viz_abc"),
// so we match elements whose ID ends with the base widget ID.
function findWidgetContainer(widgetId) {
  return document.getElementById(widgetId)
    || document.querySelector('[id$="' + CSS.escape(widgetId) + '"]');
}

// Helper: get the SVG element from a widget container.
// Works with both vega-embed (via __view__) and shinywidgets (direct SVG).
function getChartSvg(container) {
  var vegaEmbed = container.querySelector(".vega-embed");
  if (!vegaEmbed) return null;
  return vegaEmbed.querySelector("svg");
}

// Helper: serialize an SVG element to a standalone SVG string.
function serializeSvg(svgEl) {
  var clone = svgEl.cloneNode(true);
  if (!clone.getAttribute("xmlns")) {
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  }
  return new XMLSerializer().serializeToString(clone);
}

// Helper: trigger a file download from a Blob.
function downloadBlob(blob, filename) {
  var url = URL.createObjectURL(blob);
  var link = document.createElement("a");
  link.download = filename;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

// Helper: close all visible save menus, including those inside Shadow DOM.
function closeAllSaveMenus() {
  // Light DOM
  document.querySelectorAll(".querychat-save-menu--visible").forEach(function (menu) {
    menu.classList.remove("querychat-save-menu--visible");
  });
  // Shadow DOM (shinychat tool result cards)
  document.querySelectorAll("shiny-tool-result").forEach(function (el) {
    var root = el.shadowRoot;
    if (!root) return;
    root.querySelectorAll(".querychat-save-menu--visible").forEach(function (menu) {
      menu.classList.remove("querychat-save-menu--visible");
    });
  });
}

(function () {
  if (!window.Shiny) return;

  window.addEventListener("click", function (event) {
    if (event.target.tagName.toLowerCase() !== "button") return;
    if (!event.target.matches(".querychat-update-dashboard-btn")) return;

    const chatContainer = event.target.closest("shiny-chat-container");
    if (!chatContainer) return;

    const chatId = chatContainer.id;
    const { query, title } = event.target.dataset;

    window.Shiny.setInputValue(
      chatId + "_update",
      { query, title },
      { priority: "event" }
    );
  });
})();

// Show/Hide Query toggle
window.addEventListener("click", function (event) {
  var btn = deepTarget(event).closest(".querychat-show-query-btn");
  if (!btn) return;
  event.stopPropagation();
  var targetId = btn.dataset.target;
  // Section may be inside the same shadow root as the button
  var root = btn.getRootNode();
  var section = root.getElementById
    ? root.getElementById(targetId)
    : document.getElementById(targetId);
  if (!section) return;
  var isVisible = section.classList.toggle("querychat-query-section--visible");
  var label = btn.querySelector(".querychat-query-label");
  var chevron = btn.querySelector(".querychat-query-chevron");
  if (label) label.textContent = isVisible ? "Hide Query" : "Show Query";
  if (chevron) chevron.classList.toggle("querychat-query-chevron--expanded", isVisible);
});

// Save dropdown toggle + close on outside click
window.addEventListener("click", function (event) {
  var btn = deepTarget(event).closest(".querychat-save-btn");
  if (btn) {
    event.stopPropagation();
    var menu = btn.parentElement.querySelector(".querychat-save-menu");
    if (menu) menu.classList.toggle("querychat-save-menu--visible");
    return;
  }
  closeAllSaveMenus();
});

// Save as PNG: render the chart SVG onto a canvas and export
window.addEventListener("click", function (event) {
  var btn = deepTarget(event).closest(".querychat-save-png-btn");
  if (!btn) return;
  event.stopPropagation();
  var widgetId = btn.dataset.widgetId;
  var title = btn.dataset.title || "chart";
  var menu = btn.closest(".querychat-save-menu");
  if (menu) menu.classList.remove("querychat-save-menu--visible");

  var container = findWidgetContainer(widgetId);
  if (!container) return;
  var svgEl = getChartSvg(container);
  if (!svgEl) return;

  var svgStr = serializeSvg(svgEl);
  var svgBlob = new Blob([svgStr], { type: "image/svg+xml;charset=utf-8" });
  var url = URL.createObjectURL(svgBlob);
  var img = new Image();
  var scale = 2;

  img.onload = function () {
    var canvas = document.createElement("canvas");
    canvas.width = img.width * scale;
    canvas.height = img.height * scale;
    var ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    ctx.drawImage(img, 0, 0);
    URL.revokeObjectURL(url);

    canvas.toBlob(function (blob) {
      if (blob) downloadBlob(blob, title + ".png");
    }, "image/png");
  };
  img.onerror = function () {
    console.error("Failed to save chart as PNG: SVG image load failed");
    URL.revokeObjectURL(url);
  };
  img.src = url;
});

// Save as SVG: extract the SVG directly from the DOM
window.addEventListener("click", function (event) {
  var btn = deepTarget(event).closest(".querychat-save-svg-btn");
  if (!btn) return;
  event.stopPropagation();
  var widgetId = btn.dataset.widgetId;
  var title = btn.dataset.title || "chart";
  var menu = btn.closest(".querychat-save-menu");
  if (menu) menu.classList.remove("querychat-save-menu--visible");

  var container = findWidgetContainer(widgetId);
  if (!container) return;
  var svgEl = getChartSvg(container);
  if (!svgEl) return;

  var svgStr = serializeSvg(svgEl);
  var blob = new Blob([svgStr], { type: "image/svg+xml" });
  downloadBlob(blob, title + ".svg");
});

