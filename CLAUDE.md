# querychat

## Project Overview

querychat is a multilingual package that allows users to chat with their data using natural language queries. It's available for R (Shiny) and Python (Shiny for Python).

The core functionality translates natural language queries into SQL statements that are executed against data sources. This approach ensures reliability, transparency, and reproducibility by:

1. Leveraging LLMs' strengths in writing SQL
2. Providing transparency with visible SQL queries
3. Enabling reproducibility through reusable queries

## Repository Structure

The repository contains separate packages for R and Python:

```
/
├── pkg-r/                  # R package implementation
│   ├── R/                  # R source files
│   ├── inst/               # Installed files
│   │   ├── examples-shiny/ # Shiny example applications
│   │   ├── htmldep/        # HTML dependencies
│   │   └── prompts/        # Prompt templates
│   └── tests/              # testthat test suite
│
├── pkg-py/       # Python package implementation
│   ├── src/      # Python source files
│   ├── tests/    # pytest test suite
│   └── examples/ # Example applications
│
├── docs/ # Documentation site
├── _dev/ # Development utilities and demos (local scratch space only)
```

## Common Commands

### Python Package

We use `uv` for Python package management and `make` for common tasks.

```bash
# Setup Python environment
make py-setup

# Run Python checks (format, types, tests)
make py-check
make py-check-format
make py-check-types
make py-check-tests

# Format Python code
make py-format

# Build Python package
make py-build

# Build Python documentation
make py-docs
```

### R Package

```bash
# Install R dependencies
make r-setup

# Run R checks (format, tests, package)
make r-check
make r-check-format
make r-check-tests
make r-check-package

# Format R code
make r-format

# Document R package
make r-document

# Build R documentation
make r-docs
```

### Documentation

```bash
# Build all documentation
make docs

# Preview R docs
make r-docs-preview

# Preview Python docs
make py-docs-preview
```

## Code Architecture

### Core Components

1. **Data Sources**: Abstractions for data frames and database connections that provide schema information and execute SQL queries
   - R: `querychat_data_source()` in `pkg-r/R/data_source.R`
   - Python: `DataSource` classes in `pkg-py/src/querychat/datasource.py`

2. **LLM Client**: Integration with LLM providers (OpenAI, Anthropic, etc.) through:
   - R: ellmer package
   - Python: chatlas package

3. **Query Chat Interface**: UI components and server logic for the chat experience:
   - R: `querychat_sidebar()`, `querychat_ui()`, and `querychat_server()` in `pkg-r/R/querychat.R`
   - Python: `QueryChat` class in `pkg-py/src/querychat/querychat.py`

4. **Prompt Engineering**: System prompts and tool definitions that guide the LLM:
   - R: `pkg-r/inst/prompts/`
     - Main prompt (`prompt.md`)
     - Tool descriptions (`tool-query.md`, `tool-reset-dashboard.md`, `tool-update-dashboard.md`)
   - Python: `pkg-py/src/querychat/prompts/`
     - Main prompt (`prompt.md`)
     - Tool descriptions (`tool-query.md`, `tool-reset-dashboard.md`, `tool-update-dashboard.md`)

### Data Flow

1. User enters a natural language query in the UI
2. The query is sent to an LLM along with schema information
3. The LLM generates a SQL query using tool calling
4. The SQL query is executed against the data source
5. Results are returned and displayed in the UI
6. The SQL query is also displayed for transparency

## Recommendations for Development

1. Always test changes with both R and Python implementations to maintain consistency
2. Use the provided Make commands for development tasks
3. Follow the existing code style (ruff for Python, `air format .` for R)
4. Ask before running tests (the user may want to run them themselves)
5. Update documentation when adding new features
6. Always ask about file names before writing any new code
7. Always pay attention to your working directory when running commands, especially when working in a sub-package.
8. When planning, talk through all function and argument names, file names and locations.
9. Additional, context-specific instructions can be found in `.claude/`.
