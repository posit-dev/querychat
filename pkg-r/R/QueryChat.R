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
#' - Initialize server logic that returns session-specific reactive values (via `$server()`)
#' - Access reactive data, SQL queries, and titles through the returned server values
#'
#' @section Usage:
#' ```r
#' library(querychat)
#'
#' # Create a QueryChat object
#' qc <- QueryChat$new(mtcars)
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
#'   qc_vals <- qc$server()
#'
#'   output$sql <- renderText(qc_vals$sql())
#'   output$data <- renderDataTable(qc_vals$df())
#' }
#'
#' shinyApp(ui, server)
#' ```
#'
#' @export
#' @examples
#' \dontrun{
#' # Basic usage with a data frame
#' qc <- QueryChat$new(mtcars)
#' app <- qc$app()
#'
#' # With a custom greeting
#' greeting <- "Welcome! Ask me about the mtcars dataset."
#' qc <- QueryChat$new(mtcars, greeting = greeting)
#'
#' # With a specific LLM provider
#' qc <- QueryChat$new(mtcars, client = "anthropic/claude-sonnet-4-5")
#'
#' # Generate a greeting for reuse
#' qc <- QueryChat$new(mtcars)
#' greeting <- qc$generate_greeting(echo = "text")
#' # Save greeting for next time
#' writeLines(greeting, "mtcars_greeting.md")
#' }
QueryChat <- R6::R6Class(
  "QueryChat",
  private = list(
    server_values = NULL,
    .data_source = NULL,
    .client = NULL
  ),
  public = list(
    #' @field greeting The greeting message displayed to users.
    greeting = NULL,
    #' @field id The module ID for namespacing.
    id = NULL,

    #' @description
    #' Create a new QueryChat object.
    #'
    #' @param data_source Either a data.frame or a database connection (e.g., DBI
    #'   connection).
    #' @param table_name A string specifying the table name to use in SQL queries.
    #'   If `data_source` is a data.frame, this is the name to refer to it by in
    #'   queries (typically the variable name). If not provided, will be inferred
    #'   from the variable name for data.frame inputs. For database connections,
    #'   this parameter is required.
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
    #' @param categorical_threshold For text columns, the maximum number of unique
    #'   values to consider as a categorical variable. Default is 20.
    #' @param extra_instructions Optional additional instructions for the chat
    #'   model in plain text or Markdown. Can be a string or a file path.
    #' @param prompt_template Optional path to or string of a custom prompt
    #'   template file. If not provided, the default querychat template will be
    #'   used. See the package prompts directory for the default template format.
    #' @param cleanup Whether or not to automatically run `$cleanup()` when the
    #'   Shiny session/app stops. By default, cleanup only occurs if `QueryChat`
    #'   gets created within a Shiny session. Set to `TRUE` to always clean up,
    #'   or `FALSE` to never clean up automatically.
    #'
    #' @return A new `QueryChat` object.
    #'
    #' @examples
    #' \dontrun{
    #' # Basic usage
    #' qc <- QueryChat$new(mtcars)
    #'
    #' # With options
    #' qc <- QueryChat$new(
    #'   mtcars,
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
      table_name = rlang::missing_arg(),
      ...,
      id = NULL,
      greeting = NULL,
      client = NULL,
      data_description = NULL,
      categorical_threshold = 20,
      extra_instructions = NULL,
      prompt_template = NULL,
      cleanup = NA
    ) {
      rlang::check_dots_empty()

      if (rlang::is_missing(table_name) && is.data.frame(data_source)) {
        table_name <- deparse1(substitute(data_source))
      }

      private$.data_source <- normalize_data_source(data_source, table_name)

      # Validate table name
      if (!grepl("^[a-zA-Z][a-zA-Z0-9_]*$", table_name)) {
        cli::cli_abort(
          "Table name must begin with a letter and contain only letters, numbers, and underscores"
        )
      }

      self$id <- id %||% table_name

      if (!is.null(greeting) && file.exists(greeting)) {
        greeting <- paste(readLines(greeting), collapse = "\n")
      }
      self$greeting <- greeting

      prompt <- create_system_prompt(
        private$.data_source,
        data_description = data_description,
        categorical_threshold = categorical_threshold,
        extra_instructions = extra_instructions,
        prompt_template = prompt_template
      )

      # Fork and empty chat now so the per-session forks are fast
      client <- as_querychat_client(client)
      private$.client <- client$clone()
      private$.client$set_turns(list())
      private$.client$set_system_prompt(prompt)

      # By default, only close automatically if a Shiny session is active
      if (is.na(cleanup)) {
        cleanup <- !is.null(shiny::getDefaultReactiveDomain())
      }

      if (cleanup) {
        shiny::onStop(function() {
          cli::cli_inform("Closing data source...")
          self$cleanup()
        })
      }
    },

    #' @description
    #' Create and run a Shiny gadget for chatting with data
    #'
    #' Runs a Shiny gadget (designed for interactive use) that provides
    #' a complete interface for chatting with your data using natural language.
    #' If you're looking to deploy this app or run it through some other means,
    #' see `$app_obj()`.
    #'
    #' @param ... Arguments passed to `$app_obj()`.
    #' @param bookmark_store The bookmarking storage method. Passed to
    #'   [shiny::enableBookmarking()]. If `"url"` or `"server"`, the chat state
    #'   (including current query) will be bookmarked. Default is `"url"`.
    #'
    #' @return Invisibly returns a list of session-specific values:
    #'  - `df`: The final filtered data frame
    #'  - `sql`: The final SQL query string
    #'  - `title`: The final title
    #'  - `client`: The session-specific chat client instance
    #'
    #' @examples
    #' \dontrun{
    #' library(querychat)
    #'
    #' qc <- QueryChat$new(mtcars)
    #' qc$app()
    #' }
    #'
    app = function(..., bookmark_store = "url") {
      app <- self$app_obj(..., bookmark_store = bookmark_store)
      vals <- tryCatch(shiny::runGadget(app), interrupt = function(cnd) NULL)
      invisible(vals)
    },

    #' @description
    #' A streamlined Shiny app for chatting with data
    #'
    #' Creates a Shiny app designed for chatting with data, with:
    #' - A sidebar containing the chat interface
    #' - A card displaying the current SQL query
    #' - A card displaying the filtered data table
    #' - A reset button to clear the query
    #'
    #' @param ... Additional arguments (currently unused).
    #' @param bookmark_store The bookmarking storage method. Passed to
    #'  [shiny::enableBookmarking()]. If `"url"` or `"server"`, the chat state
    #'  (including current query) will be bookmarked. Default is `"url"`.
    #'
    #' @return A Shiny app object that can be run with `shiny::runApp()`.
    #'
    #' @examples
    #' \dontrun{
    #' library(querychat)
    #'
    #' qc <- QueryChat$new(mtcars)
    #' app <- qc$app_obj()
    #' shiny::runApp(app)
    #' }
    #'
    app_obj = function(..., bookmark_store = "url") {
      rlang::check_installed("DT")
      rlang::check_installed("bsicons")
      rlang::check_dots_empty()

      table_name <- private$.data_source$table_name

      ui <- function(req) {
        bslib::page_sidebar(
          title = shiny::HTML(sprintf(
            "<span>querychat with <code>%s</code></span>",
            table_name
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
            full_screen = TRUE,
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

      server <- function(input, output, session) {
        # Enable bookmarking if bookmark_store is enabled
        enable_bookmarking <- bookmark_store %in% c("url", "server")
        qc_vals <- self$server(enable_bookmarking = enable_bookmarking)

        output$query_title <- shiny::renderText({
          if (shiny::isTruthy(qc_vals$title())) {
            qc_vals$title()
          } else {
            "SQL Query"
          }
        })

        output$ui_reset <- shiny::renderUI({
          shiny::req(qc_vals$sql())

          shiny::actionButton(
            "reset_query",
            label = "Reset Query",
            class = "btn btn-outline-danger btn-sm lh-1"
          )
        })

        shiny::observeEvent(input$reset_query, label = "on_reset_query", {
          qc_vals$sql("")
          qc_vals$title(NULL)
        })

        output$dt <- DT::renderDT({
          DT::datatable(
            qc_vals$df(),
            fillContainer = TRUE,
            options = list(pageLength = 25, scrollX = TRUE)
          )
        })

        output$sql_output <- shiny::renderUI({
          sql <- if (shiny::isTruthy(qc_vals$sql())) {
            qc_vals$sql()
          } else {
            paste("SELECT * FROM", table_name)
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
          shiny::stopApp(list(
            df = qc_vals$df(),
            sql = qc_vals$sql(),
            title = qc_vals$title(),
            client = qc_vals$client
          ))
        })
      }

      shiny::shinyApp(ui, server, enableBookmarking = bookmark_store)
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
    #' qc <- QueryChat$new(mtcars)
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
    #' qc <- QueryChat$new(mtcars)
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
    #' the reactive logic for the chat interface and returns session-specific
    #' reactive values.
    #'
    #' @param enable_bookmarking Whether to enable bookmarking for the chat
    #'   state. Default is `FALSE`. When enabled, the chat state (including
    #'   current query, title, and chat history) will be saved and restored
    #'   with Shiny bookmarks. This requires that the Shiny app has bookmarking
    #'   enabled via `shiny::enableBookmarking()` or the `enableBookmarking`
    #'   parameter of `shiny::shinyApp()`.
    #' @param session The Shiny session object.
    #'
    #' @return A list containing session-specific reactive values and the chat
    #'   client with the following elements:
    #'   - `df`: Reactive expression returning the current filtered data frame
    #'   - `sql`: Reactive value for the current SQL query string
    #'   - `title`: Reactive value for the current title
    #'   - `client`: The session-specific chat client instance
    #'
    #' @examples
    #' \dontrun{
    #' qc <- QueryChat$new(mtcars)
    #'
    #' server <- function(input, output, session) {
    #'   qc_vals <- qc$server(enable_bookmarking = TRUE)
    #'
    #'   output$data <- renderDataTable(qc_vals$df())
    #'   output$query <- renderText(qc_vals$sql())
    #'   output$title <- renderText(qc_vals$title() %||% "No Query")
    #' }
    #' }
    server = function(
      enable_bookmarking = FALSE,
      session = shiny::getDefaultReactiveDomain()
    ) {
      if (is.null(session)) {
        cli::cli_abort(
          "$server() must be called within a Shiny server function."
        )
      }

      mod_server(
        self$id,
        data_source = private$.data_source,
        greeting = self$greeting,
        client = private$.client,
        enable_bookmarking = enable_bookmarking
      )
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
    #'   `"none"` (default, no output) or `"output"` (print to console).
    #'
    #' @return The greeting string in Markdown format.
    #'
    #' @examples
    #' \dontrun{
    #' # Create QueryChat object
    #' qc <- QueryChat$new(mtcars)
    #'
    #' # Generate a greeting and save it
    #' greeting <- qc$generate_greeting()
    #' writeLines(greeting, "mtcars_greeting.md")
    #'
    #' # Later, use the saved greeting
    #' qc2 <- QueryChat$new(mtcars, greeting = "mtcars_greeting.md")
    #' }
    generate_greeting = function(echo = c("none", "output")) {
      echo <- match.arg(echo)

      chat <- private$.client$clone()
      chat$set_turns(list())

      as.character(chat$chat(GREETING_PROMPT, echo = echo))
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
      if (!is.null(private$.data_source)) {
        private$.data_source$cleanup()
      }
      invisible(NULL)
    }
  ),
  active = list(
    #' @field system_prompt Get the system prompt.
    system_prompt = function() {
      private$.client$get_system_prompt()
    },

    #' @field data_source Get the current data source.
    data_source = function() {
      private$.data_source
    }
  )
)

#' QueryChat convenience functions
#'
#' Convenience functions for wrapping [QueryChat] creation (i.e., `querychat()`)
#' and app launching (i.e., `querychat_app()`).
#'
#' @param data_source Either a data.frame or a database connection (e.g., DBI
#'   connection).
#' @param table_name A string specifying the table name to use in SQL queries.
#'   If `data_source` is a data.frame, this is the name to refer to it by in
#'   queries (typically the variable name). If not provided, will be inferred
#'   from the variable name for data.frame inputs. For database connections,
#'   this parameter is required.
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
#' @param categorical_threshold For text columns, the maximum number of unique
#'   values to consider as a categorical variable. Default is 20.
#' @param extra_instructions Optional additional instructions for the chat
#'   model in plain text or Markdown. Can be a string or a file path.
#' @param prompt_template Optional path to or string of a custom prompt
#'   template file. If not provided, the default querychat template will be
#'   used. See the package prompts directory for the default template format.
#' @param cleanup Whether or not to automatically run `$cleanup()` when the
#'   Shiny session/app stops. By default, cleanup only occurs if `QueryChat`
#'   gets created within a Shiny session. Set to `TRUE` to always clean up,
#'   or `FALSE` to never clean up automatically.
#'
#' @return A `QueryChat` object. See [QueryChat] for available methods.
#'
#' @rdname querychat-convenience
#'
#' @export
#' @examples
#' \dontrun{
#' # Quick start - chat with mtcars dataset in one line
#' querychat_app(mtcars)
#'
#' # Add options
#' querychat_app(
#'   mtcars,
#'   greeting = "Welcome to the mtcars explorer!",
#'   client = "openai/gpt-4o"
#' )
#'
#' # Chat with a database table (table_name required)
#' library(DBI)
#' conn <- dbConnect(RSQLite::SQLite(), ":memory:")
#' dbWriteTable(conn, "mtcars", mtcars)
#' querychat_app(conn, "mtcars")
#'
#' # Create QueryChat class object
#' qc <- querychat(mtcars)
#'
#' # Run the app later
#' qc$app()
#'
#' }
querychat <- function(
  data_source,
  table_name = rlang::missing_arg(),
  ...,
  id = NULL,
  greeting = NULL,
  client = NULL,
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  cleanup = NA
) {
  if (rlang::is_missing(table_name) && is.data.frame(data_source)) {
    table_name <- deparse1(substitute(data_source))
  }

  QueryChat$new(
    data_source = data_source,
    table_name = table_name,
    ...,
    id = id,
    greeting = greeting,
    client = client,
    data_description = data_description,
    categorical_threshold = categorical_threshold,
    extra_instructions = extra_instructions,
    prompt_template = prompt_template,
    cleanup = cleanup
  )
}

#' @rdname querychat-convenience
#' @param bookmark_store The bookmarking storage method. Passed to
#'   [shiny::enableBookmarking()]. If `"url"` or `"server"`, the chat state
#'   (including current query) will be bookmarked. Default is `"url"`.
#' @return Invisibly returns the chat object after the app stops.
#'
#' @export
querychat_app <- function(
  data_source,
  table_name = rlang::missing_arg(),
  ...,
  id = NULL,
  greeting = NULL,
  client = NULL,
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  cleanup = TRUE,
  bookmark_store = "url"
) {
  if (rlang::is_missing(table_name) && is.data.frame(data_source)) {
    table_name <- deparse1(substitute(data_source))
  }

  qc <- QueryChat$new(
    data_source = data_source,
    table_name = table_name,
    ...,
    id = id,
    greeting = greeting,
    client = client,
    data_description = data_description,
    categorical_threshold = categorical_threshold,
    extra_instructions = extra_instructions,
    prompt_template = prompt_template,
    cleanup = cleanup
  )

  qc$app(bookmark_store = bookmark_store)
}

normalize_data_source <- function(data_source, table_name) {
  if (is_data_source(data_source)) {
    return(data_source)
  }

  if (is.data.frame(data_source)) {
    return(DataFrameSource$new(data_source, table_name))
  }

  if (inherits(data_source, "DBIConnection")) {
    return(DBISource$new(data_source, table_name))
  }

  cli::cli_abort(
    paste0(
      "`data_source` must be a DataSource, data.frame, or DBIConnection. ",
      "Got: ",
      class(data_source)[1]
    )
  )
}
