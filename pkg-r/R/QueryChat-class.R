#' QueryChat: Interactive Data Querying with Natural Language
#'
#' @description
#' `QueryChat` is an R6 class built on Shiny, shinychat, and ellmer to enable
#' interactive querying of data using natural language. It leverages large
#' language models (LLMs) to translate user questions into SQL queries, execute
#' them against a data source (data frame or database), and various ways of
#' accessing/displaying the results.
#'
#'
#' @details
#' The `QueryChat` class takes your data (a data frame or database connection)
#' as input and provides methods to:
#' - Generate a chat UI for natural language queries (e.g., `$app()`, `$sidebar()`)
#' - Reactively read SQL results in your Shiny app (e.g., `$df()`)
#' - Programmatically get/set the current query and title (e.g., `$sql()`, `$title()`)
#'
#' @section Usage:
#' ```r
#' library(querychat)
#'
#' # Create a QueryChat object
#' qc <- QueryChat$new(mtcars, "mtcars")
#'
#' # Quick start: run a complete app
#' qc$app()
#'
#' # Or build a custom Shiny app
#' ui <- page_sidebar(
#'   qc$sidebar(),
#'   verbatimTextOutput("sql"),
#'   dataTableOutput("data")
#' )
#'
#' server <- function(input, output, session) {
#'   qc$server()
#'
#'   output$sql <- renderText(qc$sql())
#'   output$data <- renderDataTable(qc$df())
#' }
#'
#' shinyApp(ui, server)
#' ```
#'
#' @section Constructor:
#' `QueryChat$new(data_source, table_name, id = NULL, greeting = NULL,
#'                client = NULL, data_description = NULL,
#'                extra_instructions = NULL, prompt_template = NULL)`
#'
#' @section Methods:
#' \describe{
#'   \item{`$new(...)`}{Create a new QueryChat object.}
#'   \item{`$sidebar(...)`}{Create a sidebar UI with chat interface.}
#'   \item{`$ui(...)`}{Create the chat UI component.}
#'   \item{`$server()`}{Initialize server logic (call within server function).}
#'   \item{`$df()`}{Get the current filtered data frame (reactive).}
#'   \item{`$sql(query)`}{Get or set the current SQL query (reactive).}
#'   \item{`$title(value)`}{Get or set the current title (reactive).}
#'   \item{`$app()`}{Create a complete Shiny app with sensible defaults.}
#'   \item{`$generate_greeting(echo)`}{Generate a greeting message using the LLM.}
#'   \item{`$set_system_prompt(...)`}{Update the system prompt.}
#'   \item{`$set_data_source(...)`}{Update the data source.}
#'   \item{`$set_client(...)`}{Update the chat client.}
#' }
#'
#' @field data_source The normalized data source object.
#' @field system_prompt The system prompt string used by the LLM.
#' @field greeting The greeting message displayed to users.
#' @field client The LLM chat client.
#' @field id The module ID for namespacing.
#'
#' @export
#' @examples
#' \dontrun{
#' # Basic usage with a data frame
#' qc <- QueryChat$new(mtcars, "mtcars")
#' app <- qc$app()
#'
#' # With a custom greeting
#' greeting <- "Welcome! Ask me about the mtcars dataset."
#' qc <- QueryChat$new(mtcars, "mtcars", greeting = greeting)
#'
#' # With a specific LLM provider
#' qc <- QueryChat$new(mtcars, "mtcars", client = "anthropic/claude-sonnet-4-5")
#'
#' # Generate a greeting for reuse
#' qc <- QueryChat$new(mtcars, "mtcars")
#' greeting <- qc$generate_greeting(echo = "text")
#' # Save greeting for next time
#' writeLines(greeting, "mtcars_greeting.md")
#' }
QueryChat <- R6::R6Class(
  "QueryChat",
  private = list(
    server_values = NULL
  ),
  public = list(
    data_source = NULL,
    system_prompt = NULL,
    greeting = NULL,
    client = NULL,
    id = NULL,

    #' @description
    #' Create a new QueryChat object.
    #'
    #' @param data_source Either a data.frame or a database connection (e.g., DBI
    #'   connection).
    #' @param table_name A string specifying the table name to use in SQL queries.
    #'   If `data_source` is a data.frame, this is the name to refer to it by in
    #'   queries (typically the variable name). If `data_source` is a database
    #'   connection, this is the name of the table in the database.
    #' @param ... Additional arguments (currently unused).
    #' @param id Optional module ID for the QueryChat instance. If not provided,
    #'   will be auto-generated from `table_name`. The ID is used to namespace
    #'   the Shiny module.
    #' @param greeting Optional initial message to display to users. Can be a
    #'   character string (in Markdown format) or a file path. If not provided,
    #'   a greeting will be generated at the start of each conversation using the
    #'   LLM, which adds latency and cost. Use `$generate_greeting()` to create
    #'   a greeting to save and reuse.
    #' @param client Optional chat client. Can be:
    #'   - An [ellmer::Chat] object
    #'   - A string to pass to [ellmer::chat()] (e.g., `"openai/gpt-4o"`)
    #'   - `NULL` (default): Uses the `querychat.client` option, the
    #'     `QUERYCHAT_CLIENT` environment variable, or defaults to
    #'     [ellmer::chat_openai()]
    #' @param data_description Optional description of the data in plain text or
    #'   Markdown. Can be a string or a file path. This provides context to the
    #'   LLM about what the data represents.
    #' @param extra_instructions Optional additional instructions for the chat
    #'   model in plain text or Markdown. Can be a string or a file path.
    #' @param prompt_template Optional path to or string of a custom prompt
    #'   template file. If not provided, the default querychat template will be
    #'   used. See the package prompts directory for the default template format.
    #' @param auto_cleanup Logical indicating whether to automatically close the
    #'   data source when the Shiny app stops. Default is `TRUE`.
    #'
    #' @return A new `QueryChat` object.
    #'
    #' @examples
    #' \dontrun{
    #' # Basic usage
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' # With options
    #' qc <- QueryChat$new(
    #'   mtcars,
    #'   "mtcars",
    #'   greeting = "Welcome to the mtcars explorer!",
    #'   client = "openai/gpt-4o",
    #'   data_description = "Motor Trend car road tests dataset"
    #' )
    #'
    #' # With database
    #' library(DBI)
    #' conn <- dbConnect(RSQLite::SQLite(), ":memory:")
    #' dbWriteTable(conn, "mtcars", mtcars)
    #' qc <- QueryChat$new(conn, "mtcars")
    #' }
    initialize = function(
      data_source,
      table_name,
      ...,
      id = NULL,
      greeting = NULL,
      client = NULL,
      data_description = NULL,
      extra_instructions = NULL,
      prompt_template = NULL,
      auto_cleanup = TRUE
    ) {
      rlang::check_dots_empty()

      self$data_source <- normalize_data_source(data_source, table_name)      

      # Validate table name
      if (!grepl("^[a-zA-Z][a-zA-Z0-9_]*$", table_name)) {
        rlang::abort(
          "Table name must begin with a letter and contain only letters, numbers, and underscores"
        )
      }

      self$id <- id %||% table_name
      self$client <- normalize_client(client)

      if (!is.null(greeting) && file.exists(greeting)) {
        greeting <- paste(readLines(greeting), collapse = "\n")
      }
      self$greeting <- greeting

      if (is.null(greeting)) {
        rlang::warn(c(
          "No greeting provided; the LLM will be invoked at conversation start to generate one.",
          "*" = "For faster startup, lower cost, and determinism, please save a greeting and pass it to QueryChat$new().",
          "i" = "You can generate a greeting with $generate_greeting()."
        ))
      }

      self$system_prompt <- create_system_prompt(
        self$data_source,
        data_description = data_description,
        extra_instructions = extra_instructions,
        prompt_template = prompt_template
      )

      if (auto_cleanup) {
        # Close the data source when the Shiny app stops (or, if some reason the
        # querychat_init call is within a specific session, when the session ends)
        shiny::onStop(function() {
          message("Closing data source...")
          self$cleanup()
        })
      }
    },

    #' @description
    #' Create a complete Shiny app with sensible defaults.
    #'
    #' This is a convenience method that creates a full Shiny application with:
    #' - A sidebar containing the chat interface
    #' - A card displaying the current SQL query
    #' - A card displaying the filtered data table
    #' - A reset button to clear the query
    #'
    #' @param bookmark_store The bookmarking storage method. Passed to
    #'   [shiny::enableBookmarking()]. If `"url"` or `"server"`, the chat state
    #'   (including current query) will be bookmarked. Default is `"url"`.
    #'
    #' @return A Shiny app object that can be run with [shiny::runApp()] or
    #'   passed to [shiny::shinyApp()].
    #'
    #' @examples
    #' \dontrun{
    #' library(querychat)
    #'
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #' app <- qc$app()
    #'
    #' # Run the app
    #' shiny::runApp(app)
    #'
    #' # Or return from a script
    #' app
    #' }
    app = function(bookmark_store = "url") {
      rlang::check_installed("DT")
      rlang::check_installed("bsicons")

      table_name <- self$data_source$table_name

      ui <- function(req) {
        bslib::page_sidebar(
          title = shiny::HTML(paste0(
            "<span>querychat with <code>",
            table_name,
            "</code></span>"
          )),
          class = "bslib-page-dashboard",
          sidebar = self$sidebar(),
          shiny::useBusyIndicators(pulse = TRUE, spinners = FALSE),
          bslib::card(
            fill = FALSE,
            style = bslib::css(max_height = "33%"),
            bslib::card_header(
              shiny::div(
                class = "hstack",
                shiny::div(
                  bsicons::bs_icon("terminal-fill"),
                  shiny::textOutput("query_title", inline = TRUE)
                ),
                shiny::div(
                  class = "ms-auto",
                  shiny::uiOutput("ui_reset", inline = TRUE)
                )
              )
            ),
            shiny::uiOutput("sql_output")
          ),
          bslib::card(
            bslib::card_header(bsicons::bs_icon("table"), "Data"),
            DT::DTOutput("dt")
          ),
          shiny::actionButton(
            "close_btn",
            label = "",
            class = "btn-close",
            style = "position: fixed; top: 6px; right: 6px;"
          )
        )
      }

      chat <- NULL

      server <- function(input, output, session) {
        self$server()
        chat <<- private$server_values$chat

        output$query_title <- shiny::renderText({
          if (shiny::isTruthy(self$title())) {
            self$title()
          } else {
            "SQL Query"
          }
        })

        output$ui_reset <- shiny::renderUI({
          shiny::req(self$sql())

          shiny::actionButton(
            "reset_query",
            label = "Reset Query",
            class = "btn btn-outline-danger btn-sm lh-1"
          )
        })

        shiny::observeEvent(input$reset_query, label = "on_reset_query", {
          self$sql("")
          self$title(NULL)
        })

        output$dt <- DT::renderDT({
          DT::datatable(self$df())
        })

        output$sql_output <- shiny::renderUI({
          sql <- if (shiny::isTruthy(self$sql())) {
            self$sql()
          } else {
            paste("SELECT * FROM", self$data_source$table_name)
          }

          sql_code <- paste(c("```sql", sql, "```"), collapse = "\n")

          shinychat::output_markdown_stream(
            "sql_code",
            content = sql_code,
            auto_scroll = FALSE,
            width = "100%"
          )
        })

        shiny::observeEvent(input$close_btn, label = "on_close_btn", {
          shiny::stopApp()
        })
      }

      app <- shiny::shinyApp(ui, server, enableBookmarking = bookmark_store)
      tryCatch(shiny::runGadget(app), interrupt = function(cnd) NULL)
      invisible(chat)
    },

    #' @description
    #' Create a sidebar containing the querychat UI.
    #'
    #' This method generates a [bslib::sidebar()] component containing the chat
    #' interface, suitable for use with [bslib::page_sidebar()] or similar layouts.
    #'
    #' @param width Width of the sidebar in pixels. Default is 400.
    #' @param height Height of the sidebar. Default is "100%".
    #' @param ... Additional arguments passed to [bslib::sidebar()].
    #'
    #' @return A [bslib::sidebar()] UI component.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' ui <- page_sidebar(
    #'   qc$sidebar(),
    #'   # Main content here
    #' )
    #' }
    sidebar = function(width = 400, height = "100%", ...) {
      bslib::sidebar(
        width = width,
        height = height,
        class = "querychat-sidebar",
        ...,
        self$ui()
      )
    },

    #' @description
    #' Create the UI for the querychat chat interface.
    #'
    #' This method generates the chat UI component. Typically you'll use
    #' `$sidebar()` instead, which wraps this in a sidebar layout.
    #'
    #' @param ... Additional arguments passed to [shinychat::chat_ui()].
    #'
    #' @return A UI component containing the chat interface.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' ui <- fluidPage(
    #'   qc$ui()
    #' )
    #' }
    ui = function(...) {
      mod_ui(self$id, ...)
    },

    #' @description
    #' Initialize the querychat server logic.
    #'
    #' This method must be called within a Shiny server function. It sets up
    #' the reactive logic for the chat interface and populates the internal
    #' server values that are accessed via `$df()`, `$sql()`, and `$title()`.
    #'
    #' @param session The Shiny session object.
    #'
    #' @return Invisibly returns `NULL`. Access reactive values via `$df()`,
    #'   `$sql()`, and `$title()` methods.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' server <- function(input, output, session) {
    #'   qc$server()
    #'
    #'   output$data <- renderDataTable(qc$df())
    #'   output$query <- renderText(qc$sql())
    #' }
    #' }
    server = function(session = shiny::getDefaultReactiveDomain()) {
      if (is.null(session)) {
        rlang::abort(
          "$server() must be called within a Shiny server function."
        )
      }

      private$server_values <- mod_server(
        self$id,
        data_source = self$data_source,
        system_prompt = self$system_prompt,
        greeting = self$greeting,
        client = self$client
      )

      invisible(NULL)
    },

    #' @description
    #' Get the current filtered data frame.
    #'
    #' This is a reactive expression that returns the data after applying the
    #' current SQL query. If no query has been set, returns the unfiltered data.
    #'
    #' @return A data.frame with the filtered/transformed data.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' server <- function(input, output, session) {
    #'   qc$server()
    #'
    #'   output$table <- renderDataTable({
    #'     qc$df()  # Reactive - will update when query changes
    #'   })
    #' }
    #' }
    df = function() {
      vals <- private$server_values
      if (is.null(vals)) {
        rlang::abort(
          "Must call $server() before accessing $df(). Make sure to call qc$server() within your Shiny server function."
        )
      }
      vals$df()
    },

    #' @description
    #' Get or set the current SQL query.
    #'
    #' This method provides both getter and setter functionality for the SQL
    #' query. When called without arguments, it returns the current query.
    #' When called with a query string, it sets the query and returns whether
    #' the query changed.
    #'
    #' @param query Optional SQL query string. If provided, sets the current
    #'   query to this value. If `NULL` (default), returns the current query.
    #'
    #' @return
    #' - When `query = NULL` (getter): Returns the current SQL query as a string
    #'   (may be an empty string `""` if no query has been set).
    #' - When `query` is provided (setter): Returns `TRUE` if the query was
    #'   changed to a new value, `FALSE` if it was the same as the current value.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' server <- function(input, output, session) {
    #'   qc$server()
    #'
    #'   # Get current query
    #'   output$current_query <- renderText({
    #'     qc$sql()
    #'   })
    #'
    #'   # Set query programmatically
    #'   observeEvent(input$filter_button, {
    #'     qc$sql("SELECT * FROM mtcars WHERE cyl = 6")
    #'   })
    #' }
    #' }
    sql = function(query = NULL) {
      vals <- private$server_values
      if (is.null(vals)) {
        rlang::abort(
          "Must call $server() before accessing $sql(). Make sure to call qc$server() within your Shiny server function."
        )
      }

      if (is.null(query)) {
        vals$sql()
      } else {
        old_query <- shiny::isolate(vals$sql())
        vals$sql(query)
        return(!identical(old_query, query))
      }
    },

    #' @description
    #' Get or set the current title.
    #'
    #' The title is a short description of the current query that the LLM
    #' provides whenever it generates a new SQL query. It can be used as a
    #' status string for the data dashboard.
    #'
    #' @param value Optional title string. If provided, sets the current title
    #'   to this value. If `NULL` (default), returns the current title.
    #'
    #' @return
    #' - When `value = NULL` (getter): Returns the current title as a string,
    #'   or `NULL` if no title has been set (because no SQL query has been set).
    #' - When `value` is provided (setter): Returns `TRUE` if the title was
    #'   changed to a new value, `FALSE` if it was the same as the current value.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' server <- function(input, output, session) {
    #'   qc$server()
    #'
    #'   # Get current title
    #'   output$title <- renderText({
    #'     qc$title() %||% "No Query"
    #'   })
    #'
    #'   # Set title programmatically
    #'   observeEvent(input$set_title, {
    #'     qc$title("Filtered Cars")
    #'   })
    #' }
    #' }
    title = function(value = NULL) {
      vals <- private$server_values
      if (is.null(vals)) {
        rlang::abort(
          "Must call $server() before accessing $title(). Make sure to call qc$server() within your Shiny server function."
        )
      }

      if (is.null(value)) {
        vals$title()
      } else {
        old_value <- shiny::isolate(vals$title())
        vals$title(value)
        return(!identical(old_value, value))
      }
    },

    #' @description
    #' Generate a welcome greeting for the chat.
    #'
    #' By default, `QueryChat$new()` generates a greeting at the start of every
    #' new conversation, which is convenient for getting started and development,
    #' but also might add unnecessary latency and cost. Use this method to
    #' generate a greeting once and save it for reuse.
    #'
    #' @param echo Whether to print the greeting to the console. Options are
    #'   `"none"` (default, no output) or `"text"` (print to console).
    #'
    #' @return The greeting string in Markdown format.
    #'
    #' @examples
    #' \dontrun{
    #' # Create QueryChat object
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' # Generate a greeting and save it
    #' greeting <- qc$generate_greeting(echo = "text")
    #' writeLines(greeting, "mtcars_greeting.md")
    #'
    #' # Later, use the saved greeting
    #' qc2 <- QueryChat$new(mtcars, "mtcars", greeting = "mtcars_greeting.md")
    #' }
    generate_greeting = function(echo = c("none", "output")) {
      echo <- match.arg(echo)

      chat <- self$client$clone()
      chat$set_system_prompt(self$system_prompt)
      chat$set_turns(list())

      prompt <- "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list."
      as.character(chat$chat(prompt, echo = echo))
    },

    #' @description
    #' Clean up resources associated with the data source.
    #'
    #' This method releases any resources (e.g., database connections)
    #' associated with the data source. Call this when you are done using
    #' the QueryChat object to avoid resource leaks.
    #' 
    #' Note: If `auto_cleanup` was set to `TRUE` in the constructor,
    #'  this will be called automatically when the Shiny app stops.
    #'
    #' @return Invisibly returns `NULL`. Resources are cleaned up internally.
    cleanup = function() {
      cleanup_source(self$data_source)
    },

    #' @description
    #' Update the system prompt.
    #'
    #' This method regenerates the system prompt based on the data source's
    #' schema and optional additional context and instructions. Use this when
    #' you want to customize how the LLM interprets and queries your data.
    #'
    #' Note: This method is for parametrized system prompt generation only. To
    #' set a fully custom system prompt string, access the `$system_prompt`
    #' field directly (not recommended for typical usage).
    #'
    #' @param data_source A `querychat_data_source` object to generate schema
    #'   information from. Typically you'll pass the same data source used in
    #'   the constructor, but you can also pass a different one.
    #' @param data_description Optional description of the data, in plain text
    #'   or Markdown format. Can be a string or file path.
    #' @param extra_instructions Optional additional instructions for the chat
    #'   model, in plain text or Markdown format. Can be a string or file path.
    #' @param categorical_threshold Threshold for determining if a column is
    #'   categorical based on the number of unique values. Default is 10.
    #' @param prompt_template Optional path to or string of a custom prompt
    #'   template. If not provided, the default querychat template will be used.
    #'
    #' @return Invisibly returns `NULL`. The system prompt is updated internally.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' # Update with additional context
    #' qc$set_system_prompt(
    #'   qc$data_source,
    #'   data_description = "Motor Trend car data from 1974",
    #'   extra_instructions = "Always order results by mpg descending"
    #' )
    #' }
    set_system_prompt = function(
      data_source,
      data_description = NULL,
      extra_instructions = NULL,
      categorical_threshold = 10,
      prompt_template = NULL
    ) {
      self$system_prompt <- create_system_prompt(
        data_source,
        data_description = data_description,
        extra_instructions = extra_instructions,
        categorical_threshold = categorical_threshold,
        prompt_template = prompt_template
      )
      invisible(NULL)
    },

    #' @description
    #' Set a new data source for the QueryChat object.
    #'
    #' This method updates the data source that queries will be executed against.
    #' Note that this does not automatically update the system prompt - you may
    #' want to call `$set_system_prompt()` after changing the data source.
    #'
    #' @param data_source Either a data.frame or a database connection.
    #' @param table_name The name to use for the table in SQL queries.
    #'
    #' @return Invisibly returns `NULL`. The data source is updated internally.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' # Switch to a different dataset
    #' qc$set_data_source(iris, "iris")
    #' qc$set_system_prompt(qc$data_source)  # Update prompt to match new data
    #' }
    set_data_source = function(data_source, table_name) {
      self$data_source <- normalize_data_source(data_source, table_name)
      invisible(NULL)
    },

    #' @description
    #' Set a new chat client for the QueryChat object.
    #'
    #' This method updates the LLM client used for generating SQL queries and
    #' responses. The client can be an [ellmer::Chat] object, a string describing
    #' the model, or a function that returns a Chat object.
    #'
    #' @param client The new chat client. Can be:
    #'   - An [ellmer::Chat] object
    #'   - A string to pass to [ellmer::chat()] (e.g., `"openai/gpt-4o"`)
    #'   - A function that returns an [ellmer::Chat] object
    #'
    #' @return Invisibly returns `NULL`. The client is updated internally.
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars, "mtcars")
    #'
    #' # Switch to a different model
    #' qc$set_client("anthropic/claude-sonnet-4-5")
    #' }
    set_client = function(client) {
      self$client <- normalize_client(client)
      invisible(NULL)
    }
  )
)


normalize_data_source <- function(data_source, table_name) {
  if (is_data_source(data_source)) {
    return(data_source)
  } else {
    create_data_source(data_source, table_name)
  }
}