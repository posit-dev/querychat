const targetDoc = window.parent.document;

targetDoc.addEventListener('click', function(e) {
    const suggestion = e.target.closest('.suggestion');

    if (suggestion) {
        e.preventDefault();

        const suggestionText = suggestion.textContent.trim();
        const chatInput = targetDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');

        if (chatInput) {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.parent.HTMLTextAreaElement.prototype,
                'value'
            ).set;
            nativeInputValueSetter.call(chatInput, suggestionText);

            chatInput.dispatchEvent(new Event('input', { bubbles: true }));
            chatInput.focus();
        }
    }
});
