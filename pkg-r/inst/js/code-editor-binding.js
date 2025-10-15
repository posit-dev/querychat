/**
 * Shiny Input Binding for Prism Code Editor
 *
 * This binding creates a bidirectional connection between R and a Prism Code Editor instance,
 * allowing code content to be sent from the editor to R and updated from R to the editor.
 */

// Track which languages have been loaded to avoid duplicate imports
const loadedLanguages = new Set();

// Track which editor instances have been initialized
const initializedEditors = new WeakSet();

// Memoized base path for prism-code-editor files
let _prismCodeEditorBasePath = null;

/**
 * Discovers and memoizes the base path for prism-code-editor files
 * by finding the script element that loaded index.js
 * @returns {string} The base path to prism-code-editor files
 */
function getPrismCodeEditorBasePath() {
  if (_prismCodeEditorBasePath !== null) {
    return _prismCodeEditorBasePath;
  }

  // Find the script element that loaded prism-code-editor's index.js
  const scriptElement = document.querySelector('script[src*="prism-code-editor"][src$="index.js"]');

  if (!scriptElement) {
    console.error('Could not find prism-code-editor script element');
    _prismCodeEditorBasePath = '';
    return _prismCodeEditorBasePath;
  }

  // Extract the base path from the src attribute
  const src = scriptElement.getAttribute('src');

  // Convert relative URL to absolute URL
  const absoluteSrc = new URL(src, document.baseURI).href;

  // Remove '/index.js' from the end to get the base path
  _prismCodeEditorBasePath = absoluteSrc.replace(/\/index\.js$/, '');

  return _prismCodeEditorBasePath;
}


/**
 * Dynamically loads a language grammar module if not already loaded
 *
 * Prism grammars from prism-code-editor register themselves via side effects
 * when imported. They should be imported from prism/languages/ not the regular
 * languages/ directory.
 *
 * @param {string} language - The language identifier (e.g., 'sql', 'python', 'r')
 * @param {string} prismCodeEditorBasePath - The base path to the prism-code-editor files
 * @returns {Promise<void>}
 */
async function loadLanguage(language, prismCodeEditorBasePath) {
  if (loadedLanguages.has(language)) {
    return;
  }

  // HTML is included in the clike grammar which is loaded by default
  if (language === 'html') {
    language = 'markup';
  }

  try {
    // Import from prism/languages/ not regular languages/
    // The prism grammars register themselves through side effects
    await import(`${prismCodeEditorBasePath}/prism/languages/${language}.js`);
    loadedLanguages.add(language);
  } catch (error) {
    console.error(`Failed to load language '${language}':`, error);
    throw error;
  }
}

/**
 * Loads or switches the theme CSS for an editor instance
 * @param {string} inputId - The editor's input ID
 * @param {string} themeName - The theme name (e.g., 'github-light', 'vs-code-dark')
 * @param {string} prismCodeEditorBasePath - The base path to prism-code-editor files
 */
function loadTheme(inputId, themeName, prismCodeEditorBasePath) {
  const linkId = `code-editor-theme-${inputId}`;
  const existingLink = document.getElementById(linkId);

  const newLink = document.createElement('link');
  newLink.id = linkId;
  newLink.rel = 'stylesheet';
  newLink.href = `${prismCodeEditorBasePath}/themes/${themeName}.css`;

  // Add new link to head
  document.head.appendChild(newLink);

  // Remove old link after new one loads to prevent FOUC
  if (existingLink) {
    newLink.addEventListener('load', () => {
      existingLink.remove();
    });
  }
}

/**
 * Sets up theme watching for Bootstrap 5 data-bs-theme attribute
 * @param {HTMLElement} el - The editor container element
 * @param {string} themeLight - Light theme name
 * @param {string} themeDark - Dark theme name
 * @param {string} prismCodeEditorBasePath - Base path to prism-code-editor files
 */
function setupThemeWatcher(el, themeLight, themeDark, prismCodeEditorBasePath) {
  const inputId = el.id;

  // Function to load appropriate theme based on current data-bs-theme
  const updateTheme = () => {
    const htmlEl = document.documentElement;
    const theme = htmlEl.getAttribute('data-bs-theme');
    const themeName = (theme === 'dark')
      ? el.dataset.themeDark || themeDark
      : el.dataset.themeLight || themeLight;
    loadTheme(inputId, themeName, prismCodeEditorBasePath);
  };

  // Set initial theme
  updateTheme();

  // Watch for theme changes
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
        updateTheme();
      }
    }
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-bs-theme']
  });

  // Store observer on element for cleanup
  el._themeObserver = observer;
}

/**
 * Initializes a Prism Code Editor instance for an element
 * @param {HTMLElement} el - The editor container element
 * @returns {Promise<Object>} The created editor instance
 */
