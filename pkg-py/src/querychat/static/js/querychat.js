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
  var btn = event.target.closest(".querychat-show-query-btn");
  if (!btn) return;
  event.stopPropagation();
  var targetId = btn.dataset.target;
  var section = document.getElementById(targetId);
  if (!section) return;
  var isVisible = section.classList.toggle("querychat-query-section--visible");
  var label = btn.querySelector(".querychat-query-label");
  var chevron = btn.querySelector(".querychat-query-chevron");
  if (label) label.textContent = isVisible ? "Hide Query" : "Show Query";
  if (chevron) chevron.classList.toggle("querychat-query-chevron--expanded", isVisible);
});

// Save dropdown toggle + close on outside click
window.addEventListener("click", function (event) {
  var btn = event.target.closest(".querychat-save-btn");
  if (btn) {
    event.stopPropagation();
    var menu = btn.parentElement.querySelector(".querychat-save-menu");
    if (menu) menu.classList.toggle("querychat-save-menu--visible");
    return;
  }
  document.querySelectorAll(".querychat-save-menu--visible").forEach(function (menu) {
    menu.classList.remove("querychat-save-menu--visible");
  });
});

// Save as PNG via Vega view API
window.addEventListener("click", function (event) {
  var btn = event.target.closest(".querychat-save-png-btn");
  if (!btn) return;
  event.stopPropagation();
  var widgetId = btn.dataset.widgetId;
  var title = btn.dataset.title || "chart";
  var menu = btn.closest(".querychat-save-menu");
  if (menu) menu.classList.remove("querychat-save-menu--visible");
  var container = document.getElementById(widgetId);
  if (!container) return;
  var vegaEmbed = container.querySelector(".vega-embed");
  if (!vegaEmbed || !vegaEmbed.__view__) return;
  vegaEmbed.__view__.toCanvas(2).then(function (canvas) {
    var url = canvas.toDataURL("image/png");
    var link = document.createElement("a");
    link.download = title + ".png";
    link.href = url;
    link.click();
  }).catch(function (err) {
    console.error("Failed to save chart as PNG:", err);
  });
});

// Save as SVG via Vega view API
window.addEventListener("click", function (event) {
  var btn = event.target.closest(".querychat-save-svg-btn");
  if (!btn) return;
  event.stopPropagation();
  var widgetId = btn.dataset.widgetId;
  var title = btn.dataset.title || "chart";
  var menu = btn.closest(".querychat-save-menu");
  if (menu) menu.classList.remove("querychat-save-menu--visible");
  var container = document.getElementById(widgetId);
  if (!container) return;
  var vegaEmbed = container.querySelector(".vega-embed");
  if (!vegaEmbed || !vegaEmbed.__view__) return;
  vegaEmbed.__view__.toSVG().then(function (svg) {
    var blob = new Blob([svg], { type: "image/svg+xml" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.download = title + ".svg";
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }).catch(function (err) {
    console.error("Failed to save chart as SVG:", err);
  });
});

// Copy query to clipboard
window.addEventListener("click", function (event) {
  var btn = event.target.closest(".querychat-copy-btn");
  if (!btn) return;
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
});