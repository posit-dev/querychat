library(shiny)
library(bslib)
library(querychat)

ui <- page_sidebar(
  title = "Code Editor Demo",
  theme = bs_theme(version = 5),

  sidebar = sidebar(
    width = 300,
    h4("Editor Controls"),

    selectInput(
      "language",
      "Language:",
      choices = c("sql", "python", "r", "javascript", "html", "css", "json"),
      selected = "sql"
    ),

    selectInput(
      "theme_light",
      "Light Theme:",
      choices = code_editor_themes(),
      selected = "github-light"
    ),

    selectInput(
      "theme_dark",
      "Dark Theme:",
      choices = code_editor_themes(),
      selected = "github-dark"
    ),

    checkboxInput("read_only", "Read Only", value = FALSE),
    checkboxInput("line_numbers", "Line Numbers", value = TRUE),
    checkboxInput("word_wrap", "Word Wrap", value = FALSE),

    sliderInput("tab_size", "Tab Size:", min = 2, max = 8, value = 2, step = 1),

    radioButtons(
      "indentation",
      "Indentation:",
      choices = c("Spaces" = "space", "Tabs" = "tab"),
      selected = "space"
    ),

    hr(),

    h4("Actions"),
    actionButton("update_settings", "Apply Settings", class = "btn-primary btn-sm w-100 mb-2"),
    actionButton("load_sample", "Load Sample Code", class = "btn-secondary btn-sm w-100 mb-2"),
    actionButton("clear_code", "Clear Editor", class = "btn-warning btn-sm w-100 mb-2"),

    hr(),

    h4("Bootstrap Theme"),
    p("Toggle to test automatic theme switching:"),
    input_dark_mode(id = "dark_mode", mode = "light")
  ),

  card(
    card_header("Code Editor"),
    card_body(
      p(
        "This editor supports syntax highlighting, line numbers, word wrap, and more. ",
        "Try pressing ", tags$kbd("Ctrl/Cmd+Enter"), " to submit the code."
      ),
      input_code_editor(
        "code",
        code = "SELECT * FROM table\nWHERE column = 'value'\nORDER BY id DESC\nLIMIT 10;",
        language = "sql",
        height = "400px",
        placeholder = "Enter your code here..."
      )
    )
  ),

  card(
    card_header("Editor Output"),
    card_body(
      h4("Current Code:"),
      verbatimTextOutput("code_output"),

      hr(),

      h4("Editor Info:"),
      verbatimTextOutput("editor_info")
    )
  ),

  card(
    card_header("Features & Keyboard Shortcuts"),
    card_body(
      tags$ul(
        tags$li(tags$kbd("Ctrl/Cmd+Enter"), " - Submit code to R (triggers reactive update)"),
        tags$li(tags$kbd("Ctrl/Cmd+Z"), " - Undo"),
        tags$li(tags$kbd("Ctrl/Cmd+Shift+Z"), " - Redo"),
        tags$li(tags$kbd("Tab"), " - Indent selection"),
        tags$li(tags$kbd("Shift+Tab"), " - Dedent selection"),
        tags$li("Copy button in top-right corner"),
        tags$li("Automatic theme switching based on Bootstrap theme"),
        tags$li("Update on blur (when editor loses focus)")
      ),

      h4("Supported Languages:"),
      p("sql, python, r, javascript, html, css, json, bash, markdown, yaml, xml"),

      h4("Available Themes:"),
      p(paste(code_editor_themes(), collapse = ", "))
    )
  )
)