async function initializeEditor(el) {
  if (initializedEditors.has(el)) {
    return el.prismEditor;
  }

  // Get configuration from data attributes
  const language = el.dataset.language || 'sql';
  const initialCode = el.dataset.initialCode || '';
  const themeLight = el.dataset.themeLight || 'github-light';
  const themeDark = el.dataset.themeDark || 'github-dark';
  const readOnly = el.dataset.readOnly === 'true';
  const lineNumbers = el.dataset.lineNumbers !== 'false'; // default true
  const wordWrap = el.dataset.wordWrap === 'true';
  const tabSize = parseInt(el.dataset.tabSize) || 2;
  const insertSpaces = el.dataset.insertSpaces !== 'false'; // default true
  const placeholder = el.dataset.placeholder || '';

  // Get the base path to prism-code-editor files
  const prismCodeEditorBasePath = getPrismCodeEditorBasePath();

  // Load required language grammar
  await loadLanguage(language, prismCodeEditorBasePath);

  // Dynamically import the createEditor function and extensions
  const { createEditor } = await import(`${prismCodeEditorBasePath}/index.js`);
  const { copyButton } = await import(`${prismCodeEditorBasePath}/extensions/copyButton/index.js`);
  const { defaultCommands } = await import(`${prismCodeEditorBasePath}/extensions/commands.js`);

  // Create editor instance
  const editor = createEditor(
    el,
    {
      language: language,
      value: initialCode,
      tabSize: tabSize,
      insertSpaces: insertSpaces,
      lineNumbers: lineNumbers,
      wordWrap: wordWrap,
      readOnly: readOnly,
      placeholder: placeholder
    },
    copyButton(),
    defaultCommands()
  );

  // Store editor instance on element
  el.prismEditor = editor;
  initializedEditors.add(el);

  // Set up theme management
  setupThemeWatcher(el, themeLight, themeDark, prismCodeEditorBasePath);

  // Set up event listeners for value changes
  const textarea = el.querySelector('textarea');
  if (textarea) {
    // Blur event
    textarea.addEventListener('blur', () => {
      el.dispatchEvent(new CustomEvent('codeEditorUpdate'));
    });

    // Ctrl/Cmd+Enter keyboard shortcut
    textarea.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        el.dispatchEvent(new CustomEvent('codeEditorUpdate'));

        // Visual feedback: brief border flash
        el.classList.add('code-editor-submit-flash');
        setTimeout(() => {
          el.classList.remove('code-editor-submit-flash');
        }, 200);
      }
    });
  }

  return editor;
}

// Define the Shiny input binding
const codeEditorBinding = new Shiny.InputBinding();

$.extend(codeEditorBinding, {
  // Find all code editor elements in the scope
  find: function(scope) {
    return $(scope).find('.shiny-input-code-editor');
  },

  // Get the current value of the editor
  getValue: function(el) {
    if (el.prismEditor) {
      return el.prismEditor.value;
    }
    // Return initial value if editor not yet initialized
    return el.dataset.initialCode || '';
  },

  // Set the value without triggering reactivity (for bookmark restoration)
  setValue: function(el, value) {
    if (el.prismEditor) {
      el.prismEditor.setOptions({ value: value });
    } else {
      // Update data attribute for when editor initializes
      el.dataset.initialCode = value;
    }
  },

  // Subscribe to value changes
  subscribe: function(el, callback) {
    // Initialize editor lazily on first subscription
    initializeEditor(el).catch(error => {
      console.error('Failed to initialize code editor:', error);
    });

    this._updateCallback = () => callback(true); // true enables rate policy

    // Listen for custom update events
    el.addEventListener('codeEditorUpdate', this._updateCallback);
  },

  // Unsubscribe from value changes
  unsubscribe: function(el) {
    el.removeEventListener('codeEditorUpdate', this._updateCallback);

    // Clean up theme observer
    if (el._themeObserver) {
      el._themeObserver.disconnect();
      delete el._themeObserver;
    }
  },

  // Handle messages from R (update_code_editor calls)
  receiveMessage: function(el, data) {
    const editor = el.prismEditor;

    if (!editor) {
      console.warn('Cannot update code editor: editor not initialized');
      return;
    }

    // Build options object for updates
    const options = {};

    if (data.code !== undefined) {
      options.value = data.code;
    }

    if (data.tab_size !== undefined) {
      options.tabSize = data.tab_size;
    }

    if (data.indentation !== undefined) {
      options.insertSpaces = (data.indentation === 'space');
    }

    if (data.read_only !== undefined) {
      options.readOnly = data.read_only;
    }

    if (data.line_numbers !== undefined) {
      options.lineNumbers = data.line_numbers;
    }

    if (data.word_wrap !== undefined) {
      options.wordWrap = data.word_wrap;
    }

    // Apply options to editor
    if (Object.keys(options).length > 0) {
      editor.setOptions(options);
    }

    // Handle language change (requires grammar loading and reinitialization)
    if (data.language !== undefined && data.language !== el.dataset.language) {
      const prismCodeEditorBasePath = getPrismCodeEditorBasePath();
      loadLanguage(data.language, prismCodeEditorBasePath).then(() => {
        el.dataset.language = data.language;
        editor.setOptions({ language: data.language });
        // Force retokenization
        editor.update();
      }).catch(error => {
        console.error(`Failed to change language to '${data.language}':`, error);
      });
    }

    // Handle theme updates
    if (data.theme_light !== undefined) {
      el.dataset.themeLight = data.theme_light;
      // Re-evaluate current theme
      const htmlEl = document.documentElement;
      const currentTheme = htmlEl.getAttribute('data-bs-theme');
      if (currentTheme !== 'dark') {
        const prismCodeEditorBasePath = getPrismCodeEditorBasePath();
        loadTheme(el.id, data.theme_light, prismCodeEditorBasePath);
      }
    }

    if (data.theme_dark !== undefined) {
      el.dataset.themeDark = data.theme_dark;
      // Re-evaluate current theme
      const htmlEl = document.documentElement;
      const currentTheme = htmlEl.getAttribute('data-bs-theme');
      if (currentTheme === 'dark') {
        const prismCodeEditorBasePath = getPrismCodeEditorBasePath();
        loadTheme(el.id, data.theme_dark, prismCodeEditorBasePath);
      }
    }
  },

  // Rate policy: debounce to avoid excessive updates
  getRatePolicy: function() {
    return {
      policy: 'debounce',
      delay: 300
    };
  }
});

// Register the binding with Shiny
Shiny.inputBindings.register(codeEditorBinding, 'querychat.codeEditorBinding');
