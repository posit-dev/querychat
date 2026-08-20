// Browser runtime for the artifact feature: the Create Artifact modal
// (gallery selection, format/language pills, freeform input, Generate) and the
// side panel (revise drawer, streaming source editor, download, backdrop
// dismiss). All DOM and Shiny wiring is registered by
// `installArtifact`; the entry point (`artifact.ts`) calls it once Shiny is
// available.

// Minimal surface of the global `Shiny` object that this module relies on.
interface ShinyApi {
  setInputValue(
    id: string,
    value: unknown,
    opts?: { priority?: string },
  ): void;
  addCustomMessageHandler<T>(name: string, handler: (msg: T) => void): void;
}

const artifactMessageActions = [
  "recommend",
  "recommend-error",
  "source-update",
  "streaming",
  "panel-toggle",
] as const;

type ArtifactMessageAction = (typeof artifactMessageActions)[number];

type ArtifactMessage = {
  root_id: string;
};

type RecommendationMessage = ArtifactMessage & {
  selected_ids: string[];
  format_id: string;
  directions: string;
  directions_id: string;
};

type RecommendationErrorMessage = ArtifactMessage & {
  error: string;
};

type SourceUpdateMessage = ArtifactMessage & {
  id: string;
  value: string;
  language?: string;
  download_available?: boolean;
};

type StreamingMessage = ArtifactMessage & {
  active: boolean;
};

type PanelToggleMessage = ArtifactMessage & {
  open: boolean;
};

function artifactMessageName(action: ArtifactMessageAction): string {
  return `querychat-artifact-${action}`;
}

function getArtifactRoot(rootId: string): HTMLElement | null {
  return document.getElementById(rootId);
}

function getElementInRoot<T extends HTMLElement>(
  root: HTMLElement,
  id: string,
): T | null {
  const element = document.getElementById(id);
  if (!element || !root.contains(element)) return null;
  return element as T;
}

