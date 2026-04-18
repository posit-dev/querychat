(function () {
  if (!window.Shiny) return;

  var preloadObserver = null;

  function stopVizPreloadObserver() {
    if (!preloadObserver) return;
    preloadObserver.disconnect();
    preloadObserver = null;
  }

  function handleVizPreload(root) {
    if (!root || !root.isConnected) return;

    if (window.__querychatVizPreloaded) {
      root.remove();
      stopVizPreloadObserver();
      return;
    }

    window.__querychatVizPreloaded = true;
    root.removeAttribute("hidden");
    stopVizPreloadObserver();
  }

  function processVizPreloads(node) {
    if (!(node instanceof Element)) return;

    if (node.matches(".querychat-viz-preload")) {
      handleVizPreload(node);
    }

    node.querySelectorAll(".querychat-viz-preload").forEach(handleVizPreload);
  }

  processVizPreloads(document.documentElement);

  if (!window.__querychatVizPreloaded) {
    preloadObserver = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(processVizPreloads);
      });
    });

    preloadObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  }
})();
