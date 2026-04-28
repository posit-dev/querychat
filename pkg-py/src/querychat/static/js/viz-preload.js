(() => {
  // In Shiny apps, reveal the first `.querychat-viz-preload` element that appears
  // and then stop watching the DOM. This is a one-time, page-level initialization:
  // if a preload element already exists at startup, reveal it immediately; otherwise
  // observe DOM mutations until one is added, then reveal it and disconnect.

  if (!window.Shiny || window.__querychatVizPreloaded) return;

  let preloadObserver;

  const stopVizPreloadObserver = () => {
    preloadObserver?.disconnect();
    preloadObserver = undefined;
  };

  const findVizPreload = (node) => {
    if (!(node instanceof Element)) return null;
    return node.matches(".querychat-viz-preload")
      ? node
      : node.querySelector(".querychat-viz-preload");
  };

  const revealVizPreload = (root) => {
    if (!root?.isConnected || window.__querychatVizPreloaded) return false;

    window.__querychatVizPreloaded = true;
    root.hidden = false;
    stopVizPreloadObserver();
    return true;
  };

  const processVizPreloads = (node) => {
    const preloadRoot = findVizPreload(node);
    if (!preloadRoot) return false;
    return revealVizPreload(preloadRoot);
  };

  if (processVizPreloads(document.documentElement)) return;

  preloadObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (processVizPreloads(node)) return;
      }
    }
  });

  preloadObserver.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
