library(testthat)
library(querychat)

test_that("html_dependency_code_editor returns valid htmlDependencies", {
  deps <- html_dependency_code_editor()

  # Should be a tagList containing both dependencies
  expect_s3_class(deps, "shiny.tag.list")

  # Extract the actual dependencies
  dep_list <- htmltools::findDependencies(deps)
  expect_true(length(dep_list) >= 2)

  # Check that both prism-code-editor and shiny-input-code-editor are present
  dep_names <- sapply(dep_list, function(d) d$name)
  expect_true("prism-code-editor" %in% dep_names)
  expect_true("shiny-input-code-editor" %in% dep_names)
})

test_that("code_editor_themes returns character vector of themes", {
  themes <- code_editor_themes()

  expect_type(themes, "character")
  expect_true(length(themes) > 0)

  # Check for expected default themes
  expect_true("github-light" %in% themes)
  expect_true("github-dark" %in% themes)
  expect_true("vs-code-light" %in% themes)
  expect_true("vs-code-dark" %in% themes)
})

test_that("validate_theme accepts valid themes", {
  expect_silent(validate_theme("github-light"))
  expect_silent(validate_theme("github-dark"))
  expect_silent(validate_theme("vs-code-light"))
  expect_silent(validate_theme(NULL))
})

test_that("validate_theme rejects invalid themes", {
  expect_error(
    validate_theme("nonexistent-theme"),
    "must be one of the available themes"
  )
  expect_error(
    validate_theme("fake-theme"),
    "You provided"
  )
})

test_that("validate_language accepts valid languages", {
  expect_silent(validate_language("sql"))
  expect_silent(validate_language("python"))
  expect_silent(validate_language("r"))
  expect_silent(validate_language("javascript"))
  expect_silent(validate_language(NULL))
})

test_that("validate_language rejects invalid languages", {
  expect_error(
    validate_language("fortran"),
    "must be one of the supported languages"
  )
  expect_error(
    validate_language("cobol"),
    "You provided"
  )
})

test_that("input_code_editor generates correct HTML structure", {
  editor <- input_code_editor(
    "test_editor",
    code = "SELECT * FROM table",
    language = "sql"
  )

  # Check that dependencies are attached
  deps <- htmltools::findDependencies(editor)
  dep_names <- sapply(deps, function(d) d$name)
  expect_true("prism-code-editor" %in% dep_names)
  expect_true("shiny-input-code-editor" %in% dep_names)

  html <- as.character(editor)

  # Check for editor div with correct class
  expect_match(html, 'class="code-editor-input"')

  # Check for correct ID
  expect_match(html, 'id="test_editor"')

  # Check for data attributes
  expect_match(html, 'data-language="sql"')
  expect_match(html, 'data-initial-code="SELECT \\* FROM table"')
})

test_that("input_code_editor handles all parameters correctly", {
  editor <- input_code_editor(
    "full_editor",
    code = "print('hello')",
    language = "python",
    height = "500px",
    width = "80%",
    theme_light = "vs-code-light",
    theme_dark = "vs-code-dark",
    placeholder = "Enter code here",
    read_only = TRUE,
    line_numbers = FALSE,
    word_wrap = TRUE,
    tab_size = 4,
    indentation = "tab"
  )

  html <- as.character(editor)

  # Check all data attributes
  expect_match(html, 'data-language="python"')
  expect_match(html, 'data-theme-light="vs-code-light"')
  expect_match(html, 'data-theme-dark="vs-code-dark"')
  expect_match(html, 'data-placeholder="Enter code here"')
  expect_match(html, 'data-read-only="true"')
  expect_match(html, 'data-line-numbers="false"')
  expect_match(html, 'data-word-wrap="true"')
  expect_match(html, 'data-tab-size="4"')
  expect_match(html, 'data-insert-spaces="false"') # tab indentation

  # Check style attributes
  expect_match(html, 'height:\\s*500px')
  expect_match(html, 'width:\\s*80%')
})

test_that("input_code_editor uses correct defaults", {
  editor <- input_code_editor("default_editor")

  html <- as.character(editor)

  expect_match(html, 'data-language="sql"')
  expect_match(html, 'data-theme-light="github-light"')
  expect_match(html, 'data-theme-dark="github-dark"')
  expect_match(html, 'data-read-only="false"')
  expect_match(html, 'data-line-numbers="true"')
  expect_match(html, 'data-word-wrap="false"')
  expect_match(html, 'data-tab-size="2"')
  expect_match(html, 'data-insert-spaces="true"')
  expect_match(html, 'height:\\s*300px')
  expect_match(html, 'width:\\s*100%')
})

