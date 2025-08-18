(function () {
  if (!window.Shiny) return;

  window.addEventListener("click", function (event) {
    if (event.target.tagName.toLowerCase() !== "button") return;
    if (!event.target.matches(".querychat-update-dashboard-btn")) return;

    const chatContainer = event.target.closest("shiny-chat-container");
    if (!chatContainer) return;

    const chatId = chatContainer.id;
    const { query, title } = event.target.dataset;

    window.Shiny.setInputValue(
      chatId + "_update",
      { query, title },
      { priority: "event" }
    );
  });
})();
