# querychat: Chat with Shiny apps (R)

Imagine typing questions like these directly into your Shiny dashboard, and seeing the results in realtime:

* "Show only penguins that are not species Gentoo and have a bill length greater than 50mm."
* "Show only blue states with an incidence rate greater than 100 per 100,000 people."
* "What is the average mpg of cars with 6 cylinders?"

querychat is a drop-in component for Shiny that allows users to query a data frame using natural language. The results are available as a reactive data frame, so they can be easily used from Shiny outputs, reactive expressions, downloads, etc.

**This is not as terrible an idea as you might think!** We need to be very careful when bringing LLMs into data analysis, as we all know that they are prone to hallucinations and other classes of errors. querychat is designed to excel in reliability, transparency, and reproducibility by using this one technique: denying it raw access to the data, and forcing it to write SQL queries instead. See the section below on ["How it works"](#how-it-works) for more.

## Installation

```r
pak::pak("posit-dev/querychat/pkg-r")
```

## How to use

First, you'll need an OpenAI API key. See the [instructions from Ellmer](https://ellmer.tidyverse.org/reference/chat_openai.html). (Or use a different LLM provider, see below.)

Here's a very minimal example that shows the three function calls you need to make.

```r
library(shiny)
library(bslib)
library(querychat)

# 1. Create a data source for querychat
mtcars_source <- querychat_data_source(mtcars)

# 2. Configure querychat with the data source
querychat_config <- querychat_init(mtcars_source)

ui <- page_sidebar(
  # 3. Use querychat_sidebar(id) in a bslib::page_sidebar.
  #    Alternatively, use querychat_ui(id) elsewhere if you don't want your
  #    chat interface to live in a sidebar.
  sidebar = querychat_sidebar("chat"),
  DT::DTOutput("dt")
)

server <- function(input, output, session) {

  # 4. Create a querychat object using the config from step 2.
  querychat <- querychat_server("chat", querychat_config)

  output$dt <- DT::renderDT({
    # 5. Use the filtered/sorted data frame anywhere you wish, via the
    #    querychat$df() reactive.
    DT::datatable(querychat$df())
  })
}

shinyApp(ui, server)
```

## Using Database Sources

In addition to data frames, querychat can connect to external databases via DBI:

```r
library(shiny)
library(bslib)
library(querychat)
library(DBI)
library(RSQLite)

# 1. Connect to a database
conn <- DBI::dbConnect(RSQLite::SQLite(), "path/to/database.db")

# 2. Create a database data source for querychat
db_source <- querychat_data_source(conn, "table_name")

# 3. Configure querychat with the database source
querychat_config <- querychat_init(db_source)

# Then use querychat_config in your Shiny app as shown above
```

## How it works

### Powered by LLMs

querychat's natural language chat experience is powered by LLMs. You may use any model that [ellmer](https://ellmer.tidyverse.org) supports that has the ability to do tool calls, but we currently recommend (as of March 2025):

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

Currently, querychat uses DuckDB for its SQL engine when working with data frames. For database sources, it uses the native SQL dialect of the connected database. DuckDB is extremely fast and has a surprising number of [statistical functions](https://duckdb.org/docs/stable/sql/functions/aggregates.html#statistical-aggregates).

## Customizing querychat

### Provide a greeting (recommended)

When the querychat UI first appears, you will usually want it to greet the user with some basic instructions. By default, these instructions are auto-generated every time a user arrives; this is slow, wasteful, and unpredictable. Instead, you should create a file called `greeting.md`, and when calling `querychat_init`, pass `greeting = readLines("greeting.md")`.

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

If you need help coming up with a greeting, your own app can help you! Just launch it and paste this into the chat interface:

> Help me create a greeting for your future users. Include some example questions. Format your suggested greeting as Markdown, in a code block.

And keep giving it feedback until you're happy with the result, which will then be ready to be pasted into `greeting.md`.

Alternatively, you can completely suppress the greeting by passing `greeting = ""`.

### Augment the system prompt (recommended)

In LLM parlance, the _system prompt_ is the set of instructions and specific knowledge you want the model to use during a conversation. querychat automatically creates a system prompt which is comprised of:

1. The basic set of behaviors the LLM must follow in order for querychat to work properly. (See `inst/prompt/prompt.md` if you're curious what this looks like.)
2. The SQL schema of the data source you provided.
3. (Optional) Any additional description of the data you choose to provide.
4. (Optional) Any additional instructions you want to use to guide querychat's behavior.

#### Data description

If you give querychat your dataset and nothing else, it will provide the LLM with the basic schema of your data:

- Column names
- SQL data type (integer, float, boolean, datetime, text)
- For text columns with less than 10 unique values, we assume they are categorical variables and include the list of values
- For integer and float columns, we include the range

And that's all the LLM will know about your data.
The actual data does not get passed into the LLM.
We calculate these values before we pass the schema information into the LLM.

If the column names are usefully descriptive, it may be able to make a surprising amount of sense out of the data. But if your data frame's columns are `x`, `V1`, `value`, etc., then the model will need to be given more background info--just like a human would.

To provide this information, use the `data_description` argument. For example, the `mtcars` data frame used in the example above has pretty minimal column names. You might create a `data_description.md` like this:

```markdown
The data was extracted from the 1974 Motor Trend US magazine, and
comprises fuel consumption and 10 aspects of automobile design and
performance for 32 automobiles (1973–74 models).

- mpg:  Miles/(US) gallon
- cyl:  Number of cylinders
- disp: Displacement (cu.in.)
- hp:   Gross horsepower
- drat: Rear axle ratio
- wt:   Weight (1000 lbs)
- qsec: 1/4 mile time
- vs:   Engine (0 = V-shaped, 1 = straight)
- am:   Transmission (0 = automatic, 1 = manual)
- gear: Number of forward gears
- carb: Number of carburetors
```

which you can then pass via:

```r
# Create data source first
mtcars_source <- querychat_data_source(mtcars, tbl_name = "cars")

# Then initialize with the data source and description
querychat_config <- querychat_init(
  data_source = mtcars_source,
  data_description = readLines("data_description.md")
)
```

querychat doesn't need this information in any particular format; just put whatever information, in whatever format, you think a human would find helpful.

#### Additional instructions

You can add additional instructions of your own to the end of the system prompt, by passing `extra_instructions` into `query_init`.

```r
# Create data source first
mtcars_source <- querychat_data_source(mtcars, tbl_name = "cars")

# Then initialize with instructions
querychat_config <- querychat_init(
  data_source = mtcars_source,
  extra_instructions = c(
    "You're speaking to a British audience--please use appropriate spelling conventions.",
    "Use lots of emojis! 😃 Emojis everywhere, 🌍 emojis forever. ♾️",
    "Stay on topic, only talk about the data dashboard and refuse to answer other questions."
  )
)
```

You can also put these instructions in a separate file and use `readLines()` to load them, as we did for `data_description` above.

**Warning:** It is not 100% guaranteed that the LLM will always—or in many cases, ever—obey your instructions, and it can be difficult to predict which instructions will be a problem. So be sure to test extensively each time you change your instructions, and especially, if you change the model you use.

### Use a different LLM provider

By default, querychat uses OpenAI with the default model chosen by `ellmer::chat_openai()`. If you want to use a different model, you can provide an ellmer chat object to the `client` argument of `querychat_init()`.

```r
library(ellmer)
library(purrr)

mtcars_source <- querychat_data_source(mtcars, tbl_name = "cars")

querychat_config <- querychat_init(
  data_source = mtcars_source,
  client = ellmer::chat_anthropic(model = "claude-3-7-sonnet-latest")
)
```

This would use Claude 3.7 Sonnet instead, which would require you to provide an API key.
See the [instructions from Ellmer](https://ellmer.tidyverse.org/reference/chat_anthropic.html) for more information on how to authenticate with different providers.

Alternatively, you can use a provider-model string, which will be passed to `ellmer::chat()`:

```r
querychat_config <- querychat_init(
  data_source = mtcars_source,
  client = "anthropic/claude-3-7-sonnet-latest"
)
```

Or you can set the `querychat.client` R option to a chat object or provider-model string, which will be used as the default client for all querychat apps in your session:

```r
option(querychat.client = "anthropic/claude-3-7-sonnet-latest")
```
