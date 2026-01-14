# Playwright E2E Tests

End-to-end tests for querychat example applications using Playwright.

## Running Tests

```bash
# Install playwright browsers (one-time setup)
make py-e2e-setup

# Run tests that don't require LLM API calls (used in CI)
make py-e2e-tests

# Run all tests including those that call LLM APIs
make py-e2e-tests-all
```

## Test Categories

### Non-VCR Tests (Run in CI)
Tests without `@pytest.mark.vcr` verify UI behavior without making LLM API calls:
- App loads correctly
- UI components are visible
- Chat input works
- Static content displays properly

These run automatically in CI via GitHub Actions.

### VCR Tests (Local Only)
Tests marked with `@pytest.mark.vcr(record_mode="once")` make actual LLM API calls and require:
- `OPENAI_API_KEY` environment variable (or other provider key)
- Network access to the LLM API

These are excluded from CI runs (`-k "not vcr"`).

## Recording LLM Responses (Future)

To enable VCR tests in CI, you would:

1. Run tests locally with API key to record cassettes:
   ```bash
   OPENAI_API_KEY=sk-... make py-e2e-tests-all
   ```

2. Commit the generated `cassettes/` directory

3. Update CI to run all tests (cassettes replay without API calls)

Currently, VCR tests are development-only for verifying LLM integration works correctly.

## Test Structure

```
playwright/
├── conftest.py          # Fixtures for starting app servers
├── patterns.py          # Shared regex patterns
├── test_01_hello_app.py # Shiny basic example tests
├── test_02_prompt_app.py# Shiny custom prompt tests
├── test_03_sidebar_apps.py # Shiny sidebar layout tests
├── test_04_streamlit_apps.py # Streamlit integration tests
├── test_05_gradio_apps.py    # Gradio integration tests
└── test_06_dash_apps.py      # Dash integration tests
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
