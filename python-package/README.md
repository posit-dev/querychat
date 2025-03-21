# querychat for Python

Chat with your Shiny Python apps using natural language.

Imagine typing questions like these directly into your Shiny dashboard, and seeing the results in realtime:

* "Show only data from 2008 with highway MPG greater than 30."
* "What's the average city MPG for SUVs vs compact cars?"
* "Sort the data by highway fuel efficiency descending."

## Installation

```bash
pip install "querychat @ git+https://github.com/posit-dev/querychat#subdirectory=python-package"
```

## How to use

First, you'll need access to an LLM that supports tools/function calling. querychat uses [chatlas](https://github.com/posit-dev/chatlas) to interface with various providers.

Here's a minimal example (see [examples/app.py](examples/app.py) for an unabridged version):

```python
from pathlib import Path

from seaborn import load_dataset
from shiny import App, render, ui

import querychat

titanic = load_dataset("titanic")

# 1. Configure querychat
querychat_config = querychat.init(titanic, "titanic")

# Create UI
app_ui = ui.page_sidebar(
    # 2. Place the chat component in the sidebar
    querychat.sidebar("chat"),
    # Main panel with data viewer
    ui.output_data_frame("data_table"),
    title="querychat with Python",
    fillable=True,
)


# Define server logic
def server(input, output, session):
    # 3. Initialize querychat server with the config from step 1
    chat = querychat.server("chat", querychat_config)

    # 4. Display the filtered dataframe
    @render.data_frame
    def data_table():
        # Access filtered data via chat.df() reactive
        return chat["df"]()


# Create Shiny app
app = App(app_ui, server)
```

## Features

querychat uses LLMs to generate SQL queries from natural language, offering:

- **Reliability**: LLMs are excellent at writing SQL but bad at direct calculation
- **Transparency**: SQL is always displayed to the user
- **Reproducibility**: Generated SQL can be copied and reused elsewhere

## Customization

### Configure with your own data

```python
querychat_config = querychat.init(
    df=my_dataframe,
    table_name="my_data",  # Optional: defaults to "data"
    greeting="Welcome! Ask me anything about the data.",
    data_description="""
    This dataset contains information about...
    - column1: Description of column 1
    - column2: Description of column 2
    """,
    extra_instructions="Please use British English spelling conventions."
)
```

### Use a different LLM provider

You can configure which LLM provider to use through chatlas:

```python
import chatlas

querychat_config = querychat.init(
    df=my_dataframe,
    create_chat_func=lambda x: chatlas.ChatAnthropic(system_prompt=x)
)
```

## How it works

querychat works by:

1. Converting your pandas DataFrame to a DuckDB table
2. Creating a system prompt with your data schema
3. Setting up tools that let the LLM execute SQL queries
4. Processing natural language to SQL queries
5. Returning filtered data to your Shiny app

See the `examples/` directory for more complete examples.
