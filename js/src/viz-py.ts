import { installVizFooter } from "./viz-core";

type VegaActionLink = HTMLAnchorElement;

function findVegaAction(
  container: HTMLElement,
  extension: "png" | "svg",
): VegaActionLink | null {
  return container.querySelector<VegaActionLink>(
    `.vega-actions a[download$=".${extension}"]`,
  );
}

function findWidgetContainer(widgetId: string): HTMLElement | null {
  return (
    document.getElementById(widgetId) ||
    document.querySelector<HTMLElement>(`[id$="${CSS.escape(widgetId)}"]`)
  );
}

function triggerVegaAction(link: VegaActionLink, filename: string): void {
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

installVizFooter({
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
});
