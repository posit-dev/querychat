// Browser runtime for the dashboard drawer: grid canvas (gridstack), palette,
// undo/redo history controls, and badge toggle. All DOM and Shiny wiring is
// registered by `initDashboard`; the entry point (`dashboard.ts`) calls it
// once Shiny is available.

import { GridStack, type GridItemHTMLElement, type GridStackNode } from "gridstack";

// gridstack v11 changed content rendering: the default renderCB sets
// el.textContent = w.content (text-only, XSS-safe default). Our content comes
// from our own server, so injecting HTML is intentional.  Set renderCB once at
// module load so every addWidget call uses innerHTML.
GridStack.renderCB = (el: HTMLElement, w: { content?: string }) => {
  el.innerHTML = w.content ?? "";
};

// Minimal surface of the global `Shiny` object this module relies on.
interface ShinyApi {
  addCustomMessageHandler(type: string, handler: (msg: any) => void): void;
  setInputValue?(id: string, value: unknown, opts?: { priority?: string }): void;
  initializeInputs?(el: HTMLElement): void;
  bindAll?(el: HTMLElement): Promise<void> | void;
  unbindAll?(el: HTMLElement): void;
}

const PREFIX = "querychat-dashboard-";

interface Layout {
  x: number;
  y: number;
  w: number;
  h: number;
}

let grid: GridStack | null = null;
let suppressChange = false;

function qs(sel: string): HTMLElement | null {
  return document.querySelector(sel);
}

function inputIds(): Record<string, string> {
  const drawer = qs(".querychat-dash-drawer");
  if (!drawer) return {};
  try {
    return JSON.parse(drawer.getAttribute("data-qcdash-inputs") || "{}") as Record<
      string,
      string
    >;
  } catch {
    return {};
  }
}

function setInput(shiny: ShinyApi, name: string, value: unknown): void {
  const id = inputIds()[name];
  if (id && shiny.setInputValue) {
    shiny.setInputValue(id, value, { priority: "event" });
  }
}

function ensureGrid(shiny: ShinyApi): GridStack {
  if (grid) return grid;
  const el = qs(".querychat-dash-canvas");
  if (!el) throw new Error("querychat dashboard canvas missing");
  grid = GridStack.init(
    { column: 12, cellHeight: 90, margin: 6, float: false, animate: true },
    el,
  );
  grid.on("change", (_ev: Event, nodes: GridStackNode[]) => {
    if (suppressChange || !nodes?.length) return;
    const placements = nodes
      .filter((n) => n.el?.getAttribute("data-card-name"))
      .map((n) => ({
        name: n.el!.getAttribute("data-card-name")!,
        x: n.x ?? 0,
        y: n.y ?? 0,
        w: n.w ?? 1,
        h: n.h ?? 1,
      }));
    if (placements.length) setInput(shiny, "dashboard_layout_change", placements);
  });
  return grid;
}

async function bindInto(shiny: ShinyApi, el: HTMLElement): Promise<void> {
  shiny.initializeInputs?.(el);
  await shiny.bindAll?.(el);
}

function cardItem(name: string): GridItemHTMLElement | null {
  return document.querySelector<GridItemHTMLElement>(
    `.grid-stack-item[data-card-name="${name}"]`,
  );
}

function upsertCard(
  shiny: ShinyApi,
  msg: { name: string; html: string; layout: Layout },
): void {
  const g = ensureGrid(shiny);
  suppressChange = true;
  try {
    const existing = cardItem(msg.name);
    if (existing) {
      shiny.unbindAll?.(existing);
      g.removeWidget(existing, true);
    }
    // Content from our server; innerHTML is intentional (see renderCB above).
    const content = `<button class="querychat-dash-card-remove" title="Remove">✕</button>${msg.html}`;
    const el = g.addWidget({
      x: msg.layout.x,
      y: msg.layout.y,
      w: msg.layout.w,
      h: msg.layout.h,
      content,
    });
    el.setAttribute("data-card-name", msg.name);
    el
      .querySelector(".querychat-dash-card-remove")
      ?.addEventListener("click", () =>
        setInput(shiny, "dashboard_remove_card", msg.name),
      );
    void bindInto(shiny, el);
  } finally {
    suppressChange = false;
  }
}

function removeCard(shiny: ShinyApi, msg: { name: string }): void {
  const el = cardItem(msg.name);
  if (el && grid) {
    suppressChange = true;
    shiny.unbindAll?.(el);
    grid.removeWidget(el);
    suppressChange = false;
  }
}

function canvasReset(msg: { title: string }): void {
  if (!grid) return;
  suppressChange = true;
  grid.removeAll();
  suppressChange = false;
  const title = qs(".querychat-dash-title");
  if (title) title.textContent = msg.title;
}

function applyLayout(msg: {
  placements: Array<{ name: string } & Layout>;
}): void {
  if (!grid) return;
  suppressChange = true;
  try {
    for (const p of msg.placements) {
      const el = cardItem(p.name);
      if (el) grid.update(el, { x: p.x, y: p.y, w: p.w, h: p.h });
    }
  } finally {
    suppressChange = false;
  }
}

// Move the live chat element into the drawer's left rail (and back).
// DOM moves preserve Shiny bindings; falls back gracefully if elements are absent.
let chatHome: { parent: HTMLElement; next: Node | null } | null = null;

