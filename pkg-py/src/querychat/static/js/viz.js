// Helper: find a native vega-embed action link inside a widget container.
// vega-embed renders a hidden <details> with <a> tags for "Save as SVG",
// "Save as PNG", etc. We find them by matching the download attribute suffix.
//
// Why not use the Vega View API (view.toSVG(), view.toImageURL()) directly?
// Altair renders charts via its anywidget ESM, which calls vegaEmbed() and
// stores the resulting View in a closure — it's never exposed on the DOM or
// any accessible object. vega-embed v7 also doesn't set __vega_embed__ on
// the element. The only code with access to the View is vega-embed's own
// action handlers, so we delegate to them.
function findVegaAction(container, extension) {
  return container.querySelector(
    '.vega-actions a[download$=".' + extension + '"]'
  );
}

// Helper: find a widget container by its base ID.
// Shiny module namespacing may prefix the ID (e.g. "mod-querychat_viz_abc"),
// so we match elements whose ID ends with the base widget ID.
function findWidgetContainer(widgetId) {
  return document.getElementById(widgetId)
    || document.querySelector('[id$="' + CSS.escape(widgetId) + '"]');
}

// Helper: trigger a vega-embed export action link.
// vega-embed attaches an async mousedown handler that calls
// view.toImageURL() and sets the link's href to a data URL.
// We dispatch mousedown, then use a MutationObserver to detect
// when href changes from "#" to a data URL, and click the link.
function triggerVegaAction(link, filename) {
  link.download = filename;

  // If href is already a data URL (unlikely but possible), click immediately.
  if (link.href && link.href !== "#" && !link.href.endsWith("#")) {
    link.click();
    return;
  }

  var observer = new MutationObserver(function () {
    if (link.href && link.href !== "#" && !link.href.endsWith("#")) {
      observer.disconnect();
      clearTimeout(timeout);
      link.click();
    }
  });

  observer.observe(link, { attributes: true, attributeFilter: ["href"] });

  var timeout = setTimeout(function () {
    observer.disconnect();
    console.error("Timed out waiting for vega-embed to generate image");
  }, 5000);

  link.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
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

function handleSaveExport(event, btn, extension) {
  event.stopPropagation();
  var widgetId = btn.dataset.widgetId;
  var title = btn.dataset.title || "chart";
  var menu = btn.closest(".querychat-save-menu");
  if (menu) menu.classList.remove("querychat-save-menu--visible");

  var container = findWidgetContainer(widgetId);
  if (!container) return;
  var link = findVegaAction(container, extension);
  if (!link) return;
  triggerVegaAction(link, title + "." + extension);
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
