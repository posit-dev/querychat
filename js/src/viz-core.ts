type ExportFormat = "png" | "svg";

export interface VizRuntimeAdapter {
  exportPlot(widgetId: string, format: ExportFormat, filename: string): void;
}

function findWidgetContainer(widgetId: string): HTMLElement | null {
  return document.getElementById(widgetId);
}

function findVegaAction(
  container: HTMLElement,
  format: ExportFormat,
): HTMLAnchorElement | null {
  return container.querySelector<HTMLAnchorElement>(
    `.vega-actions a[download$=".${format}"]`,
  );
}

function triggerVegaAction(link: HTMLAnchorElement, filename: string): void {
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
    attributeFilter: ["href"],
  });

  const timeoutId = window.setTimeout(() => {
    observer.disconnect();
    console.error("Timed out waiting for vega-embed to generate image");
  }, 5000);

  link.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
}

function closeAllSaveMenus(): void {
  document
    .querySelectorAll<HTMLElement>(".querychat-save-menu--visible")
    .forEach((menu) => {
      menu.classList.remove("querychat-save-menu--visible");
    });
}

function handleShowQuery(event: MouseEvent, button: HTMLElement): void {
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
  const label = button.querySelector<HTMLElement>(".querychat-query-label");
  const chevron = button.querySelector<HTMLElement>(".querychat-query-chevron");

  if (label) {
    label.textContent = isVisible ? "Hide Query" : "Show Query";
  }

  if (chevron) {
    chevron.classList.toggle("querychat-query-chevron--expanded", isVisible);
  }
}

function handleSaveToggle(event: MouseEvent, button: HTMLElement): void {
  event.stopPropagation();

  const menu = button.parentElement?.querySelector<HTMLElement>(
    ".querychat-save-menu",
  );

  if (menu) {
    menu.classList.toggle("querychat-save-menu--visible");
  }
}

function handleSaveExport(
  event: MouseEvent,
  button: HTMLElement,
  format: ExportFormat,
  adapter: VizRuntimeAdapter,
): void {
  event.stopPropagation();

  const widgetId = button.dataset.widgetId;
  if (!widgetId) {
    return;
  }

  const filename = button.dataset.title || "chart";
  const menu = button.closest<HTMLElement>(".querychat-save-menu");
  if (menu) {
    menu.classList.remove("querychat-save-menu--visible");
  }

  adapter.exportPlot(widgetId, format, filename);
}

function handleCopy(event: MouseEvent, button: HTMLElement): void {
  event.stopPropagation();

  const query = button.dataset.query;
  if (!query) {
    return;
  }

  navigator.clipboard
    .writeText(query)
    .then(() => {
      const original = button.textContent;
      button.textContent = "Copied!";
      setTimeout(() => {
        button.textContent = original;
      }, 2000);
    })
    .catch((error: unknown) => {
      console.error("Failed to copy:", error);
    });
}

export function installVizFooter(adapter: VizRuntimeAdapter): void {
  window.addEventListener("click", (event) => {
    const target = event.target;

    if (!(target instanceof Element)) {
      closeAllSaveMenus();
      return;
    }

    const showQueryButton = target.closest<HTMLElement>(".querychat-show-query-btn");
    if (showQueryButton) {
      handleShowQuery(event, showQueryButton);
      return;
    }

    const savePngButton = target.closest<HTMLElement>(".querychat-save-png-btn");
    if (savePngButton) {
      handleSaveExport(event, savePngButton, "png", adapter);
      return;
    }

    const saveSvgButton = target.closest<HTMLElement>(".querychat-save-svg-btn");
    if (saveSvgButton) {
      handleSaveExport(event, saveSvgButton, "svg", adapter);
      return;
    }

    const copyButton = target.closest<HTMLElement>(".querychat-copy-btn");
    if (copyButton) {
      handleCopy(event, copyButton);
      return;
    }

    const saveButton = target.closest<HTMLElement>(".querychat-save-btn");
    if (saveButton) {
      handleSaveToggle(event, saveButton);
      return;
    }

    closeAllSaveMenus();
  });
}

export function createVegaActionAdapter(): VizRuntimeAdapter {
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
    },
  };
}
