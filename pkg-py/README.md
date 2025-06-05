# querychat: Chat with Shiny apps (Python)

Imagine typing questions like these directly into your Shiny dashboard, and seeing the results in realtime:

* "Show only penguins that are not species Gentoo and have a bill length greater than 50mm."
* "Show only blue states with an incidence rate greater than 100 per 100,000 people."
* "What is the average mpg of cars with 6 cylinders?"

querychat is a drop-in component for Shiny that allows users to query a data frame using natural language. The results are available as a reactive data frame, so they can be easily used from Shiny outputs, reactive expressions, downloads, etc.

**This is not as terrible an idea as you might think!** We need to be very careful when bringing LLMs into data analysis, as we all know that they are prone to hallucinations and other classes of errors. querychat is designed to excel in reliability, transparency, and reproducibility by using this one technique: denying it raw access to the data, and forcing it to write SQL queries instead. See the section below on ["How it works"](#how-it-works) for more.

## Installation

```bash
pip install "querychat @ git+https://github.com/posit-dev/querychat#subdirectory=pkg-py"
```

## How to use

First, you'll need access to an LLM that supports tools/function calling. querychat uses [chatlas](https://github.com/posit-dev/chatlas) to interface with various providers.

Here's a very minimal example that shows the three function calls you need to make:

```python
from pathlib import Path

from seaborn import load_dataset
from shiny import App, render, ui

import querychat

# 1. Configure querychat. This is where you specify the dataset and can also
#    override options like the greeting message, system prompt, model, etc.
titanic = load_dataset("titanic")
querychat_config = querychat.init(titanic, "titanic")

# Create UI
app_ui = ui.page_sidebar(
    # 2. Use querychat.sidebar(id) in a ui.page_sidebar.
    #    Alternatively, use querychat.ui(id) elsewhere if you don't want your
    #    chat interface to live in a sidebar.
    querychat.sidebar("chat"),
    ui.output_data_frame("data_table"),
    title="querychat with Python",
    fillable=True,
)


# Define server logic
def server(input, output, session):
    # 3. Create a querychat object using the config from step 1.
    chat = querychat.server("chat", querychat_config)

    # 4. Use the filtered/sorted data frame anywhere you wish, via the
    #    chat["df"]() reactive.
    @render.data_frame
    def data_table():
        return chat.df()


# Create Shiny app
app = App(app_ui, server)
```

## How it works

### Powered by LLMs

querychat's natural language chat experience is powered by LLMs. You may use any model that [chatlas](https://github.com/posit-dev/chatlas) supports that has the ability to do tool calls, but we currently recommend (as of March 2025):

* GPT-4o
* Claude 3.5 Sonnet
* Claude 3.7 Sonnet

In our testing, we've found that those models strike a good balance between accuracy and latency. Smaller models like GPT-4o-mini are fine for simple queries but make surprising mistakes with moderately complex ones; and reasoning models like o3-mini slow down responses without providing meaningfully better results.

The small open source models (8B and below) we've tested have fared extremely poorly. Sorry. 🤷

### Powered by SQL

querychat does not have direct access to the raw data; it can _only_ read or filter the data by writing SQL `SELECT` statements. This is crucial for ensuring relability, transparency, and reproducibility:

- **Reliability:** Today's LLMs are excellent at writing SQL, but bad at direct calculation.
- **Transparency:** querychat always displays the SQL to the user, so it can be vetted instead of blindly trusted.
- **Reproducibility:** The SQL query can be easily copied and reused.

Currently, querychat uses DuckDB for its SQL engine. It's extremely fast and has a surprising number of [statistical functions](https://duckdb.org/docs/stable/sql/functions/aggregates.html#statistical-aggregates).

## Customizing querychat

### Provide a greeting (recommended)

When the querychat UI first appears, you will usually want it to greet the user with some basic instructions. By default, these instructions are auto-generated every time a user arrives; this is slow, wasteful, and unpredictable. Instead, you should create a file called `greeting.md`, and when calling `querychat.init`, pass `greeting=Path("greeting.md").read_text()`.

You can provide suggestions to the user by using the `<span class="suggestion"> </span>` tag.

For example:

```markdown
* **Filter and sort the data:**
  * <span class="suggestion">Show only survivors</span>
  * <span class="suggestion">Filter to first class passengers under 30</span>
  * <span class="suggestion">Sort by fare from highest to lowest</span>

* **Answer questions about the data:**
  * <span class="suggestion">What was the survival rate by gender?</span>
  * <span class="suggestion">What's the average age of children who survived?</span>
  * <span class="suggestion">How many passengers were traveling alone?</span>
```

These suggestions appear in the greeting and automatically populate the chat text box when clicked.
This gives the user a few ideas to explore on their own.
You can see this behavior in our [`querychat template`](https://shiny.posit.co/py/templates/querychat/).

If you need help coming up with a greeting, your own app can help you! Just launch it and paste this into the chat interface:

> Help me create a greeting for your future users. Include some example questions. Format your suggested greeting as Markdown, in a code block.

And keep giving it feedback until you're happy with the result, which will then be ready to be pasted into `greeting.md`.

Alternatively, you can completely suppress the greeting by passing `greeting=""`.

### Augment the system prompt (recommended)

In LLM parlance, the _system prompt_ is the set of instructions and specific knowledge you want the model to use during a conversation. querychat automatically creates a system prompt which is comprised of:

1. The basic set of behaviors the LLM must follow in order for querychat to work properly. (See `querychat/prompt/prompt.md` if you're curious what this looks like.)
2. The SQL schema of the data frame you provided.
3. (Optional) Any additional description of the data you choose to provide.
4. (Optional) Any additional instructions you want to use to guide querychat's behavior.

#### Data description

If you give querychat your dataset and nothing else, it will provide the LLM with the basic schema of your data:

- Column names
- DuckDB data type (integer, float, boolean, datetime, text)
- For text columns with less than 10 unique values, we assume they are categorical variables and include the list of values. This threshold is configurable.
- For integer and float columns, we include the range

And that's all the LLM will know about your data.
The actual data does not get passed into the LLM.
We calculate these values before we pass the schema information into the LLM.

If the column names are usefully descriptive, it may be able to make a surprising amount of sense out of the data. But if your data frame's columns are `x`, `V1`, `value`, etc., then the model will need to be given more background info--just like a human would.

To provide this information, use the `data_description` argument. For example, if you're using the `titanic` dataset, you might create a `data_description.md` like this:

```markdown
This dataset contains information about Titanic passengers, collected for predicting survival.

- survived: Survival (0 = No, 1 = Yes)
- pclass: Ticket class (1 = 1st, 2 = 2nd, 3 = 3rd)
- sex: Sex of passenger
- age: Age in years
- sibsp: Number of siblings/spouses aboard
- parch: Number of parents/children aboard
- fare: Passenger fare
- embarked: Port of embarkation (C = Cherbourg, Q = Queenstown, S = Southampton)
- class: Same as pclass but as text
- who: Man, woman, or child
- adult_male: Boolean for adult males
- deck: Deck of the ship
- embark_town: Town of embarkation
- alive: Survival status as text
- alone: Whether the passenger was alone
```

which you can then pass via:

```python
querychat_config = querychat.init(
    titanic,
    "titanic",
    data_description=Path("data_description.md").read_text()
)
```

querychat doesn't need this information in any particular format; just put whatever information, in whatever format, you think a human would find helpful.

#### Additional instructions

You can add additional instructions of your own to the end of the system prompt, by passing `extra_instructions` into `querychat.init`.

```python
querychat_config = querychat.init(
    titanic,
    "titanic",
    extra_instructions=[
        "You're speaking to a British audience--please use appropriate spelling conventions.",
        "Use lots of emojis! 😃 Emojis everywhere, 🌍 emojis forever. ♾️",
        "Stay on topic, only talk about the data dashboard and refuse to answer other questions."
    ]
)
```

You can also put these instructions in a separate file and use `Path("instructions.md").read_text()` to load them, as we did for `data_description` above.

**Warning:** It is not 100% guaranteed that the LLM will always—or in many cases, ever—obey your instructions, and it can be difficult to predict which instructions will be a problem. So be sure to test extensively each time you change your instructions, and especially, if you change the model you use.

### Use a different LLM provider

By default, querychat uses GPT-4o via the OpenAI API. If you want to use a different model, you can provide a `create_chat_callback` function that takes a `system_prompt` parameter, and returns a chatlas Chat object:

```python
import chatlas
from functools import partial

# Option 1: Define a function
def my_chat_func(system_prompt: str) -> chatlas.Chat:
    return chatlas.ChatAnthropic(
        model="claude-3-7-sonnet-latest",
        system_prompt=system_prompt
    )

# Option 2: Use partial
my_chat_func = partial(chatlas.ChatAnthropic, model="claude-3-7-sonnet-latest")

querychat_config = querychat.init(
    titanic,
    "titanic",
    create_chat_callback=my_chat_func
)
```

This would use Claude 3.7 Sonnet instead, which would require you to provide an API key. See the [chatlas documentation](https://github.com/posit-dev/chatlas) for more information on how to authenticate with different providers.

## Complete example

For a complete working example, see the [examples/app.py](examples/app.py) file in the repository. This example includes:

- Loading a dataset
- Reading greeting and data description from files
- Setting up the querychat configuration
- Creating a Shiny UI with the chat sidebar
- Displaying the filtered data in the main panel

If you have Shiny installed, and want to get started right away, you can use our
[querychat template](https://shiny.posit.co/py/templates/querychat/)
or
[sidebot template](https://shiny.posit.co/py/templates/sidebot/).
