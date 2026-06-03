// Browser runtime for the artifact feature: the Create Artifact modal
// (gallery selection, format/language pills, freeform input, Generate) and the
// side panel (revise drawer, streaming source editor, version nav, download,
// backdrop dismiss). All DOM and Shiny wiring is registered by
// `installArtifact`; the entry point (`artifact.ts`) calls it once Shiny is
// available.

// Minimal surface of the global `Shiny` object that this module relies on.
interface ShinyApi {
  setInputValue(
    id: string,
    value: unknown,
    opts?: { priority?: string },
  ): void;
  addCustomMessageHandler(name: string, handler: (msg: any) => void): void;
}

function updateGenerateButton(): void {
  const modal = document.querySelector(".modal");
  if (!modal) return;
  const generateBtn = modal.querySelector(
    "[id$='artifact_generate']",
  ) as HTMLButtonElement | null;
  if (!generateBtn) return;

  const gallery = modal.querySelector(".querychat-artifact-gallery");
  if (gallery && gallery.classList.contains("loading")) {
    generateBtn.disabled = true;
    return;
  }

  const selectedCount = modal.querySelectorAll(
    ".querychat-artifact-gallery-item.selected",
  ).length;

  // If "Other" is active, also require freeform format name
  const activePill = modal.querySelector(
    ".querychat-artifact-type-pill.active",
  ) as HTMLElement | null;
  const isOther = activePill?.getAttribute("data-artifact-type") === "other";
  const freeformInput = modal.querySelector(
    ".querychat-artifact-freeform-input input",
  ) as HTMLInputElement | null;
  const hasFreeformText =
    !isOther || (freeformInput?.value.trim().length ?? 0) > 0;

  generateBtn.disabled = selectedCount === 0 || !hasFreeformText;
}