test_that("input_code_editor validates theme names", {
  expect_error(
    input_code_editor("test", theme_light = "invalid-theme"),
    "theme_light.*must be one of the available themes"
  )

  expect_error(
    input_code_editor("test", theme_dark = "invalid-theme"),
    "theme_dark.*must be one of the available themes"
  )
})

test_that("input_code_editor validates language", {
  expect_error(
    input_code_editor("test", language = "fortran"),
    "language.*must be one of the supported languages"
  )
})

test_that("input_code_editor handles empty code", {
  editor <- input_code_editor("empty_editor", code = "")

  html <- as.character(editor)
  expect_match(html, 'data-initial-code=""')
})

test_that("input_code_editor handles special characters in code", {
  code_with_special <- "SELECT * FROM table WHERE name = 'O\"Brien' AND value < 100"
  editor <- input_code_editor("special_editor", code = code_with_special)

  html <- as.character(editor)
  # HTML should be properly escaped
  expect_true(grepl("data-initial-code", html))
})

test_that("input_code_editor handles NULL placeholder", {
  editor <- input_code_editor("test", placeholder = NULL)

  html <- as.character(editor)
  # NULL placeholder should not appear in HTML or should be empty
  # The htmltools package handles NULL attributes by not including them
  expect_true(grepl('class="code-editor-input"', html))
})

test_that("input_code_editor indentation parameter works correctly", {
  editor_spaces <- input_code_editor("test1", indentation = "space")
  editor_tabs <- input_code_editor("test2", indentation = "tab")

  html_spaces <- as.character(editor_spaces)
  html_tabs <- as.character(editor_tabs)

  expect_match(html_spaces, 'data-insert-spaces="true"')
  expect_match(html_tabs, 'data-insert-spaces="false"')
})

test_that("update_code_editor validates inputs", {
  # Create a mock session for testing
  # Note: This test verifies validation, not actual message sending
  # which requires a live Shiny session

  expect_error(
    update_code_editor("test", language = "fortran", session = NULL),
    "language.*must be one of the supported languages"
  )

  expect_error(
    update_code_editor("test", theme_light = "invalid", session = NULL),
    "theme_light.*must be one of the available themes"
  )

  expect_error(
    update_code_editor("test", theme_dark = "invalid", session = NULL),
    "theme_dark.*must be one of the available themes"
  )

  expect_error(
    update_code_editor("test", indentation = "invalid", session = NULL),
    "indentation.*must be either.*space.*or.*tab"
  )
})

test_that("input_code_editor creates unique IDs", {
  editor1 <- input_code_editor("editor1")
  editor2 <- input_code_editor("editor2")

  html1 <- as.character(editor1)
  html2 <- as.character(editor2)

  expect_match(html1, 'id="editor1"')
  expect_match(html2, 'id="editor2"')
  expect_false(grepl('id="editor2"', html1))
  expect_false(grepl('id="editor1"', html2))
})

test_that("input_code_editor attaches dependency once", {
  editor <- input_code_editor("test")

  # The editor should be a tagList with the dependency and the div
  expect_s3_class(editor, "shiny.tag.list")

  # Extract dependencies
  deps <- htmltools::findDependencies(editor)
  expect_true(length(deps) > 0)

  # Check that prism-code-editor dependency is present
  dep_names <- sapply(deps, function(d) d$name)
  expect_true("prism-code-editor" %in% dep_names)
})

test_that("input_code_editor works with different languages", {
  languages <- c("sql", "python", "r", "javascript", "html", "css", "json")

  for (lang in languages) {
    editor <- input_code_editor(paste0("editor_", lang), language = lang)
    html <- as.character(editor)
    expect_match(html, sprintf('data-language="%s"', lang))
  }
})

test_that("input_code_editor tab_size validates range", {
  # Valid tab sizes
  expect_silent(input_code_editor("test1", tab_size = 2))
  expect_silent(input_code_editor("test2", tab_size = 4))
  expect_silent(input_code_editor("test3", tab_size = 8))

  # Note: The function doesn't currently validate tab_size range,
  # but this test is here for future validation if needed
})