server <- function(input, output, session) {
  # Sample code for different languages
  sample_code <- list(
    sql = "SELECT \n  users.id,\n  users.name,\n  COUNT(orders.id) as order_count\nFROM users\nLEFT JOIN orders ON users.id = orders.user_id\nGROUP BY users.id, users.name\nHAVING order_count > 5\nORDER BY order_count DESC;",
    python = "def fibonacci(n):\n    \"\"\"Generate Fibonacci sequence up to n terms\"\"\"\n    fib_sequence = [0, 1]\n    for i in range(2, n):\n        next_num = fib_sequence[i-1] + fib_sequence[i-2]\n        fib_sequence.append(next_num)\n    return fib_sequence\n\n# Example usage\nresult = fibonacci(10)\nprint(f\"First 10 Fibonacci numbers: {result}\")",
    r = "# Load libraries\nlibrary(dplyr)\nlibrary(ggplot2)\n\n# Analyze mtcars dataset\nmtcars %>%\n  group_by(cyl) %>%\n  summarise(\n    avg_mpg = mean(mpg),\n    avg_hp = mean(hp),\n    count = n()\n  ) %>%\n  ggplot(aes(x = factor(cyl), y = avg_mpg)) +\n  geom_col(fill = \"steelblue\") +\n  labs(title = \"Average MPG by Cylinders\",\n       x = \"Cylinders\",\n       y = \"Average MPG\")",
    javascript = "// Async function to fetch data\nasync function fetchUserData(userId) {\n  try {\n    const response = await fetch(`/api/users/${userId}`);\n    if (!response.ok) {\n      throw new Error(`HTTP error! status: ${response.status}`);\n    }\n    const data = await response.json();\n    return data;\n  } catch (error) {\n    console.error('Failed to fetch user data:', error);\n    return null;\n  }\n}\n\n// Usage\nfetchUserData(123).then(user => {\n  console.log('User data:', user);\n});",
    html = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n  <title>My Web Page</title>\n  <link rel=\"stylesheet\" href=\"styles.css\">\n</head>\n<body>\n  <header>\n    <h1>Welcome to My Website</h1>\n    <nav>\n      <ul>\n        <li><a href=\"#home\">Home</a></li>\n        <li><a href=\"#about\">About</a></li>\n        <li><a href=\"#contact\">Contact</a></li>\n      </ul>\n    </nav>\n  </header>\n  <main>\n    <p>This is the main content area.</p>\n  </main>\n</body>\n</html>",
    css = "/* Modern CSS with variables */\n:root {\n  --primary-color: #007bff;\n  --secondary-color: #6c757d;\n  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;\n}\n\nbody {\n  font-family: var(--font-family);\n  line-height: 1.6;\n  color: #333;\n  max-width: 1200px;\n  margin: 0 auto;\n  padding: 20px;\n}\n\n.card {\n  background: white;\n  border-radius: 8px;\n  box-shadow: 0 2px 4px rgba(0,0,0,0.1);\n  padding: 20px;\n  transition: transform 0.2s;\n}\n\n.card:hover {\n  transform: translateY(-2px);\n  box-shadow: 0 4px 8px rgba(0,0,0,0.15);\n}",
    json = "{\n  \"name\": \"my-app\",\n  \"version\": \"1.0.0\",\n  \"description\": \"A sample application\",\n  \"main\": \"index.js\",\n  \"scripts\": {\n    \"start\": \"node index.js\",\n    \"test\": \"jest\",\n    \"build\": \"webpack --mode production\"\n  },\n  \"dependencies\": {\n    \"express\": \"^4.18.0\",\n    \"react\": \"^18.2.0\",\n    \"react-dom\": \"^18.2.0\"\n  },\n  \"devDependencies\": {\n    \"jest\": \"^29.0.0\",\n    \"webpack\": \"^5.75.0\"\n  },\n  \"keywords\": [\"example\", \"demo\", \"sample\"],\n  \"author\": \"Your Name\",\n  \"license\": \"MIT\"\n}"
  )

  # Update settings when button is clicked
  observeEvent(input$update_settings, {
    update_code_editor(
      "code",
      language = input$language,
      theme_light = input$theme_light,
      theme_dark = input$theme_dark,
      read_only = input$read_only,
      line_numbers = input$line_numbers,
      word_wrap = input$word_wrap,
      tab_size = input$tab_size,
      indentation = input$indentation
    )
  })

  # Load sample code for selected language
  observeEvent(input$load_sample, {
    lang <- input$language
    sample <- sample_code[[lang]]
    if (!is.null(sample)) {
      update_code_editor(
        "code",
        code = sample,
        language = lang
      )
    }
  })

  # Clear editor
  observeEvent(input$clear_code, {
    update_code_editor("code", code = "")
  })

  # Display current code
  output$code_output <- renderText({
    code <- input$code
    if (is.null(code) || code == "") {
      "[Editor is empty]"
    } else {
      code
    }
  })

  # Display editor information
  output$editor_info <- renderText({
    code <- input$code
    if (is.null(code)) {
      code <- ""
    }

    lines <- length(strsplit(code, "\n")[[1]])
    chars <- nchar(code)

    paste(
      sprintf("Language: %s", input$language),
      sprintf("Lines: %d", lines),
      sprintf("Characters: %d", chars),
      sprintf("Read Only: %s", input$read_only),
      sprintf("Line Numbers: %s", input$line_numbers),
      sprintf("Word Wrap: %s", input$word_wrap),
      sprintf("Tab Size: %d", input$tab_size),
      sprintf("Indentation: %s", input$indentation),
      sep = "\n"
    )
  })
}

shinyApp(ui = ui, server = server)