function updateGenerateButton(modal: HTMLElement): void {
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

function updateLanguagePills(
  modal: HTMLElement,
  activeFormatPill: HTMLElement | null,
): void {
  const langsAttr =
    activeFormatPill?.getAttribute("data-languages") ?? "python,r";
  const supported = new Set(
    langsAttr
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
  const selector = modal.querySelector(
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
    const modal = genBtn.closest(
      ".querychat-artifact-modal",
    ) as HTMLElement | null;
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
    const root = reviseToggle.closest(".querychat-artifact-root");
    const drawer = root?.querySelector(".querychat-artifact-revise-drawer");
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
    const modal = typePill.closest(
      ".querychat-artifact-modal",
    ) as HTMLElement | null;
    if (!modal) return;
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
      const freeformWrapper = modal.querySelector(
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
    updateLanguagePills(modal, typePill);
    updateGenerateButton(modal);
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
    const modal = item.closest(
      ".querychat-artifact-modal",
    ) as HTMLElement | null;
    if (modal) updateGenerateButton(modal);
    return;
  }
}

function handleDocumentInput(event: Event): void {
  const target = event.target as HTMLElement;
  const freeformWrapper = target.closest(".querychat-artifact-freeform-input");
  if (freeformWrapper) {
    const modal = freeformWrapper.closest(
      ".querychat-artifact-modal",
    ) as HTMLElement | null;
    if (modal) updateGenerateButton(modal);
  }
}

// Backdrop click — dismiss the artifact panel by proxying to the close button.
function handleBackdropClick(event: MouseEvent): void {
  const target = event.target as HTMLElement;
  if (!target.classList.contains("querychat-artifact-backdrop")) return;

  const root = target.closest(".querychat-artifact-root");
  const closeBtn = root?.querySelector(
    ".querychat-artifact-panel-header [id$='artifact_close']",
  ) as HTMLButtonElement | null;
  if (closeBtn) closeBtn.click();
}

// Recommend complete — update gallery selection, fill directions, set format,
// remove loading.
function handleRecommend(
  msg: RecommendationMessage,
  shiny: ShinyApi,
): void {
  const modal = getArtifactRoot(msg.root_id);
  if (!modal) return;
  const selectedIds = new Set(msg.selected_ids);

  // Remove loading state from gallery
  const gallery = modal.querySelector(".querychat-artifact-gallery");
  if (gallery) {
    gallery.classList.remove("loading");
  }

  // Update card selection and checkboxes
  modal
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
    const selector = modal.querySelector(
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
        updateLanguagePills(modal, targetPill as HTMLElement);
      }
    }
  }

  // Fill directions textarea and remove loading state
  const directionsWrapper = modal.querySelector(
    ".querychat-artifact-directions-wrapper",
  );
  if (directionsWrapper) {
    directionsWrapper.classList.remove("loading");
  }

  const directionsEl = getElementInRoot<HTMLTextAreaElement>(
    modal,
    msg.directions_id,
  );
  if (directionsEl) {
    directionsEl.disabled = false;
    if (msg.directions) {
      directionsEl.value = msg.directions;
      directionsEl.dispatchEvent(new Event("input", { bubbles: true }));
      shiny.setInputValue(msg.directions_id, msg.directions);
    }
  }

  // Show the "Pre-filled by AI" subtitle
  const subtitle = modal.querySelector(
    ".querychat-artifact-directions-subtitle",
  );
  if (subtitle) {
    subtitle.classList.remove("hidden");
  }

  // Hide loading status
  const status = modal.querySelector(".querychat-artifact-loading-status");
  if (status) {
    status.classList.add("hidden");
  }

  updateGenerateButton(modal);
}

// Recommend error — remove loading, leave everything unchecked, and surface
// the failure inline where the user is working so they know auto-suggest
// didn't run (the modal stays usable for manual selection).
function handleRecommendError(msg: RecommendationErrorMessage): void {
  const modal = getArtifactRoot(msg.root_id);
  if (!modal) return;
  const gallery = modal.querySelector(".querychat-artifact-gallery");
  if (gallery) {
    gallery.classList.remove("loading");
  }

  const directionsWrapper = modal.querySelector(
    ".querychat-artifact-directions-wrapper",
  );
  if (directionsWrapper) {
    directionsWrapper.classList.remove("loading");
  }

  const directionsEl = modal.querySelector(
    ".querychat-artifact-directions-wrapper textarea",
  ) as HTMLTextAreaElement | null;
  if (directionsEl) {
    directionsEl.disabled = false;
  }

  const status = modal.querySelector(".querychat-artifact-loading-status");
  if (status) {
    status.classList.remove("hidden");
    status.classList.add("error");
    status.textContent = msg.error
      ? `Couldn't auto-suggest results: ${msg.error}. Select and configure manually.`
      : "Couldn't auto-suggest results. Select and configure manually.";
  }

  updateGenerateButton(modal);
}

// Stream source into the code editor, bypassing Shiny's flush queue.
// The <bslib-code-editor> custom element exposes `value` and `language`
// setters that update the underlying prism-code-editor instance.
function handleSourceUpdate(msg: SourceUpdateMessage): void {
  const root = getArtifactRoot(msg.root_id);
  if (!root) return;
  const el = getElementInRoot<HTMLElement>(root, msg.id) as any;
  if (el) {
    if (msg.language) {
      el.language = msg.language;
    }
    el.value = msg.value;
  }
  if (msg.download_available !== undefined) {
    const downloadBtn = root.querySelector(
      "[id$='artifact_download']",
    ) as HTMLAnchorElement | null;
    if (downloadBtn) {
      downloadBtn.classList.toggle("disabled", !msg.download_available);
      downloadBtn.setAttribute("aria-disabled", String(!msg.download_available));
      downloadBtn.tabIndex = msg.download_available ? 0 : -1;
      downloadBtn.title = msg.download_available
        ? "Download"
        : "Download unavailable: data snapshot is no longer available";
    }
  }
}

function getPanel(root: HTMLElement): Element | null {
  return root.querySelector(".querychat-artifact-panel");
}

// Streaming indicator — toggle the header spinner while source streams in.
function handleStreaming(msg: StreamingMessage): void {
  const root = getArtifactRoot(msg.root_id);
  if (!root) return;
  const panel = getPanel(root);
  if (panel) panel.classList.toggle("streaming", msg.active);
}

// Panel toggle message handler — adds/removes .open class on panel + backdrop
function handlePanelToggle(msg: PanelToggleMessage): void {
  const root = getArtifactRoot(msg.root_id);
  if (!root) return;
  const panel = getPanel(root);
  const backdrop = root.querySelector(".querychat-artifact-backdrop");
  if (panel) panel.classList.toggle("open", msg.open);
  if (backdrop) backdrop.classList.toggle("open", msg.open);

  if (!msg.open) {
    const drawer = root.querySelector(".querychat-artifact-revise-drawer");
    const toggle = root.querySelector(".querychat-artifact-revise-toggle");
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

  shiny.addCustomMessageHandler<RecommendationMessage>(
    artifactMessageName("recommend"),
    (msg) => handleRecommend(msg, shiny),
  );
  shiny.addCustomMessageHandler<RecommendationErrorMessage>(
    artifactMessageName("recommend-error"),
    handleRecommendError,
  );
  shiny.addCustomMessageHandler<SourceUpdateMessage>(
    artifactMessageName("source-update"),
    handleSourceUpdate,
  );
  shiny.addCustomMessageHandler<StreamingMessage>(
    artifactMessageName("streaming"),
    handleStreaming,
  );
  shiny.addCustomMessageHandler<PanelToggleMessage>(
    artifactMessageName("panel-toggle"),
    handlePanelToggle,
  );
}
