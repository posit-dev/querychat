(function () {
  if (!window.Shiny) return;

  window.addEventListener("click", function (event) {
    if (event.target.tagName.toLowerCase() !== "button") return;
    if (!event.target.matches(".querychat-update-dashboard-btn")) return;

    const chatContainer = event.target.closest("shiny-chat-container");
    if (!chatContainer) return;

    const chatId = chatContainer.id;
    const { query, title, table } = event.target.dataset;

    window.Shiny.setInputValue(
      chatId + "_update",
      { query, title, table },
      { priority: "event" }
    );
  });

  // R Shiny only re-scans output visibility on bindAll/unbindAll or
  // Bootstrap/jQuery shown/hidden events -- the chat drawer toggling its
  // `hidden` attribute triggers none of those, so outputs inside an
  // initially-closed drawer would stay server-suspended forever. Nudge Shiny
  // when the drawer opens/closes. (Only R Shiny ships jQuery; py-shiny
  // tracks output visibility on its own.)
  if (window.jQuery) {
    new MutationObserver(function (mutations) {
      for (const mutation of mutations) {
        const el = mutation.target;
        if (!el.matches("aside.shiny-chat-drawer")) continue;
        window
          .jQuery(el)
          .trigger(el.hasAttribute("hidden") ? "hidden" : "shown");
      }
    }).observe(document.documentElement, {
      subtree: true,
      attributes: true,
      attributeFilter: ["hidden"],
    });
  }
})();
