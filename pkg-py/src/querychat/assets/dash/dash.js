// Register clientside callback functions for querychat
window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.querychat = {
    // Auto-scroll chat history to bottom when new messages are added
    scroll_to_bottom: function(children) {
        var chatHistories = document.querySelectorAll('.querychat-chat-history');
        chatHistories.forEach(function(chatHistory) {
            chatHistory.scrollTop = chatHistory.scrollHeight;
        });
        return window.dash_clientside.no_update;
    },

    // Show loading indicator when user sends a message
    show_loading: function(n_clicks, n_submit, message) {
        if (message && message.trim()) {
            return 'querychat-loading';
        }
        return window.dash_clientside.no_update;
    },

    // Set up suggestion click handler (with guard to prevent double-registration)
    setup_suggestion_handler: function(data) {
        if (!window._querychatSuggestionHandlerRegistered) {
            window._querychatSuggestionHandlerRegistered = true;
            document.addEventListener('click', function(e) {
                var suggestion = e.target.closest('.suggestion');
                if (suggestion) {
                    e.preventDefault();
                    var suggestionText = suggestion.textContent.trim();
                    var card = suggestion.closest('.card');
                    var chatInput = card ? card.querySelector('input[type="text"]') : null;
                    if (chatInput && window.dash_clientside && window.dash_clientside.set_props) {
                        window.dash_clientside.set_props(chatInput.id, {value: suggestionText});
                        chatInput.focus();
                    }
                }
            });
        }
        return window.dash_clientside.no_update;
    }
};