function updateLanguagePills(activeFormatPill: HTMLElement | null): void {
  const langsAttr =
    activeFormatPill?.getAttribute("data-languages") ?? "python,r";
  const supported = new Set(
    langsAttr
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
  const selector = document.querySelector(
    ".querychat-artifact-language-selector",
  );
  if (!selector) return;

  let resetNeeded = false;
  selector
    .querySelectorAll(".querychat-artifact-language-pill")
    .forEach((p) => {
      const lang = p.getAttribute("data-language") ?? "";
      const ok = lang === "" || supported.has(lang);
      p.classList.toggle("disabled", !ok);
      (p as HTMLButtonElement).disabled = !ok;
      if (!ok && p.classList.contains("active")) {
        p.classList.remove("active");
        resetNeeded = true;
      }
    });

  if (resetNeeded) {
    const noPref = selector.querySelector(
      '.querychat-artifact-language-pill[data-language=""]',
    ) as HTMLElement | null;
    if (noPref) {
      noPref.classList.add("active");
    }
  }
}

function handleDocumentClick(event: MouseEvent, shiny: ShinyApi): void {
  const target = event.target as HTMLElement;

  // 0. Generate button — gather modal state into one payload and submit
  const genBtn = target.closest(
    "[id$='artifact_generate']",
  ) as HTMLButtonElement | null;
  if (genBtn) {
    if (genBtn.disabled) return;
    const modal = document.querySelector(".modal");
    if (!modal) return;
    const selected_ids = Array.from(
      modal.querySelectorAll(".querychat-artifact-gallery-item.selected"),
    )
      .map((el) => (el as HTMLElement).dataset.itemId)
      .filter((id): id is string => Boolean(id));
    const activeType = modal.querySelector(
      ".querychat-artifact-type-pill.active",
    ) as HTMLElement | null;
    const type = activeType?.getAttribute("data-artifact-type") ?? "";
    const activeLang = modal.querySelector(
      ".querychat-artifact-language-pill.active",
    ) as HTMLElement | null;
    const language = activeLang?.getAttribute("data-language") ?? "";
    const freeformInput = modal.querySelector(
      ".querychat-artifact-freeform-input input",
    ) as HTMLInputElement | null;
    const freeform = freeformInput?.value.trim() ?? "";
    shiny.setInputValue(
      genBtn.id,
      { selected_ids, type, language, freeform },
      { priority: "event" },
    );
    return;
  }

  // 1. Revise toggle (in panel header) — opens/closes the revise drawer
  const reviseToggle = target.closest(
    ".querychat-artifact-revise-toggle",
  ) as HTMLElement | null;
  if (reviseToggle) {
    const drawer = document.querySelector(".querychat-artifact-revise-drawer");
    if (drawer) {
      const isOpen = drawer.classList.toggle("open");
      reviseToggle.classList.toggle("active", isOpen);
      if (isOpen) {
        const textarea = drawer.querySelector(
          "textarea",
        ) as HTMLTextAreaElement | null;
        if (textarea) textarea.focus();
      }
    }
    return;
  }

  // 2. Artifact pill (in chat) — opens the artifact panel
  const pill = target.closest(
    ".querychat-artifact-pill",
  ) as HTMLElement | null;
  if (pill) {
    const inputId = pill.getAttribute("data-input-id");
    const artifactId = pill.getAttribute("data-artifact-id");
    if (inputId && artifactId) {
      shiny.setInputValue(inputId, artifactId, { priority: "event" });
    }
    return;
  }

  // 3. Type selector pill (in modal) — toggles active type
  const typePill = target.closest(
    ".querychat-artifact-type-pill",
  ) as HTMLElement | null;
  if (typePill) {
    const selector = typePill.parentElement;
    if (selector) {
      selector
        .querySelectorAll(".querychat-artifact-type-pill")
        .forEach((p) => {
          p.classList.remove("active");
        });
      typePill.classList.add("active");

      const typeId = typePill.getAttribute("data-artifact-type");

      // Show/hide freeform input based on whether "Other" is selected
      const freeformWrapper = document.querySelector(
        ".querychat-artifact-freeform-input",
      );
      if (freeformWrapper) {
        if (typeId === "other") {
          freeformWrapper.classList.remove("hidden");
          const textInput = freeformWrapper.querySelector(
            "input",
          ) as HTMLInputElement | null;
          if (textInput) textInput.focus();
        } else {
          freeformWrapper.classList.add("hidden");
        }
      }
    }
    updateLanguagePills(typePill);
    updateGenerateButton();
    return;
  }

  // 4. Language selector pill (in modal) — toggles active language
  const langPill = target.closest(
    ".querychat-artifact-language-pill",
  ) as HTMLElement | null;
  if (langPill) {
    if ((langPill as HTMLButtonElement).disabled) return;
    const selector = langPill.parentElement;
    if (selector) {
      selector
        .querySelectorAll(".querychat-artifact-language-pill")
        .forEach((p) => p.classList.remove("active"));
      langPill.classList.add("active");
    }
    return;
  }

  // 5. Gallery item (in modal) — toggles selection + checkbox
  const item = target.closest(
    ".querychat-artifact-gallery-item",
  ) as HTMLElement | null;
  if (item) {
    item.classList.toggle("selected");
    updateGenerateButton();
    return;
  }
}

function handleDocumentInput(event: Event): void {
  const target = event.target as HTMLElement;
  const freeformWrapper = target.closest(".querychat-artifact-freeform-input");
  if (freeformWrapper) {
    updateGenerateButton();
  }
}

// Backdrop click — dismiss the artifact panel by proxying to the close button.
function handleBackdropClick(event: MouseEvent): void {
  const target = event.target as HTMLElement;
  if (!target.classList.contains("querychat-artifact-backdrop")) return;

  const closeBtn = document.querySelector(
    ".querychat-artifact-panel-header [id$='artifact_close']",
  ) as HTMLButtonElement | null;
  if (closeBtn) closeBtn.click();
}

// Recommend complete — update gallery selection, fill directions, set format,
// remove loading.
function handleRecommend(
  msg: {
    selected_ids: string[];
    format_id: string;
    directions: string;
    directions_id: string;
  },
  shiny: ShinyApi,
): void {
  const selectedIds = new Set(msg.selected_ids);

  // Remove loading state from gallery
  const gallery = document.querySelector(".querychat-artifact-gallery");
  if (gallery) {
    gallery.classList.remove("loading");
  }

  // Update card selection and checkboxes
  document
    .querySelectorAll(".querychat-artifact-gallery-item")
    .forEach((el) => {
      const itemId = (el as HTMLElement).dataset.itemId;
      if (itemId && selectedIds.has(itemId)) {
        el.classList.add("selected");
      } else {
        el.classList.remove("selected");
      }
    });

  // Activate the LLM-chosen format pill
  if (msg.format_id) {
    const selector = document.querySelector(
      ".querychat-artifact-type-selector",
    );
    if (selector) {
      const targetPill = selector.querySelector(
        `[data-artifact-type="${msg.format_id}"]`,
      );
      if (targetPill) {
        selector
          .querySelectorAll(".querychat-artifact-type-pill")
          .forEach((p) => {
            p.classList.remove("active");
          });
        targetPill.classList.add("active");
        updateLanguagePills(targetPill as HTMLElement);
      }
    }
  }

  // Fill directions textarea and remove loading state
  const directionsWrapper = document.querySelector(
    ".querychat-artifact-directions-wrapper",
  );
  if (directionsWrapper) {
    directionsWrapper.classList.remove("loading");
  }

  const directionsEl = document.getElementById(
    msg.directions_id,
  ) as HTMLTextAreaElement | null;
  if (directionsEl) {
    directionsEl.disabled = false;
    if (msg.directions) {
      directionsEl.value = msg.directions;
      directionsEl.dispatchEvent(new Event("input", { bubbles: true }));
      shiny.setInputValue(msg.directions_id, msg.directions);
    }
  }

  // Show the "Pre-filled by AI" subtitle
  const subtitle = document.querySelector(
    ".querychat-artifact-directions-subtitle",
  );
  if (subtitle) {
    subtitle.classList.remove("hidden");
  }

  // Hide loading status
  const status = document.querySelector(".querychat-artifact-loading-status");
  if (status) {
    status.classList.add("hidden");
  }

  updateGenerateButton();
}

// Recommend error — remove loading, leave everything unchecked, and surface
// the failure inline where the user is working so they know auto-suggest
// didn't run (the modal stays usable for manual selection).
function handleRecommendError(msg: { error: string }): void {
  const gallery = document.querySelector(".querychat-artifact-gallery");
  if (gallery) {
    gallery.classList.remove("loading");
  }

  const directionsWrapper = document.querySelector(
    ".querychat-artifact-directions-wrapper",
  );
  if (directionsWrapper) {
    directionsWrapper.classList.remove("loading");
  }

  const directionsEl = document.querySelector(
    ".querychat-artifact-directions-wrapper textarea",
  ) as HTMLTextAreaElement | null;
  if (directionsEl) {
    directionsEl.disabled = false;
  }

  const status = document.querySelector(".querychat-artifact-loading-status");
  if (status) {
    status.classList.remove("hidden");
    status.classList.add("error");
    status.textContent = msg.error
      ? `Couldn't auto-suggest results: ${msg.error}. Select and configure manually.`
      : "Couldn't auto-suggest results. Select and configure manually.";
  }

  updateGenerateButton();
}

// Stream source into the code editor, bypassing Shiny's flush queue.
// The <bslib-code-editor> custom element exposes `value` and `language`
// setters that update the underlying prism-code-editor instance.
function handleSourceUpdate(msg: {
  id: string;
  value: string;
  language?: string;
}): void {
  const el = document.getElementById(msg.id) as any;
  if (el) {
    if (msg.language) {
      el.language = msg.language;
    }
    el.value = msg.value;
  }
}

function getPanel(): Element | null {
  return document.querySelector(".querychat-artifact-panel");
}

// Streaming indicator — toggle the header spinner while source streams in.
function handleStreaming(msg: { active: boolean }): void {
  const panel = getPanel();
  if (panel) panel.classList.toggle("streaming", msg.active);
}

// Version state — toggle the nav (only shown with 2+ versions), update the
// stepper label and prev/next disabled state.
function handleVersionUpdate(msg: {
  label: string;
  total: number;
  prev_disabled: boolean;
  next_disabled: boolean;
}): void {
  const panel = getPanel();
  if (!panel) return;

  const nav = panel.querySelector(".querychat-artifact-version-nav");
  if (nav) nav.classList.toggle("show", msg.total > 1);

  const labelEl = panel.querySelector(".querychat-artifact-version-label");
  if (labelEl) labelEl.textContent = msg.label;

  const prevBtn = panel.querySelector(
    "[id$='artifact_version_prev']",
  ) as HTMLButtonElement | null;
  const nextBtn = panel.querySelector(
    "[id$='artifact_version_next']",
  ) as HTMLButtonElement | null;
  if (prevBtn) prevBtn.disabled = msg.prev_disabled;
  if (nextBtn) nextBtn.disabled = msg.next_disabled;
}

// Panel toggle message handler — adds/removes .open class on panel + backdrop
function handlePanelToggle(msg: { open: boolean }): void {
  const panel = getPanel();
  const backdrop = document.querySelector(".querychat-artifact-backdrop");
  if (panel) panel.classList.toggle("open", msg.open);
  if (backdrop) backdrop.classList.toggle("open", msg.open);

  if (!msg.open) {
    const drawer = document.querySelector(".querychat-artifact-revise-drawer");
    const toggle = document.querySelector(".querychat-artifact-revise-toggle");
    if (drawer) drawer.classList.remove("open");
    if (toggle) toggle.classList.remove("active");
  }
}

export function installArtifact(shiny: ShinyApi): void {
  document.addEventListener("click", (event) =>
    handleDocumentClick(event, shiny),
  );

  // Re-evaluate Generate button when freeform format name changes
  document.addEventListener("input", handleDocumentInput);

  document.addEventListener("click", handleBackdropClick);

  shiny.addCustomMessageHandler("querychat-artifact-recommend", (msg) =>
    handleRecommend(msg, shiny),
  );
  shiny.addCustomMessageHandler(
    "querychat-artifact-recommend-error",
    handleRecommendError,
  );
  shiny.addCustomMessageHandler(
    "querychat-artifact-source-update",
    handleSourceUpdate,
  );
  shiny.addCustomMessageHandler(
    "querychat-artifact-streaming",
    handleStreaming,
  );
  shiny.addCustomMessageHandler(
    "querychat-artifact-version-update",
    handleVersionUpdate,
  );
  shiny.addCustomMessageHandler(
    "querychat-artifact-panel-toggle",
    handlePanelToggle,
  );
}
