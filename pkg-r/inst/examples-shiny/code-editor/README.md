# Code Editor Example

This Shiny app demonstrates all features of the `input_code_editor()` component.

## Features Demonstrated

- **Multiple language support**: Switch between SQL, Python, R, JavaScript, HTML, CSS, and JSON
- **Theme switching**: Choose from 13 available themes for light and dark modes
- **Automatic theme switching**: Editor theme changes automatically with Bootstrap theme
- **Configurable options**: Line numbers, word wrap, read-only mode, tab size, indentation
- **Live updates**: All editor options can be updated from the server
- **Sample code**: Load example code for each supported language
- **Keyboard shortcuts**: Ctrl/Cmd+Enter to submit, standard editing shortcuts
- **Copy button**: Built-in copy-to-clipboard functionality
- **Reactive updates**: Code changes trigger reactive updates (on blur or Ctrl/Cmd+Enter)

## Running the Example

From R:

```r
library(shiny)
runApp(system.file("examples-shiny/code-editor", package = "querychat"))
```

Or directly:

```r
shiny::runApp("pkg-r/inst/examples-shiny/code-editor")
```

## What to Try

1. **Language switching**: Select different languages from the dropdown and click "Load Sample Code"
2. **Theme switching**: Try different theme combinations for light and dark modes
3. **Bootstrap theme toggle**: Use the dark mode switch to see automatic theme switching
4. **Editor options**: Toggle line numbers, word wrap, read-only mode
5. **Tab settings**: Adjust tab size and switch between spaces and tabs
6. **Keyboard shortcuts**:
   - Press Ctrl/Cmd+Enter to submit code (watch the output update)
   - Try Ctrl/Cmd+Z for undo, Tab for indent, Shift+Tab for dedent
7. **Copy button**: Hover over the top-right corner to see the copy button

## Code Structure

The app demonstrates:

- Creating an editor with `input_code_editor()`
- Updating editor options with `update_code_editor()`
- Accessing editor content with `input$code`
- Getting available themes with `code_editor_themes()`
- Using the editor in a `bslib::page_sidebar()` layout
- Integration with Bootstrap 5 theme switching
