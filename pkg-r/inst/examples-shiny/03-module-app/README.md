# QueryChat Modules Example

This example demonstrates how to use QueryChat within Shiny modules, following standard Shiny module patterns.

## Key Concepts

### Module UI Function

In a Shiny module UI function, you wrap the QueryChat ID with the namespace function `ns()`:

```r
module_ui <- function(id) {
  ns <- NS(id)
  card(
    qc$sidebar(id = ns("qc-ui"))  # Wrap ID with ns()
  )
}
```

### Module Server Function

In the corresponding server function, you pass the **unwrapped** ID to `qc$server()`:

```r
module_server <- function(id) {
  moduleServer(id, function(input, output, session) {
    qc_vals <- qc$server(id = "qc-ui")  # Use unwrapped ID
    # ... rest of server logic
  })
}
```

## Why This Pattern?

This follows the established Shiny module pattern where:

1. **UI functions** namespace all IDs using `ns()` to avoid conflicts when multiple instances exist
2. **Server functions** receive the unwrapped ID and use it to connect to the corresponding UI

This is the same pattern used for any Shiny component in a module, and QueryChat now supports it seamlessly.

## Benefits

- **Multiple instances**: You can have multiple QueryChat explorers in the same app
- **Familiar pattern**: Uses standard Shiny module conventions
- **Clean isolation**: Each module instance has its own reactive state

## Running the Example

From the R console:

```r
shiny::runApp(system.file("examples-shiny/03-module-app", package = "querychat"))
```

Or navigate to this directory and run:

```bash
Rscript app.R
```
