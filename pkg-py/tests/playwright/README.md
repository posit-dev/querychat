# Playwright E2E Tests

End-to-end tests for querychat example applications using Playwright.

## Running Tests

```bash
# Install playwright browsers (one-time setup)
make py-e2e-setup

# Run all tests (requires OPENAI_API_KEY)
make py-e2e-tests
```

## What Tests Cover

- App loads correctly
- UI components render properly
- Chat input accepts text
- LLM queries update SQL and data
- Analytical queries show results in chat

## Test Structure

```
playwright/
├── conftest.py              # Fixtures for starting app servers
├── test_01_hello_app.py     # Shiny basic example tests
├── test_02_prompt_app.py    # Shiny custom prompt tests
├── test_03_sidebar_apps.py  # Shiny sidebar layout tests
├── test_04_streamlit_apps.py# Streamlit integration tests
├── test_05_gradio_apps.py   # Gradio integration tests
└── test_06_dash_apps.py     # Dash integration tests
```

## Debugging

```bash
# Run with visible browser
uv run pytest pkg-py/tests/playwright -v --headed

# Run with slow motion (500ms delay between actions)
uv run pytest pkg-py/tests/playwright -v --slowmo=500

# Run specific test
uv run pytest pkg-py/tests/playwright/test_01_hello_app.py::Test01HelloApp::test_app_loads_successfully -v
```
