# Build an App

While
[`querychat_app()`](https://posit-dev.github.io/querychat/dev/reference/querychat-convenience.md)
provides a quick way to start exploring data, building bespoke Shiny
apps with querychat unlocks the full power of integrating natural
language data exploration with custom visualizations, layouts, and
interactivity. This guide shows you how to integrate querychat into your
own Shiny applications and leverage its reactive data outputs to create
rich, interactive dashboards.

querychat is a particularly good fit for Shiny apps that have:

1.  **A single data source** (or a set of related tables that can be
    joined)
2.  **Multiple filters** that let users slice and explore the data in
    different ways
3.  **Several visualizations and outputs** that all depend on the same
    filtered data

In these apps, querychat can replace or augment your filtering UI by
allowing users to describe what they want to see in natural language.
Instead of building complex filter controls, users can simply ask
questions like “show me customers from California who spent over \$1000
last quarter” and querychat will generate the appropriate SQL query.

This is especially valuable when:

- Your data has many columns and building a UI for all possible filters
  would be overwhelming
- Users want to explore ad-hoc combinations of filters that you didn’t
  anticipate
- You want to make data exploration more accessible to users who aren’t
  comfortable with traditional filtering UIs

If you have an existing app with a reactive data frame that flows
through multiple outputs, querychat can be a natural addition to provide
an alternative way to filter that data.

## Starter template

Integrating querychat into a Shiny app requires just three steps:

1.  Initialize a `QueryChat` instance with your data
2.  Add the UI component (either `$sidebar()` or `$ui()`)
3.  Use reactive values like `$df()`, `$sql()`, and `$title()` to build
    outputs that respond to user queries

Here’s a starter template demonstrating these steps:

``` r
library(shiny)
library(bslib)
library(querychat)
library(DT)
library(palmerpenguins)

# Step 1: Initialize QueryChat
qc <- QueryChat$new(penguins)

# Step 2: Add UI component
ui <- page_sidebar(
  sidebar = qc$sidebar(),
  card(
    card_header("Data Table"),
    dataTableOutput("table")
  ),
  card(
    fill = FALSE,
    card_header("SQL Query"),
    verbatimTextOutput("sql")
  )
)

# Step 3: Use reactive values in server
server <- function(input, output, session) {
  qc_vals <- qc$server()
  
  output$table <- renderDataTable({
    datatable(qc_vals$df(), fillContainer = TRUE)
  })

  output$sql <- renderText({
    qc_vals$sql() %||% "SELECT * FROM penguins"
  })
}

shinyApp(ui, server)
```

You’ll need to call the `qc$server()` method within your server function
to set up querychat’s reactive behavior, and capture its return value to
access reactive data.

## Deferred data sources

Some data sources, like database connections or reactive calculations,
may need to be created within an active Shiny session. To help support
this, `QueryChat` allows you to initialize without a data source and
provide it later, like this:

``` r
library(shiny)
library(bslib)
library(querychat)

# Global scope - create QueryChat without data source
qc <- QueryChat$new(NULL, "users")

ui <- page_sidebar(
  sidebar = qc$sidebar(),
  card(dataTableOutput("table"))
)

server <- function(input, output, session) {
  # Server scope - create connection with session credentials
  conn <- get_user_connection(session)
  qc_vals <- qc$server(data_source = conn)

  output$table <- renderDataTable({
    qc_vals$df()
  })
}

shinyApp(ui, server)
```

This is also a useful pattern when using something like
[`{pool}`](https://github.com/rstudio/pool) to efficiently manage a pool
of database connections (which we strongly recommend for production
apps).

## Reactives

There are three main reactive values provided by querychat for use in
your app:

### Filtered data

The `$df()` method returns the current filtered and/or sorted data
frame. This updates whenever the user prompts a filtering or sorting
operation through the chat interface (see [Data
updating](https://posit-dev.github.io/querychat/dev/articles/tools.html#data-updating)
for details).

``` r
qc_vals <- qc$server()

output$table <- renderDataTable({
  qc_vals$df()  # Returns filtered/sorted data
})
```

You can use `$df()` to power any output in your app - visualizations,
summary statistics, data tables, and more. When a user asks to “show
only Adelie penguins” or “sort by body mass”, `$df()` automatically
updates, and any outputs that depend on it will re-render.

### SQL query

The `$sql()` method returns the current SQL query as a string. This is
useful for displaying the query to users for transparency and
reproducibility:

``` r
qc_vals <- qc$server()

output$current_query <- renderText({
  qc_vals$sql() %||% "SELECT * FROM penguins"
})
```

You can also use `$sql()` as a setter to programmatically update the
query (see [Programmatic filtering](#programmatic-filtering) below).

### Title

The `$title()` method returns a short description of the current filter,
provided by the LLM when it generates a query. For example, if a user
asks to “show Adelie penguins”, the title might be “Adelie penguins”.

``` r
qc_vals <- qc$server()

output$card_title <- renderText({
  qc_vals$title() %||% "All Data"
})
```

Returns `NULL` when no filter is active. You can also use `$title()` as
a setter to update the title programmatically.

## Custom UI

In the starter template above, we used the `$sidebar()` method for a
simple sidebar layout. In some cases, you might want to place the chat
UI somewhere else in your app layout, or just more fully customize what
goes in the sidebar. The `$ui()` method is designed for this – it
returns the chat component without additional layout wrappers.

For example, you might want to create some additional controls to [reset
filters](#programmatic-filtering) alongside the chat UI:

``` r
library(querychat)
library(palmerpenguins)

qc <- QueryChat$new(penguins)

ui <- page_sidebar(
  sidebar = sidebar(
    qc$ui(),  # Chat component
    actionButton("reset", "Reset Filters", class = "w-100"),
    fillable = TRUE,
    width = 300
  ),
  # Main content here
)
```

**Customizing chat UIs**

See [shinychat](https://posit-dev.github.io/shinychat/r/)’s
[docs](https://posit-dev.github.io/shinychat/r/index.html) to learn more
about customizing the chat UI component returned by `qc$ui()`.

## Data views

Thanks to Shiny’s support for interactive visualizations with packages
like [plotly](https://plotly.com/r/), it’s straightforward to create
rich data views that depend on QueryChat data. Here’s an example of an
app showing both the filtered data and a bar chart depending on that
same data:

`app.R `

``` r
library(shiny)
library(bslib)
library(querychat)
library(DT)
library(plotly)
library(palmerpenguins)

qc <- QueryChat$new(penguins, client = "claude/claude-sonnet-4-5")

ui <- page_sidebar(
  sidebar = qc$sidebar(),
  card(
    card_header("Data Table"),
    dataTableOutput("table")
  ),
  card(
    card_header("Body Mass by Species"),
    plotlyOutput("mass_plot")
  )
)

server <- function(input, output, session) {
  qc_vals <- qc$server()

  output$table <- renderDataTable({
    datatable(qc_vals$df(), fillContainer = TRUE)
  })

  output$mass_plot <- renderPlotly({
    ggplot(qc_vals$df(), aes(x = body_mass_g, fill = species)) +
      geom_density(alpha = 0.4) +
      theme_minimal()
  })
}

shinyApp(ui, server)
```

![Screenshot of a querychat app showing both a data table and a density
plot of body mass by species](images/plotly-data-view.png)

A more useful, but slightly more involved example like the one below
might incorporate other Shiny components like value boxes to summarize
key statistics about the filtered data.

`app.R `

``` r
library(shiny)
library(bslib)
library(DT)
library(plotly)
library(palmerpenguins)
library(dplyr)
library(bsicons)
library(querychat)


qc <- QueryChat$new(penguins)

ui <- page_sidebar(
  title = "Palmer Penguins Analysis",
  class = "bslib-page-dashboard",
  sidebar = qc$sidebar(),
  layout_column_wrap(
    width = 1 / 3,
    fill = FALSE,
    value_box(
      title = "Total Penguins",
      value = textOutput("count"),
      showcase = bs_icon("piggy-bank"),
      theme = "primary"
    ),
    value_box(
      title = "Species Count",
      value = textOutput("species_count"),
      showcase = bs_icon("bookmark-star"),
      theme = "success"
    ),
    value_box(
      title = "Avg Body Mass",
      value = textOutput("avg_mass"),
      showcase = bs_icon("speedometer"),
      theme = "info"
    )
  ),
  layout_columns(
    card(
      card_header(textOutput("table_title")),
      DT::dataTableOutput("data_table")
    ),
    card(
      card_header("Species Distribution"),
      plotlyOutput("species_plot")
    )
  ),
  layout_columns(
    card(
      card_header("Bill Length Distribution"),
      plotlyOutput("bill_length_dist")
    ),
    card(
      card_header("Body Mass by Species"),
      plotlyOutput("mass_by_species")
    )
  )
)

server <- function(input, output, session) {
  qc_vals <- qc$server()

  output$count <- renderText({
    nrow(qc_vals$df())
  })

  output$species_count <- renderText({
    length(unique(qc_vals$df()$species))
  })

  output$avg_mass <- renderText({
    avg <- mean(qc_vals$df()$body_mass_g, na.rm = TRUE)
    paste0(round(avg, 0), "g")
  })

  output$table_title <- renderText({
    qc_vals$title() %||% "All Penguins"
  })

  output$data_table <- DT::renderDataTable({
    DT::datatable(
      qc_vals$df(),
      fillContainer = TRUE,
      options = list(
        scrollX = TRUE,
        pageLength = 10,
        dom = "ti"
      )
    )
  })

  output$species_plot <- renderPlotly({
    plot_ly(
      count(qc_vals$df(), species),
      x = ~species,
      y = ~n,
      type = "bar",
      marker = list(color = c("#1f77b4", "#ff7f0e", "#2ca02c"))
    )
  })

  output$bill_length_dist <- renderPlotly({
    plot_ly(
      qc_vals$df(),
      x = ~bill_length_mm,
      type = "histogram",
      nbinsx = 30,
      marker = list(color = "#1f77b4", opacity = 0.7)
    )
  })

  output$mass_by_species <- renderPlotly({
    plot_ly(
      qc_vals$df(),
      x = ~species,
      y = ~body_mass_g,
      color = ~sex,
      type = "box",
      colors = c("#1f77b4", "#ff7f0e")
    )
  })
}

shinyApp(ui = ui, server = server)
```

## Programmatic updates

querychat’s reactive state can be updated programmatically. For example,
you might want to add a “Reset Filters” button that clears any active
filters and returns the data table to its original state. You can do
this by setting both the SQL query and title to their default values.
This way you don’t have to rely on both the user and LLM to send the
right prompt.

``` r
ui <- page_sidebar(
  sidebar = sidebar(
    qc$ui(),
    hr(),
    actionButton("reset", "Reset Filters")
  ),
  # Main content
  card(dataTableOutput("table"))
)

server <- function(input, output, session) {
  qc_vals <- qc$server()

  output$table <- renderDataTable({
    qc_vals$df()
  })

  observeEvent(input$reset, {
    qc_vals$sql("")
    qc_vals$title(NULL)
  })
}

shinyApp(ui, server)
```

This is equivalent to the user asking the LLM to “reset” or “show all
data”.

## Multiple tables

Currently, you have two options for exploring multiple tables in
querychat:

1.  Join the tables into a single table before passing to querychat
2.  Use multiple querychat instances in the same app

The first option makes it possible to chat with multiple tables inside a
single chat interface, whereas the second option requires a separate
chat interface for each table.

### Multiple filtered tables

We do intend on supporting multiple filtered tables in a future release
– if you’re interested in this feature, please upvote [the relevant
issue](https://github.com/posit-dev/querychat/issues/6)

`app.R `

``` r
library(shiny)
library(bslib)
library(palmerpenguins)
library(titanic)
library(querychat)

qc_penguins <- QueryChat$new(penguins)
qc_titanic <- QueryChat$new(titanic_train)

ui <- page_navbar(
  title = "Multiple Datasets",
  sidebar = sidebar(
    id = "sidebar",
    conditionalPanel(
      "input.navbar == 'Penguins'",
      qc_penguins$ui()
    ),
    conditionalPanel(
      "input.navbar == 'Titanic'",
      qc_titanic$ui()
    )
  ),
  nav_panel(
    "Penguins",
    card(dataTableOutput("penguins_table"))
  ),
  nav_panel(
    "Titanic",
    card(dataTableOutput("titanic_table"))
  ),
  id = "navbar"
)

server <- function(input, output, session) {
  qc_penguins_vals <- qc_penguins$server()
  qc_titanic_vals <- qc_titanic$server()

  output$penguins_table <- renderDataTable({
    qc_penguins_vals$df()
  })

  output$titanic_table <- renderDataTable({
    qc_titanic_vals$df()
  })
}

shinyApp(ui, server)
```

## See also

- [Greet
  users](https://posit-dev.github.io/querychat/dev/articles/greet.md) -
  Create welcoming onboarding experiences
- [Provide
  context](https://posit-dev.github.io/querychat/dev/articles/context.md) -
  Help the LLM understand your data better
- [Tools](https://posit-dev.github.io/querychat/dev/articles/tools.md) -
  Understand what querychat can do under the hood
