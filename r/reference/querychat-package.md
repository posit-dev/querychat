# querychat: Chat with Your Data Using Natural Language

querychat provides an interactive chat interface for querying data using
natural language. It translates your questions into SQL queries,
executes them against your data, and displays the results. The package
works with both data frames and database connections.

## Quick Start

The easiest way to get started is with the
[QueryChat](https://posit-dev.github.io/querychat/reference/QueryChat.md)
R6 class:

    library(querychat)

    # Create a QueryChat object (table name inferred from variable)
    qc <- QueryChat$new(mtcars)

    # Option 1: Run a complete app with sensible defaults
    qc$app()

    # Option 2: Build a custom Shiny app
    ui <- page_sidebar(
      qc$sidebar(),
      dataTableOutput("data")
    )

    server <- function(input, output, session) {
      qc$server()
      output$data <- renderDataTable(qc$df())
    }

    shinyApp(ui, server)

## Key Features

- **Natural language queries**: Ask questions in plain English

- **SQL transparency**: See the generated SQL queries

- **Multiple data sources**: Works with data frames and database
  connections

- **Customizable**: Add data descriptions, extra instructions, and
  custom greetings

- **LLM agnostic**: Works with OpenAI, Anthropic, Google, and other
  providers via ellmer

## Main Components

- [QueryChat](https://posit-dev.github.io/querychat/reference/QueryChat.md):
  The main R6 class for creating chat interfaces

- [DataSource](https://posit-dev.github.io/querychat/reference/DataSource.md),
  [DataFrameSource](https://posit-dev.github.io/querychat/reference/DataFrameSource.md),
  [DBISource](https://posit-dev.github.io/querychat/reference/DBISource.md):
  R6 classes for data sources

## Examples

To see examples included with the package, run:

    shiny::runExample(package = "querychat")

This provides a list of available examples. To run a specific example,
like '01-hello-app', use:

    shiny::runExample("01-hello-app", package = "querychat")

## See also

Useful links:

- <https://posit-dev.github.io/querychat/pkg-r>

- <https://posit-dev.github.io/querychat>

- <https://github.com/posit-dev/querychat>

- Report bugs at <https://github.com/posit-dev/querychat/issues>

## Author

**Maintainer**: Garrick Aden-Buie <garrick@posit.co>
([ORCID](https://orcid.org/0000-0002-7111-0077))

Authors:

- Joe Cheng <joe@posit.co> \[conceptor\]

- Carson Sievert <carson@posit.co>
  ([ORCID](https://orcid.org/0000-0002-4958-2844))

Other contributors:

- Posit Software, PBC \[copyright holder, funder\]
