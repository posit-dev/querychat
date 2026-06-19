/* Generated file. Source: js/src/schema-display.js. Do not edit directly. */

"use strict";
(() => {
  // src/schema-display.js
  var lastDisplay = null;
  var lastDisplayTime = 0;
  var BATCH_MS = 1e3;
  var activePanel = null;
  function parseSchema(text) {
    const columns = [];
    let current = null;
    for (const line of text.split("\n")) {
      if (line.startsWith("- ")) {
        const match = line.slice(2).match(/^(\S+)\s+\(([^)]+)\)(?:\s+\[([^\]]+)\])?/);
        if (match) {
          current = {
            name: match[1],
            type: match[2],
            units: match[3] || null,
            description: null,
            constraints: null,
            range: null,
            categories: null
          };
          columns.push(current);
        }
      } else if (current) {
        const trimmed = line.trim();
        if (trimmed.startsWith("Description: ")) {
          current.description = trimmed.slice(13);
        } else if (trimmed.startsWith("Constraints: ")) {
          current.constraints = trimmed.slice(13);
        } else if (trimmed.startsWith("Range: ")) {
          current.range = trimmed.slice(7);
        } else if (trimmed.startsWith("Categorical values: ")) {
          current.categories = trimmed.slice(20);
        }
      }
    }
    return columns;
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  var TH = "padding:0.35em 0.75em;text-align:left;white-space:nowrap;font-weight:600;border-bottom:2px solid var(--bs-border-color,#dee2e6);background:var(--bs-tertiary-bg,#f8f9fa);position:sticky;top:0;z-index:1;";
  var TD_MONO = "padding:0.3em 0.75em;white-space:nowrap;font-family:var(--bs-font-monospace,monospace);font-size:0.875em;border-bottom:1px solid var(--bs-border-color-translucent,rgba(0,0,0,.08));";
  var TD_WRAP = "padding:0.3em 0.75em;max-width:22em;overflow-wrap:break-word;border-bottom:1px solid var(--bs-border-color-translucent,rgba(0,0,0,.08));";
  var TD_NOWRAP = "padding:0.3em 0.75em;white-space:nowrap;border-bottom:1px solid var(--bs-border-color-translucent,rgba(0,0,0,.08));";
  function renderTable(columns) {
    const rows = columns.map((col) => {
      let typeCell = esc(col.type);
      if (col.units) {
        typeCell += ` <span style="color:var(--bs-secondary-color,#6c757d)">[${esc(col.units)}]</span>`;
      }
      const details = col.range ? esc(col.range) : col.categories ? esc(col.categories) : "";
      return `<tr><td style="${TD_MONO}">${esc(col.name)}</td><td style="${TD_MONO}">${typeCell}</td><td style="${TD_WRAP}">${col.description ? esc(col.description) : ""}</td><td style="${TD_NOWRAP}">${col.constraints ? esc(col.constraints) : ""}</td><td style="${TD_WRAP}">${details}</td></tr>`;
    }).join("");
    return `<table style="border-collapse:collapse;min-width:100%;width:max-content;font-size:0.875em;"><thead><tr><th style="${TH}">Column</th><th style="${TH}">Type</th><th style="${TH}">Description</th><th style="${TH}">Constraints</th><th style="${TH}">Range / Values</th></tr></thead><tbody>${rows}</tbody></table>`;
  }
  var PANEL_STYLE = "position:fixed;z-index:9999;background:var(--bs-body-bg,#fff);color:var(--bs-body-color,#212529);border:1px solid var(--bs-border-color,#dee2e6);border-radius:var(--bs-border-radius,0.375rem);box-shadow:0 4px 16px rgba(0,0,0,.15);overflow:auto;max-height:min(420px,60vh);";
  function positionPanel(btn, panel) {
    const rect = btn.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const pw = Math.min(Math.max(360, vw * 0.55), vw - 16);
    panel.style.width = `${pw}px`;
    panel.style.left = `${Math.max(8, Math.min(rect.left, vw - pw - 8))}px`;
    const spaceBelow = vh - rect.bottom - 8;
    const spaceAbove = rect.top - 8;
    if (spaceBelow >= 120 || spaceBelow >= spaceAbove) {
      panel.style.top = `${rect.bottom + 4}px`;
    } else {
      const panelH = Math.min(420, spaceAbove);
      panel.style.top = `${Math.max(8, rect.top - panelH - 4)}px`;
    }
  }
  function closePanel() {
    if (activePanel) {
      activePanel.panel.hidden = true;
      activePanel.btn.setAttribute("aria-expanded", "false");
      activePanel = null;
    }
  }
  document.addEventListener("click", closePanel);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePanel();
  });
  window.addEventListener(
    "scroll",
    (e) => {
      if (activePanel && !activePanel.panel.contains(
        /** @type {Node} */
        e.target
      )) {
        closePanel();
      }
    },
    true
  );
  window.addEventListener("resize", closePanel);
  function createBtn(tableName, schemaText) {
    const columns = parseSchema(schemaText);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.style.cssText = "background:none;border:none;padding:0;color:inherit;text-decoration:underline dotted;cursor:pointer;font-size:inherit;border-radius:2px;";
    btn.textContent = tableName;
    btn.setAttribute("aria-label", `Show schema for ${tableName}`);
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-haspopup", "dialog");
    const panel = document.createElement("div");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", `${tableName} schema`);
    panel.style.cssText = PANEL_STYLE;
    panel.hidden = true;
    panel.innerHTML = renderTable(columns);
    document.body.appendChild(panel);
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (activePanel && activePanel.panel === panel) {
        closePanel();
        return;
      }
      closePanel();
      positionPanel(btn, panel);
      panel.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      activePanel = { btn, panel };
    });
    panel.addEventListener("click", (e) => e.stopPropagation());
    return btn;
  }
  var style = document.createElement("style");
  style.textContent = ".qc-schema-display button:focus-visible{outline:2px solid currentColor;outline-offset:2px;border-radius:2px}";
  document.head.appendChild(style);
  function processCollector(sentinel) {
    const now = Date.now();
    const tableName = sentinel.dataset.table;
    const schemaText = sentinel.dataset.schema;
    const btn = createBtn(tableName, schemaText);
    if (lastDisplay && document.contains(lastDisplay) && now - lastDisplayTime < BATCH_MS) {
      lastDisplay.appendChild(document.createTextNode(", "));
      lastDisplay.appendChild(btn);
      sentinel.remove();
    } else {
      const p = document.createElement("p");
      p.className = "qc-schema-display";
      p.style.cssText = "color:var(--bs-secondary-color,#6c757d);font-size:0.875em;margin:0.1rem 0;";
      p.appendChild(document.createTextNode("\u{1F50D} Fetched schemas: "));
      p.appendChild(btn);
      sentinel.replaceWith(p);
      lastDisplay = p;
    }
    lastDisplayTime = now;
  }
  new MutationObserver((mutations) => {
    for (const { addedNodes } of mutations) {
      for (const node of addedNodes) {
        if (node.nodeType !== 1) continue;
        if (
          /** @type {Element} */
          node.classList.contains("qc-schema-collector")
        ) {
          processCollector(
            /** @type {HTMLElement} */
            node
          );
        } else {
          node.querySelectorAll(".qc-schema-collector").forEach((el) => processCollector(
            /** @type {HTMLElement} */
            el
          ));
        }
      }
    }
  }).observe(document.body, { subtree: true, childList: true });
})();
