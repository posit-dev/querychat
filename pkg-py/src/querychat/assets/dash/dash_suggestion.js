// Handle clicks on suggestion elements to populate chat input
document.addEventListener('click', function(e) {
    var suggestion = e.target.closest('.suggestion');
    if (suggestion) {
        e.preventDefault();
        var suggestionText = suggestion.textContent.trim();
        // Find the chat input within the same card container (works with any table name)
        var card = suggestion.closest('.card');
        var chatInput = card ? card.querySelector('input[type="text"]') : null;
        if (chatInput && window.dash_clientside && window.dash_clientside.set_props) {
            window.dash_clientside.set_props(chatInput.id, {value: suggestionText});
            chatInput.focus();
        }
    }
});

// Register clientside callback functions for querychat
window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.querychat = {
    // Auto-scroll chat history to bottom when new messages are added
    // Finds the scrollable element by class name
    scroll_to_bottom: function(children) {
        // Find all querychat chat-history elements and scroll them
        var chatHistories = document.querySelectorAll('.querychat-chat-history');
        chatHistories.forEach(function(chatHistory) {
            chatHistory.scrollTop = chatHistory.scrollHeight;
        });
        return window.dash_clientside.no_update;
    },

    // Show loading indicator when user sends a message
    // Called immediately on button click/enter, before server callback
    show_loading: function(n_clicks, n_submit, message) {
        // Only show if there's actually a message to send
        if (message && message.trim()) {
            return 'querychat-loading';  // Remove d-none to show
        }
        return window.dash_clientside.no_update;
    }
};