function reparentChat(intoDrawer: boolean): void {
  const chat = qs(".querychat");
  const slot = qs(".querychat-dash-chat-slot");
  if (!chat || !slot) return;
  if (intoDrawer) {
    chatHome = {
      parent: chat.parentElement as HTMLElement,
      next: chat.nextSibling,
    };
    slot.appendChild(chat);
  } else if (chatHome) {
    chatHome.parent.insertBefore(chat, chatHome.next);
    chatHome = null;
  }
  // Let widgets re-measure after the layout shift.
  window.dispatchEvent(new Event("resize"));
}

function toggleDrawer(shiny: ShinyApi, msg: { open: boolean }): void {
  const drawer = qs(".querychat-dash-drawer");
  if (!drawer) return;
  if (msg.open) {
    drawer.removeAttribute("hidden");
    ensureGrid(shiny);
    reparentChat(true);
  } else {
    // Match the Python side's hidden="" convention.
    drawer.setAttribute("hidden", "");
    reparentChat(false);
  }
}

function updatePalette(shiny: ShinyApi, msg: { html: string }): void {
  const wrap = qs(".querychat-dash-palette-items");
  if (!wrap) return;
  wrap.innerHTML = msg.html;
  wrap
    .querySelectorAll<HTMLElement>(".querychat-dash-palette-item")
    .forEach((item) => {
      item.addEventListener("dblclick", () =>
        setInput(shiny, "dashboard_palette_add", {
          id: item.getAttribute("data-palette-id"),
        }),
      );
      item.addEventListener("dragend", (ev) => {
        const canvas = qs(".querychat-dash-canvas");
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const inside =
          ev.clientX >= rect.left &&
          ev.clientX <= rect.right &&
          ev.clientY >= rect.top &&
          ev.clientY <= rect.bottom;
        if (inside) {
          setInput(shiny, "dashboard_palette_add", {
            id: item.getAttribute("data-palette-id"),
          });
        }
      });
    });
}

function updateBadge(msg: { count: number }): void {
  const badge = qs(".querychat-dash-badge");
  const count = qs(".querychat-dash-badge-count");
  if (!badge || !count) return;
  count.textContent = String(msg.count);
  if (msg.count > 0) {
    badge.removeAttribute("hidden");
  } else {
    badge.setAttribute("hidden", "");
  }
}

function updateHistory(msg: { can_undo: boolean; can_redo: boolean }): void {
  (qs(".querychat-dash-undo") as HTMLButtonElement | null)?.toggleAttribute(
    "disabled",
    !msg.can_undo,
  );
  (qs(".querychat-dash-redo") as HTMLButtonElement | null)?.toggleAttribute(
    "disabled",
    !msg.can_redo,
  );
}

function updateAutogen(msg: { active: boolean }): void {
  qs(".querychat-dash-autogen-spinner")?.toggleAttribute("hidden", !msg.active);
}

function wireStaticControls(shiny: ShinyApi): void {
  qs(".querychat-dash-close")?.addEventListener("click", () =>
    setInput(shiny, "dashboard_close", Date.now()),
  );
  qs(".querychat-dash-undo")?.addEventListener("click", () =>
    setInput(shiny, "dashboard_undo", Date.now()),
  );
  qs(".querychat-dash-redo")?.addEventListener("click", () =>
    setInput(shiny, "dashboard_redo", Date.now()),
  );
  qs(".querychat-dash-badge")?.addEventListener("click", () =>
    setInput(shiny, "dashboard_open", Date.now()),
  );

  // Pin buttons live inside chat tool-result cards (delegated: they stream in).
  document.addEventListener("click", (ev) => {
    const btn = (ev.target as HTMLElement).closest<HTMLElement>(
      '[data-querychat-action="pin-card"]',
    );
    if (!btn) return;
    setInput(shiny, "dashboard_pin", {
      kind: btn.getAttribute("data-kind"),
      title: btn.getAttribute("data-title"),
      source: btn.getAttribute("data-source"),
    });
  });
}

export function initDashboard(): void {
  const shiny = (window as any).Shiny as ShinyApi | undefined;
  if (!shiny) return;

  shiny.addCustomMessageHandler(`${PREFIX}drawer-toggle`, (msg) =>
    toggleDrawer(shiny, msg),
  );
  shiny.addCustomMessageHandler(`${PREFIX}card-upsert`, (msg) =>
    upsertCard(shiny, msg),
  );
  shiny.addCustomMessageHandler(`${PREFIX}card-remove`, (msg) =>
    removeCard(shiny, msg),
  );
  shiny.addCustomMessageHandler(`${PREFIX}canvas-reset`, canvasReset);
  shiny.addCustomMessageHandler(`${PREFIX}layout-apply`, applyLayout);
  shiny.addCustomMessageHandler(`${PREFIX}palette`, (msg) =>
    updatePalette(shiny, msg),
  );
  shiny.addCustomMessageHandler(`${PREFIX}badge`, updateBadge);
  shiny.addCustomMessageHandler(`${PREFIX}history`, updateHistory);
  shiny.addCustomMessageHandler(`${PREFIX}autogen`, updateAutogen);
  wireStaticControls(shiny);
}
