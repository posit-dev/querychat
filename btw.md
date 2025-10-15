---
client: aws_bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0
tools:
  - docs
  # - env
  - files
  # - ide
  # - search
  # - session
  - web
---

Follow these important style rules when writing R code:

* Prefer solutions that use {tidyverse}
* Always use `<-` for assignment
* Always use the native base-R pipe `|>` for piped expressions

---

# Code Editor Component Implementation Plan

## Overview

We are adding a lightweight, language-agnostic code editor component to the querychat R package, with initial focus on SQL. The editor will use [Prism Code Editor](https://prism-code-editor.netlify.app/), a minimal alternative to Monaco/CodeMirror, suitable for displaying code in documentation, forms, and interactive applications.

**Key Requirements:**
- Language-agnostic with SQL as priority
- Bidirectional R ↔ JavaScript communication (update from R, send changes to R)
- Flexible syntax highlighting with separate light/dark themes
- Automatic theme switching based on Bootstrap 5 `data-bs-theme` attribute
- Copy-to-clipboard button
- Update triggers: blur or Ctrl/Cmd+Enter
- All options updatable from server
- Autocomplete deferred to Phase 2

## Component Naming & API

**Input Component:** `input_code_editor(id, code = "", language = "sql", ...)`
**Update Function:** `update_code_editor(session, id, code, language, theme_light, theme_dark, ...)`

This naming:
- Follows Shiny convention (`input_*`, `update_*`)
- Makes language-agnostic nature explicit
- Leaves room for future `output_code_editor()` if needed for read-only display

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         R Package                            │
│                                                              │
│  input_code_editor(id, code, language, theme_light/dark)   │
│              ↓                                              │
│     Creates <div> with data attributes                      │
│     Attaches html_dependency_code_editor()                  │
│              ↓                                              │
└──────────────┼───────────────────────────────────────────────┘
               │
               ↓ Sent to browser

┌─────────────────────────────────────────────────────────────┐
│                      Browser (JavaScript)                    │
│                                                              │
│  Shiny Input Binding detects <div class="code-editor-input">│
│              ↓                                              │
│  Creates PrismEditor instance with:                         │
│    - Prism language grammar (sql/javascript/python/etc.)   │
│    - Copy button extension                                  │
│    - Default commands (undo, redo, indent)                 │
│    - Theme CSS based on current data-bs-theme              │
│              ↓                                              │
│  Listens to:                                                │
│    - blur event → triggers input value update to R          │
│    - Ctrl/Cmd+Enter → triggers input value update to R      │
│    - data-bs-theme mutations → switches theme CSS           │
│              ↓                                              │
│  Sends current code value to Shiny input system             │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Dependency Management & Bundling

### 1.1 Set Up npm Workflow

**Create:** `package.json`

Configure npm to install `prism-code-editor` and use `cpy-cli` to copy necessary files into `pkg-r/inst/js/prism-code-editor/`.

**Required files from prism-code-editor:**
- Core: `prism-code-editor.js`, `layout.css`
- Language grammars: `languages/sql.js`, `languages/javascript.js`, `languages/python.js`, `languages/r.js`
- Extensions: `copy-button.js`, `copy-button.css`, `commands.js`
- Themes: All themes from `themes/` directory (we'll load them dynamically)

**npm scripts needed:**
- `install-deps`: Install prism-code-editor
- `copy-deps`: Use cpy-cli to copy files from `node_modules/prism-code-editor/` to `pkg-r/inst/js/prism-code-editor/`
- `update-deps`: Combined install and copy

**Directory structure after bundling:**
```
pkg-r/inst/js/prism-code-editor/
├── prism-code-editor.js
├── layout.css
├── languages/
│   ├── sql.js
│   ├── javascript.js
│   ├── python.js
│   └── r.js
├── extensions/
│   ├── copy-button.js
│   ├── copy-button.css
│   └── commands.js
└── themes/
    ├── github-light.css
    ├── github-dark.css
    ├── vs-code-light.css
    ├── vs-code-dark.css
    └── ... (all other themes)
```

### 1.2 Create JavaScript Input Binding

**Create:** `pkg-r/inst/js/code-editor-binding.js`

This file implements the Shiny input binding for the code editor using the standard Shiny input binding pattern.

**Binding Structure:**

The binding should follow Shiny's `InputBinding` interface with these key methods:

**`find(scope)`**: Return all elements with class `.code-editor-input` within scope.

**`getValue(el)`**: Return the current code content from the PrismEditor instance stored on the element. If the editor hasn't been initialized yet, return the value from the `data-initial-code` attribute.

**`setValue(el, value)`**: Update the editor's content without triggering reactivity. Used for bookmark restoration. Should call `editor.setOptions({ value })` if editor exists.

**`receiveMessage(el, data)`**: Handle messages from `session$sendInputMessage()`. The `data` object may contain:
- `code`: New code content
- `language`: New language (requires re-initialization or language switching)
- `theme_light`: New light theme name
- `theme_dark`: New dark theme name
- `read_only`: Boolean for read-only mode
- `line_numbers`: Boolean for line numbers display
- `word_wrap`: Boolean for word wrap
- `tab_size`: Number for tab size (default: 2)
- `indentation`: Enum for using `spaces` vs `tabs` (default: spaces)

When `receiveMessage()` updates values, it should call `editor.setOptions()` with the new configuration. If the update should trigger reactivity (rare), dispatch a change event.

**`subscribe(el, callback)`**: Set up event listeners for when the input value should be sent to R. Listen to:
1. Custom `codeEditorUpdate` event on the element
2. Should use `callback(true)` to enable rate policy (debouncing)

**`getRatePolicy()`**: Return `{ policy: 'debounce', delay: 300 }` to avoid excessive updates during typing.

**`unsubscribe(el)`**: Clean up event listeners using namespace to avoid memory leaks.

References (consult as needed):

* https://shiny.rstudio.com/articles/building-inputs.html
* https://github.com/gadenbuie/js4shiny/blob/main/inst/snippets/javascript.snippets#L16

**Initialization Logic:**

The binding needs an initialization function (called on first `find()` or lazily on first interaction) that:

1. Reads configuration from `data-*` attributes on the element
2. Dynamically imports the required language grammar file if not already loaded
3. Creates the PrismEditor instance using `createEditor()` from the Prism Code Editor library
4. Adds extensions: `copyButton()` and `defaultCommands()`
5. Stores the editor instance on the element (e.g., `el.prismEditor`) for later access
6. Sets up event listeners:
   - Blur event on editor's textarea → dispatch `codeEditorUpdate` event
   - Ctrl/Cmd+Enter keyboard shortcut → dispatch `codeEditorUpdate` event
7. Returns the created editor

**Theme Management:**

Create a separate initialization function that sets up Bootstrap theme watching:

1. Create a `MutationObserver` on the `<html>` element watching for `data-bs-theme` attribute changes
2. When the attribute changes, call a function to load the appropriate theme:
   - If `data-bs-theme="light"` or empty/missing → load `theme_light`
   - If `data-bs-theme="dark"` → load `theme_dark`
3. Theme loading should:
   - Create or update a `<link>` element in document head with id `code-editor-theme-{inputId}`
   - Set `href` to the theme CSS file path from the htmldep folder
   - Remove the old theme link (if exists) after new one loads to prevent flash
4. Call this function once on initialization to set the initial theme

**Language Grammar Loading:**

Maintain a global Set of loaded language names. Before creating an editor:

1. Check if language is in the loaded set
2. If not, dynamically import using: `import('/path/to/languages/{language}.js')`
3. Wait for the import promise to resolve
4. Add language to the loaded set
5. Proceed with editor creation

**Key Technical Notes:**

- The editor instance must be stored on the DOM element for access by other binding methods
- Update triggers should dispatch a custom `codeEditorUpdate` event rather than direct callback invocation
- The `subscribe()` method listens for this custom event and calls the Shiny callback
- When language changes in `receiveMessage()`, may need to recreate the editor or call `editor.setOptions({ language })` and manually retokenize
- Theme switching should not trigger reactivity
- Use jQuery's namespaced events (`.codeEditorBinding`) for easy cleanup

### 1.3 Base Styling

**Create:** `pkg-r/inst/js/code-editor.css`

Provide minimal CSS for Bootstrap 5 integration:

- Container border and border-radius to match Bootstrap form controls
- Focus styling (border color + box-shadow) matching Bootstrap input focus
- Proper `display: grid` on container (required by Prism layout)
- Responsive height handling
- Light/dark mode border color adjustments using `[data-bs-theme]` selector
- Z-index management so copy button appears above code but below modals

**Do not override Prism's theme CSS** - those provide syntax highlighting colors. Our CSS only handles the "chrome" around the editor.

## Phase 2: R Package Integration

### 2.1 HTML Dependency Function

**Create:** `pkg-r/R/input_code_editor.R`

**Function:** `html_dependency_code_editor()`

Returns an `htmltools::htmlDependency()` object that bundles:
- `prism-code-editor.js` (core library)
- `layout.css` (required layout styles)
- `copy-button.js`, `copy-button.css`
- `commands.js`
- `code-editor-binding.js` (our custom binding)
- `code-editor.css` (our integration styles)

**Important:** Do NOT include language files or theme files in the base dependency. These will be loaded dynamically by the JavaScript binding based on the `language` and `theme_*` options.

**Versioning:** Use the version from `prism-code-editor` package.json.

### 2.2 Input UI Function

**Create:** `pkg-r/R/input_code_editor.R`

**Function signature:**
```r
input_code_editor(
  id,
  code = "",
  language = "sql",
  height = "300px",
  width = "100%",
  theme_light = "github-light",
  theme_dark = "github-dark",
  placeholder = NULL,
  read_only = FALSE,
  line_numbers = TRUE,
  word_wrap = FALSE,
  tab_size = 2,
  indentation = c("space", "tab")
)
```

**Returns:** An `htmltools::tagList()` containing:
1. `html_dependency_code_editor()` dependency
2. A `<div>` with:
   - `id`: Namespaced ID
   - `class`: `"code-editor-input"`
   - `style`: Height, width, `display: grid`
   - `data-language`: The programming language
   - `data-initial-code`: The initial code content (HTML-escaped)
   - `data-theme-light`: Light theme name
   - `data-theme-dark`: Dark theme name
   - `data-read-only`: Boolean as string
   - `data-line-numbers`: Boolean as string
   - `data-word-wrap`: Boolean as string
   - `data-tab-size`: Number as string
   - `data-insert-spaces`: Boolean as string
   - `data-placeholder`: Placeholder text (if provided)

**Module support:** If `id` contains a namespace (from `shiny::NS()`), it's preserved. The binding must use the full namespaced ID.

**Validation:** Check that `language` is one of supported languages. Initially support: `"sql"`, `"javascript"`, `"python"`, `"r"`. Return informative error if unsupported language provided.

### 2.3 Update Function

**Create:** Same file as 2.2

**Function signature:**
```r
update_code_editor(
  id,
  code = NULL,
  ..., # ignored, included to require named arguments
  language = NULL,
  theme_light = NULL,
  theme_dark = NULL,
  read_only = NULL,
  line_numbers = NULL,
  word_wrap = NULL,
  tab_size = NULL,
  indentation = NULL,
  session = shiny::getDefaultReactiveDomain()
)
```

**Behavior:**
- Sends custom message to JavaScript using `session$sendInputMessage()`
- Message payload: Named list with only non-NULL values
- JavaScript input binding receives this and updates editor options

**Validation:** If `language` is provided, validate it's supported.

## Phase 3: Theme Management

### 3.1 Theme System Design

Prism Code Editor ships with 14 built-in themes. We need a system that:

1. **Discovers available themes** at package build time
2. **Validates theme names** when user specifies them
3. **Dynamically loads theme CSS** in the browser based on `data-bs-theme`

**Approach:**

**R side:**
- Helper function `code_editor_themes()` that lists available themes by reading the `themes/` directory in the bundled htmldep folder
- Validation function used by `input_code_editor()` and `update_code_editor()` to check theme names

**JavaScript side:**
- Theme CSS is loaded as `<link>` elements in document head
- Use `importmap` or dynamic imports to load theme files from the htmldep folder
- Theme file path pattern: `{htmldep_path}/themes/{theme_name}.css`

### 3.2 Automatic Theme Switching

**Implementation in code-editor-binding.js:**

On initialization:
1. Create a `MutationObserver` that watches the `<html>` element's attributes
2. When `data-bs-theme` attribute changes:
   - If new value is `"light"`, load `theme_light` CSS
   - If new value is `"dark"`, load `theme_dark` CSS
   - If value is removed or empty, default to light
3. On first load, check current `data-bs-theme` and load appropriate theme

**Theme loading mechanism:**
- Each theme gets a `<link id="code-editor-theme-{id}" rel="stylesheet" href="...">`
- When switching themes, remove old link element and add new one
- Use link's `onload` event to prevent FOUC (Flash of Unstyled Content)

### 3.3 Theme Defaults

**Default theme selection:**
- `theme_light = "github-light"` (clean, readable, GitHub-style)
- `theme_dark = "github-dark"` (consistent with light theme)

**Alternative recommendations:**
- For VS Code feel: `"vs-code-light"` / `"vs-code-dark"`
- For syntax-heavy: `"one-light"` / `"one-dark"`

Users can override per-editor or globally via a package option:
```r
options(
  querychat.code_editor_theme_light = "vs-code-light",
  querychat.code_editor_theme_dark = "night-owl"
)
```

## Phase 4: Language Support

### 4.1 Language Grammar Loading

**Challenge:** Prism Code Editor requires language grammar files to be imported before they can be used. We need to support multiple languages without loading all of them upfront.

**Solution:** Dynamic imports in JavaScript

When the binding initializes an editor:
1. Check if language grammar is already loaded (track in a global Set)
2. If not loaded, dynamically import it: `import('/path/to/languages/{language}.js')`
3. Wait for import to complete before creating editor
4. Cache that language is loaded

**Supported languages (initial):**
- `sql`: SQL queries
- `javascript`: JavaScript code
- `python`: Python code
- `r`: R code
- `markup`: HTML/XML
- `css`: CSS styles
- `json`: JSON data

**Future expansion:** Easy to add more languages by:
1. Copying additional language files from prism-code-editor
2. Adding to supported language list in validation
3. No JavaScript changes needed (dynamic import handles it)

### 4.2 Language-Specific Defaults

Different languages may benefit from different defaults:

**SQL:**
- `tab_size = 2`
- `indentation = "space"`
- `word_wrap = FALSE`
- `placeholder = "-- Enter SQL query"`

**Python:**
- `tab_size = 4`
- `indentation = "tab"`
- `placeholder = "# Enter Python code"`

**R:**
- `tab_size = 2`
- `indentation = "space"`
- `placeholder = "# Enter R code"`

Implement via internal helper function that provides language-specific defaults, which can be overridden by user arguments.

## Phase 5: Keyboard Shortcuts & UX

### 5.1 Editor Shortcuts

**Built-in from Prism Code Editor:**
- Ctrl/Cmd+Z: Undo
- Ctrl/Cmd+Shift+Z: Redo
- Tab: Indent selection
- Shift+Tab: Dedent selection
- Ctrl/Cmd+/: Toggle line comment (requires language-specific behavior)

**Custom shortcuts to add:**
- **Ctrl/Cmd+Enter: Submit code to R**
  - Trigger input value update
  - Visual feedback (brief highlight or border flash)
  - Prevent default behavior

Implementation: Add event listener to editor's textarea for keydown events, check for Ctrl/Cmd+Enter combination.

### 5.2 Copy Button

Prism Code Editor's `copyButton()` extension provides a floating copy button. Configure:
- Position: Top-right of editor
- Icon: Use clipboard icon (browser default or custom SVG)
- Tooltip: "Copy code"
- Success feedback: Brief checkmark icon or "Copied!" tooltip

### 5.3 Placeholder Text

When editor is empty, show placeholder text (like HTML `<input placeholder>`).

Implementation:
- Use `::before` pseudo-element on wrapper when editor value is empty
- Style with lower opacity and italic font
- Remove when editor gains focus or has content

## Phase 6: Testing Strategy

### 6.1 Example Shiny App

**Create:** `pkg-r/inst/examples-shiny/code-editor/app.R`

Demonstrate:
- Multiple editors with different languages on one page
- Theme switcher (buttons to change `data-bs-theme`)
- Live output showing current editor value
- Update editor from R using `update_code_editor()`
- Read-only mode toggle
- Language switching demo

### 6.2 Unit Tests

**Create:** `pkg-r/tests/testthat/test-code-editor.R`

Test coverage:
- `html_dependency_code_editor()` returns valid htmlDependency object
- `input_code_editor()` generates correct HTML structure with all data attributes
- `update_code_editor()` validation (theme names, language names)
- Language defaults are applied correctly
- Namespaced IDs work properly
- Invalid language/theme names raise errors

### 6.3 Integration Tests

Do not implement automated browser tests. This will be done manually later.

### 6.4 Manual Testing Checklist

Document in `pkg-r/examples/code-editor-manual-tests.md`:
- [ ] Copy button copies correct content
- [ ] Ctrl/Cmd+Enter triggers update
- [ ] Blur triggers update
- [ ] Theme switches automatically with Bootstrap theme
- [ ] Multiple editors on page work independently
- [ ] Syntax highlighting correct for each language
- [ ] Read-only mode prevents editing
- [ ] Undo/redo work correctly
- [ ] Line numbers toggle works
- [ ] Word wrap toggle works
- [ ] Tab size changes affect indentation
- [ ] Works in RStudio Viewer, browser, and Shiny Server

## Phase 7: Documentation

### 7.1 Function Documentation

Each should include:
- Clear description of purpose
- All parameter descriptions with types and defaults
- Return value description
- At least 3 examples of increasing complexity
- Link to related functions
- Use roxygen2 comments for documentation
- Update documentation by calling `devtools::document()`

---

## Technical Dependencies

**R Packages:**
- `htmltools`: HTML dependency management
- `shiny`: Input binding framework
- `bslib`: Bootstrap 5 integration (for theme detection)
- `jsonlite`: For serializing data to JavaScript (if passing schema)

**JavaScript Packages (via npm):**
- `prism-code-editor`: ^3.0.0 (or latest)
- `cpy-cli`: For copying files from node_modules

**Browser Requirements:**
- Modern browsers with ES6+ support
- Chrome/Edge 90+, Firefox 88+, Safari 14+
- No IE11 support (consistent with Bootstrap 5)

---

## Success Criteria

The code editor component is complete when:

1. ✅ User can add `input_code_editor()` to any Shiny app
2. ✅ Code changes in editor are sent to R as reactive input
3. ✅ `update_code_editor()` can change editor content from server
4. ✅ Themes switch automatically with Bootstrap 5 theme
5. ✅ Copy button works reliably
6. ✅ Syntax highlighting works for SQL, JavaScript, Python, R
7. ✅ Ctrl/Cmd+Enter triggers update to R
8. ✅ Blur event triggers update to R
9. ✅ All options are updatable from server
10. ✅ Component works in RStudio, browser, and Shiny Server
11. ✅ Documentation is complete with examples
12. ✅ Tests pass on all supported platforms
13. ✅ Example app demonstrates all features
