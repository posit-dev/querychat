import { installVizFooter } from "./viz-core";

type ExportFormat = "png" | "svg";

type VegaView = {
  toImageURL(type: "png"): Promise<string>;
  toSVG(): Promise<string>;
};

type GgsqlVizElement = HTMLElement & {
  _view?: VegaView;
};

function findGgsqlVizElement(widgetId: string): GgsqlVizElement | null {
  const container = document.getElementById(widgetId);
  if (!container) {
    return null;
  }

  const tagName = container.tagName.toLowerCase();
  if (tagName === "ggsql-vega" || tagName === "ggsql-viz") {
    return container as GgsqlVizElement;
  }

  return container.querySelector<GgsqlVizElement>("ggsql-vega, ggsql-viz");
}

function triggerDownload(url: string, filename: string): void {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

function exportFromView(
  vizElement: GgsqlVizElement,
  format: ExportFormat,
  filename: string,
): void {
  const view = vizElement._view;
  if (!view) {
    return;
  }

  if (format === "png") {
    view
      .toImageURL("png")
      .then((url) => {
        triggerDownload(url, `${filename}.png`);
      })
      .catch((error: unknown) => {
        console.error("querychat: failed to export PNG:", error);
      });
    return;
  }

  view
    .toSVG()
    .then((svg) => {
      const blob = new Blob([svg], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      triggerDownload(url, `${filename}.svg`);
      URL.revokeObjectURL(url);
    })
    .catch((error: unknown) => {
      console.error("querychat: failed to export SVG:", error);
    });
}

installVizFooter({
  exportPlot(widgetId, format, filename) {
    const vizElement = findGgsqlVizElement(widgetId);
    if (!vizElement) {
      return;
    }

    exportFromView(vizElement, format, filename);
  },
});
