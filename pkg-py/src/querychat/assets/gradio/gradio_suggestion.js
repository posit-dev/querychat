(function() {
    document.addEventListener('click', function(e) {
        const suggestion = e.target.closest('.suggestion');

        if (suggestion) {
            e.preventDefault();

            const suggestionText = suggestion.textContent.trim();
            const chatInput = document.querySelector('textarea[data-testid="textbox"]');

            if (chatInput) {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    HTMLTextAreaElement.prototype,
                    'value'
                ).set;
                nativeInputValueSetter.call(chatInput, suggestionText);

                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                chatInput.focus();
            }
        }
    });
})();
