(function () {
  if (typeof bootstrap === "undefined") return;

  // Inject focus ring for keyboard users (Bootstrap resets outline on buttons)
  var style = document.createElement("style");
  style.textContent =
    ".qc-schema-display button:focus-visible{" +
    "outline:2px solid currentColor;outline-offset:2px;border-radius:2px}";
  document.head.appendChild(style);

  var lastDisplay = null;
  var lastDisplayTime = 0;
  var BATCH_MS = 1000;

  function escHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function createBtn(tableName, schemaText) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.style.cssText =
      "background:none;border:none;padding:0;color:inherit;" +
      "text-decoration:underline dotted;cursor:help;font-size:inherit;";
    btn.setAttribute("data-bs-toggle", "popover");
    btn.setAttribute("data-bs-title", tableName);
    btn.setAttribute(
      "data-bs-content",
      "<pre style=\"font-size:0.75em;margin:0;white-space:pre-wrap\">" +
        escHtml(schemaText) +
        "</pre>"
    );
    btn.setAttribute("data-bs-trigger", "hover focus");
    btn.setAttribute("data-bs-placement", "top");
    btn.setAttribute("data-bs-html", "true");
    btn.textContent = tableName;
    btn.setAttribute("aria-label", "Schema for " + tableName);
    new bootstrap.Popover(btn, { html: true });
    return btn;
  }

  function processCollector(sentinel) {
    var now = Date.now();
    var tableName = sentinel.dataset.table;
    var schemaText = sentinel.dataset.schema;
    var btn = createBtn(tableName, schemaText);

    if (
      lastDisplay &&
      document.contains(lastDisplay) &&
      now - lastDisplayTime < BATCH_MS
    ) {
      lastDisplay.appendChild(document.createTextNode(", "));
      lastDisplay.appendChild(btn);
      sentinel.remove();
    } else {
      var p = document.createElement("p");
      p.className = "qc-schema-display";
      p.style.cssText =
        "color:var(--bs-secondary-color,#6c757d);font-size:0.875em;margin:0.1rem 0;";
      p.appendChild(document.createTextNode("🔍 Fetched schemas: "));
      p.appendChild(btn);
      sentinel.replaceWith(p);
      lastDisplay = p;
    }
    lastDisplayTime = now;
  }

  new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var added = mutations[i].addedNodes;
      for (var j = 0; j < added.length; j++) {
        var node = added[j];
        if (node.nodeType !== 1) continue;
        if (node.classList.contains("qc-schema-collector")) {
          processCollector(node);
        } else {
          node
            .querySelectorAll(".qc-schema-collector")
            .forEach(processCollector);
        }
      }
    }
  }).observe(document.body, { subtree: true, childList: true });
})();
