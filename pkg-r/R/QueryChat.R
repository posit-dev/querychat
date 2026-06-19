#' QueryChat: Interactive Data Querying with Natural Language
#'
#' @description
#' `QueryChat` is an R6 class built on Shiny, shinychat, and ellmer to enable
#' interactive querying of data using natural language. It leverages large
#' language models (LLMs) to translate user questions into SQL queries, execute
#' them against a data source (data frame or database), and various ways of
#' accessing/displaying the results.
#'
#' The `QueryChat` class takes your data (a data frame or database connection)
#' as input and provides methods to:
#'
#' - Generate a chat UI for natural language queries (e.g., `$app()`,
#'   `$sidebar()`)
#' - Initialize server logic that returns session-specific reactive values (via
#'   `$server()`)
#' - Access reactive data, SQL queries, and titles through the returned server
#'   values (use `$table("name")` for multi-table access)
#'
#' @section Usage in Shiny Apps:
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
#' @examplesIf rlang::is_installed("duckdb") || rlang::is_installed("RSQLite")
#' # Basic usage with a data frame
#' qc <- QueryChat$new(mtcars)
#' \dontrun{
#' app <- qc$app()
#' }
#'
#' # With a custom greeting
#' greeting <- "Welcome! Ask me about the mtcars dataset."
#' qc <- QueryChat$new(mtcars, greeting = greeting)
#'
#' # With a specific LLM provider
#' qc <- QueryChat$new(mtcars, client = "anthropic/claude-sonnet-4-5")
#'
#' # Generate a greeting for reuse (requires internet/API access)
#' \dontrun{
#' qc <- QueryChat$new(mtcars)
#' greeting <- qc$generate_greeting(echo = "text")
#' # Save greeting for next time
#' writeLines(greeting, "mtcars_greeting.md")
#' }
#'
#' # Or specify greeting and additional options at initialization
#' qc <- QueryChat$new(
#'   mtcars,
#'   greeting = "Welcome to the mtcars explorer!",
#'   client = "openai/gpt-4o",
#'   data_description = "Motor Trend car road tests dataset"
#' )
#'
#' @examplesIf rlang::is_installed("RSQLite")
#' # Create a QueryChat object from a database connection
#' # 1. Set up the database connection
#' con <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
#'
#' # 2. (For this demo) Create a table in the database
#' DBI::dbWriteTable(con, "mtcars", mtcars)
#'
#' # 3. Pass the connection and table name to `QueryChat`
#' qc <- QueryChat$new(con, "mtcars")
#'
#' @export
QueryChat <- R6::R6Class(
  "QueryChat",
  private = list(
    .data_sources = list(),
    .deferred_table_name = NULL,
    .query_executor = NULL,
    .server_initialized = FALSE,
    .client_spec = NULL,
    .client_console = NULL,
    .system_prompt = NULL,
    # Store init parameters for deferred system prompt building
    .prompt_template = NULL,
    .data_description = NULL,
    .data_description_mode = "empty", # "supplied", "inferred", or "empty"
    .extra_instructions = NULL,
    .categorical_threshold = NULL,
    .data_dicts = list(),

    require_initialized = function(method_name) {
      if (length(private$.data_sources) == 0) {
        cli::cli_abort(
          "{.arg data_source} must be set before calling {.fn ${method_name}}.
           Either pass {.arg data_source} to {.fn $new}, or call {.fn $add_table}."
        )
      }
    },

    auto_fill_data_description = function() {
      if (length(private$.data_sources) != 1) {
        return()
      }
      if (private$.data_description_mode == "inferred") {
        private$.data_description <- NULL
        private$.data_description_mode <- "empty"
      }
      if (private$.data_description_mode == "empty") {
        desc <- private$.data_sources[[1]]$get_data_description()
        if (nzchar(desc %||% "")) {
          private$.data_description <- desc
          private$.data_description_mode <- "inferred"
        }
      }
    },

    build_system_prompt = function(data_sources = NULL) {
      sources <- data_sources %||% private$.data_sources
      if (length(sources) == 0) {
        cli::cli_abort("Cannot build system prompt without data sources")
      }

      prompt_template <- private$.prompt_template %||%
        system.file("prompts", "prompt.md", package = "querychat")

      private$.system_prompt <- QueryChatSystemPrompt$new(
        prompt_template = prompt_template,
        data_sources = sources,
        data_description = private$.data_description,
        extra_instructions = private$.extra_instructions,
        categorical_threshold = private$.categorical_threshold,
        data_dicts = private$.data_dicts
      )
    },

    create_session_client = function(
      client_spec = NULL,
      tools = NA,
      session = NULL,
      update_dashboard = function(query, title, table) {
      },
      reset_dashboard = function(table) {
      },
      visualize = function(data) {
      }
    ) {
      spec <- client_spec %||% private$.client_spec
      chat <- as_querychat_client(spec)
      chat <- chat$clone()
      chat$set_turns(list())

      if (is_na(tools)) {
        tools <- self$tools
      }

      chat$set_system_prompt(private$.system_prompt$render(tools = tools))

      if (is.null(tools)) {
        return(chat)
      }

      # Build executor lazily
      if (is.null(private$.query_executor)) {
        private$.query_executor <- build_query_executor(private$.data_sources)
      }
      executor <- private$.query_executor
      tbl_names <- names(private$.data_sources)

      # Always register get_schema tool
      chat$register_tool(
        tool_get_schema(
          private$.data_dicts,
          executor,
          tbl_names,
          private$.categorical_threshold
        )
      )

      if ("update" %in% tools) {
        chat$register_tool(
          tool_update_dashboard(
            executor,
            tbl_names,
            update_fn = update_dashboard
          )
        )
        chat$register_tool(
          tool_reset_dashboard(reset_dashboard, table_names = tbl_names)
        )
      }

      if ("query" %in% tools) {
        chat$register_tool(
          tool_query(executor, multi_table = length(tbl_names) > 1)
        )
      }

      if ("visualize" %in% tools) {
        rlang::check_installed(
          "ggsql",
          reason = "for visualization support."
        )
        chat$register_tool(
          tool_visualize_dashboard(
            executor,
            session = session,
            update_fn = visualize,
            has_tool_query = "query" %in% tools
          )
        )
      }

      chat
    }
  ),
  public = list(
    #' @field greeting The greeting message displayed to users.
    greeting = NULL,
    #' @field id ID for the QueryChat instance.
    id = NULL,
    #' @field id_override Whether the ID was explicitly set by the user.
    id_override = NULL,
    #' @field tools The allowed tools for the chat client.
    tools = c("filter", "query"),

    #' @description
    #' Create a new QueryChat object.
    #'
    #' @param data_source Either a data.frame, a database connection (e.g., DBI
    #'   connection), or `NULL` to defer setting the data source until later.
    #'   When `NULL`, the data source must be added via `$add_table()` or passed
    #'   to `$server()` before calling methods that require data access.
    #' @param table_name A string specifying the table name to use in SQL
    #'   queries. If `data_source` is a data.frame, this is the name to refer to
    #'   it by in queries (typically the variable name). If not provided, will
    #'   be inferred from the variable name for data.frame inputs. For database
    #'   connections or `NULL` data sources, this parameter is required.
    #' @param ... Additional arguments (currently unused).
    #' @param id Optional module ID for the QueryChat instance. If not provided,
    #'   will be auto-generated from `table_name`. The ID is used to namespace
    #'   the Shiny module.
    #' @param greeting Optional initial message to display to users. Can be a
    #'   character string (in Markdown format) or a file path. If not provided,
    #'   a greeting will be generated at the start of each conversation using
    #'   the LLM, which adds latency and cost. Use `$generate_greeting()` to
    #'   create a greeting to save and reuse.
    #' @param client Optional chat client. Can be:
    #'   - An [ellmer::Chat] object
    #'   - A string to pass to [ellmer::chat()] (e.g., `"openai/gpt-4o"`)
    #'   - `NULL` (default): Uses the `querychat.client` option, the
    #'     `QUERYCHAT_CLIENT` environment variable, or defaults to
    #'     [ellmer::chat_openai()]
    #' @param tools Which querychat tools to include in the chat client, by
    #'   default. `"filter"` includes the tools for filtering and resetting the
    #'   dashboard and `"query"` includes the tool for executing SQL queries.
    #'   Use `tools = "filter"` when you only want the dashboard filtering tools,
    #'   or when you want to disable the querying tool entirely to prevent the
    #'   LLM from seeing any of the data in your dataset. The legacy name
    #'   `"update"` is still accepted as an alias for `"filter"`.
    #' @param data_description Optional description of the data in plain text or
    #'   Markdown. Can be a string or a file path. This provides context to the
    #'   LLM about what the data represents.
    #' @param categorical_threshold For text columns, the maximum number of
    #'   unique values to consider as a categorical variable. Default is 20.
    #' @param extra_instructions Optional additional instructions for the chat
    #'   model in plain text or Markdown. Can be a string or a file path.
    #' @param prompt_template Optional path to or string of a custom prompt
    #'   template file. If not provided, the default querychat template will be
    #'   used. See the package prompts directory for the default template
    #'   format.
    #' @param data_dict Optional data dictionary. A path to a YAML file, or a
    #'   list of YAML file paths. See [read_data_dict()] for the expected format.
    #' @param cleanup Whether or not to automatically run `$cleanup()` when the
    #'   Shiny session/app stops. By default, cleanup only occurs if `QueryChat`
    #'   gets created within a Shiny session. Set to `TRUE` to always clean up,
    #'   or `FALSE` to never clean up automatically.
    #'
    #' @return A new `QueryChat` object.
    initialize = function(
      data_source,
      table_name = missing_arg(),
      ...,
      id = NULL,
      greeting = NULL,
      client = NULL,
      tools = c("filter", "query"),
      data_description = NULL,
      categorical_threshold = 20,
      extra_instructions = NULL,
      prompt_template = NULL,
      data_dict = NULL,
      cleanup = NA
    ) {
      check_dots_empty()

      # Validate arguments
      check_string(id, allow_null = TRUE)
      check_string(greeting, allow_null = TRUE)
      arg_match(
        tools,
        values = c("filter", "update", "query", "visualize"),
        multiple = TRUE
      )
      tools <- normalize_tools(tools)
      check_string(data_description, allow_null = TRUE)
      check_number_whole(categorical_threshold, min = 1)
      check_string(extra_instructions, allow_null = TRUE)
      check_string(prompt_template, allow_null = TRUE)
      check_bool(cleanup, allow_na = TRUE)

      # Normalize data_dicts
      private$.data_dicts <- normalize_data_dicts(data_dict)

      # Store init parameters for deferred system prompt building
      private$.prompt_template <- prompt_template
      private$.data_description <- data_description
      private$.data_description_mode <- if (is.null(data_description)) {
        "empty"
      } else {
        "supplied"
      }
      private$.extra_instructions <- extra_instructions
      private$.categorical_threshold <- categorical_threshold

      self$tools <- tools
      private$.client_spec <- client

      if (!is.null(greeting) && file.exists(greeting)) {
        greeting <- read_utf8(greeting)
      }
      self$greeting <- greeting

      # Track whether id was explicitly set
      self$id_override <- id

      # Handle table_name inference for non-NULL data sources
      if (!is.null(data_source)) {
        if (is_missing(table_name)) {
          if (inherits(data_source, "DataSource")) {
            table_name <- data_source$table_name
          } else if (
            is.data.frame(data_source) || inherits(data_source, "tbl_sql")
          ) {
            table_name <- deparse1(substitute(data_source))
          } else if (inherits(data_source, "pins_board")) {
            cli::cli_abort(
              "{.arg table_name} (the pin name) is required when {.arg data_source} is a pins board."
            )
          }
        }
        normalized <- normalize_data_source(data_source, table_name)
        private$.data_sources[[normalized$table_name]] <- normalized
        private$auto_fill_data_description()
        private$build_system_prompt()
        self$id <- id %||% sprintf("querychat_%s", normalized$table_name)
      } else {
        # Deferred pattern: data_source is NULL
        if (is_missing(table_name)) {
          cli::cli_abort(
            "{.arg table_name} is required when {.arg data_source} is {.val NULL}."
          )
        }
        private$.deferred_table_name <- table_name
        self$id <- id %||% sprintf("querychat_%s", table_name)
      }

      # By default, only close automatically if a Shiny session is active
      if (is.na(cleanup)) {
        cleanup <- shiny::isRunning()
      }

      if (cleanup) {
        shiny::onStop(function() {
          cli::cli_inform("Closing data source...")
          self$cleanup()
        })
      }
    },

    #' @description
    #' Add a table to this QueryChat instance.
    #'
    #' @param data_source A data frame, database connection, or DataSource object.
    #' @param table_name The SQL table name for this data source.
    #' @param replace Whether to replace an existing table with this name.
    #'   Default is `FALSE`.
    #'
    #' @return Invisibly returns `self` for chaining.
    add_table = function(data_source, table_name, replace = FALSE) {
      if (private$.server_initialized) {
        cli::cli_abort("Cannot add tables after server initialization.")
      }
      check_sql_table_name(table_name)
      if (table_name %in% names(private$.data_sources) && !replace) {
        cli::cli_abort(
          "Table {.val {table_name}} already exists. Use {.code replace = TRUE} to replace."
        )
      }
      normalized <- normalize_data_source(data_source, table_name)

      other_sources <- private$.data_sources[
        names(private$.data_sources) != table_name
      ]
      check_source_compatibility(other_sources, normalized, table_name)

      next_sources <- private$.data_sources
      next_sources[[table_name]] <- normalized

      private$auto_fill_data_description()
      tryCatch(
        {
          private$build_system_prompt(data_sources = next_sources)
        },
        error = function(e) {
          if (!inherits(data_source, "DataSource")) normalized$cleanup()
          stop(e)
        }
      )

      old_source <- private$.data_sources[[table_name]]
      private$.data_sources <- next_sources
      if (!is.null(old_source) && !identical(old_source, normalized)) {
        old_source$cleanup()
      }

      if (!is.null(private$.query_executor)) {
        tryCatch(private$.query_executor$cleanup(), error = function(e) NULL)
        private$.query_executor <- NULL
      }

      if (length(private$.data_sources) == 1 && is.null(self$id_override)) {
        self$id <- sprintf("querychat_%s", table_name)
      }

      invisible(self)
    },

    #' @description
    #' Remove a table from this QueryChat instance.
    #'
    #' @param table_name The name of the table to remove.
    #'
    #' @return Invisibly returns `self` for chaining.
    remove_table = function(table_name) {
      if (private$.server_initialized) {
        cli::cli_abort("Cannot remove tables after server initialization.")
      }
      if (!table_name %in% names(private$.data_sources)) {
        cli::cli_abort("Table {.val {table_name}} not found.")
      }
      if (length(private$.data_sources) == 1) {
        cli::cli_abort(
          "Cannot remove last table. At least one table is required."
        )
      }
      removed <- private$.data_sources[[table_name]]
      next_sources <- private$.data_sources[
        names(private$.data_sources) != table_name
      ]
      private$build_system_prompt(data_sources = next_sources)
      private$.data_sources <- next_sources
      if (!is.null(private$.query_executor)) {
        tryCatch(private$.query_executor$cleanup(), error = function(e) NULL)
        private$.query_executor <- NULL
      }
      removed$cleanup()
      invisible(self)
    },

    #' @description
    #' Return the names of all registered tables.
    table_names = function() names(private$.data_sources),

    #' @description
    #' Return a [TableAccessor] for the given table.
    #'
    #' @param name The name of the table.
    table = function(name) {
      if (!name %in% names(private$.data_sources)) {
        available <- paste0(
          "'",
          names(private$.data_sources),
          "'",
          collapse = ", "
        )
        cli::cli_abort(
          "Table {.val {name}} not found. Available: {available}"
        )
      }
      TableAccessor$new(name, private$.data_sources[[name]])
    },

    #' @description
    #' Create a chat client, complete with registered tools, for the current
    #' data source.
    #'
    #' @param tools Which querychat tools to include in the chat client.
    #'   `"filter"` includes the tools for filtering and resetting the dashboard
    #'   and `"query"` includes the tool for executing SQL queries. By default,
    #'   when `tools = NA`, the values provided at initialization are used.
    #'   The legacy name `"update"` is still accepted as an alias for `"filter"`.
    #' @param update_dashboard Optional function to call with the `query`,
    #'   `title`, and `table` generated by the LLM for the `update_dashboard` tool.
    #' @param reset_dashboard Optional function to call when the
    #'   `reset_dashboard` tool is called. Takes a `table` argument.
    #' @param visualize Optional function to call with a list containing
    #'   `ggsql`, `title`, and `widget_id` when a visualization succeeds.
    #' @param session A Shiny session object. Required when `"visualize"` is
    #'   in `tools` and you want interactive chart rendering. When `NULL`
    #'   (the default), visualizations still execute but are not rendered
    #'   as Shiny outputs.
    client = function(
      tools = NA,
      update_dashboard = function(query, title, table) {
      },
      reset_dashboard = function(table) {
      },
      visualize = function(data) {
      },
      session = NULL
    ) {
      private$require_initialized("$client")

      if (!is_na(tools) && !is.null(tools)) {
        tools <- arg_match(
          tools,
          values = c("filter", "update", "query", "visualize"),
          multiple = TRUE
        )
        tools <- normalize_tools(tools)
      }

      private$create_session_client(
        tools = tools,
        session = session,
        update_dashboard = update_dashboard,
        reset_dashboard = reset_dashboard,
        visualize = visualize
      )
    },

    #' @description
    #' Launch a console-based chat interface with the data source.
    #'
    #' @param new Whether to create a new chat client instance or continue the
    #'   conversation from the last console chat session (the default).
    #' @param ... Additional arguments passed to the `$client()` method.
    #' @param tools Which querychat tools to include in the chat client. See
    #'   `$client()` for details. Ignored when not creating a new chat client.
    #'   By default, only the `"query"` tool is included, regardless of the
    #'   `tools` set at initialization.
    console = function(new = FALSE, ..., tools = "query") {
      private$require_initialized("$console")
      check_bool(new)
      if (new || is.null(private$.client_console)) {
        private$.client_console <- self$client(tools = tools, ...)
      }

      ellmer::live_console(private$.client_console)
    },

    #' @description
    #' Create and run a Shiny gadget for chatting with data
    #'
    #' @param ... Arguments passed to `$app_obj()`.
    #' @param bookmark_store The bookmarking storage method. Passed to
    #'   [shiny::enableBookmarking()]. If `"url"` or `"server"`, the chat state
    #'   (including current query) will be bookmarked. Default is `"url"`.
    #'
    #' @return Invisibly returns a list of session-specific values.
    app = function(..., bookmark_store = "url") {
      app <- self$app_obj(..., bookmark_store = bookmark_store)
      vals <- tryCatch(shiny::runGadget(app), interrupt = function(cnd) NULL)
      invisible(vals)
    },

    #' @description
    #' A streamlined Shiny app for chatting with data
    #'
    #' @param ... Additional arguments (currently unused).
    #' @param bookmark_store The bookmarking storage method. Passed to
    #'  [shiny::enableBookmarking()]. Default is `"url"`.
    #'
    #' @return A Shiny app object that can be run with `shiny::runApp()`.
    app_obj = function(..., bookmark_store = "url") {
      private$require_initialized("$app_obj")
      check_installed("DT")
      check_dots_empty()

      table_name <- names(private$.data_sources)[[1]]

      ui <- function(req) {
        bslib::page_sidebar(
          title = shiny::HTML(
            sprintf(
              "<span>querychat with <code>%s</code></span>",
              table_name
            )
          ),
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
          qc_vals$sql(NULL)
          qc_vals$title(NULL)
        })

        output$dt <- DT::renderDT({
          df <- qc_vals$df()
          if (inherits(df, "tbl_sql")) {
            df <- dplyr::collect(df)
          }

          DT::datatable(
            df,
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
          shiny::stopApp(
            list(
              df = qc_vals$df(),
              sql = qc_vals$sql(),
              title = qc_vals$title(),
              client = qc_vals$client
            )
          )
        })
      }

      shiny::shinyApp(ui, server, enableBookmarking = bookmark_store)
    },

    #' @description
    #' Create a sidebar containing the querychat UI.
    #'
    #' @param ... Additional arguments passed to [bslib::sidebar()].
    #' @param width Width of the sidebar in pixels. Default is 400.
    #' @param height Height of the sidebar. Default is "100%".
    #' @param fillable Whether the sidebar should be fillable. Default is
    #'   `TRUE`.
    #' @param id Optional ID for the QueryChat instance.
    #'
    #' @return A [bslib::sidebar()] UI component.
    sidebar = function(
      ...,
      width = 400,
      height = "100%",
      fillable = TRUE,
      id = NULL
    ) {
      bslib::sidebar(
        width = width,
        height = height,
        fillable = fillable,
        class = "querychat-sidebar",
        ...,
        self$ui(id = id)
      )
    },

    #' @description
    #' Create the UI for the querychat chat interface.
    #'
    #' @param ... Additional arguments passed to [shinychat::chat_ui()].
    #' @param id Optional ID for the QueryChat instance.
    #'
    #' @return A UI component containing the chat interface.
    ui = function(..., id = NULL) {
      check_string(id, allow_null = TRUE, allow_empty = FALSE)

      id <- id %||% namespaced_id(self$id)

      mod_ui(id, ...)
    },

    #' @description
    #' Initialize the querychat server logic.
    #'
    #' @param data_source Optional data source for backward compatibility.
    #'   If provided, calls `$add_table()` before initializing server logic.
    #' @param client Optional chat client override for this session.
    #' @param enable_bookmarking Whether to enable bookmarking. Default is `FALSE`.
    #' @param ... Ignored.
    #' @param id Optional module ID override.
    #' @param session The Shiny session object.
    #'
    #' @return A list containing session-specific reactive values and the chat
    #'   client. For single-table usage, includes `df`, `sql`, `title` directly.
    #'   For multi-table, use `$table("name")` to get a [TableAccessor] with
    #'   per-table reactive state. Also includes `table_names()` to list tables.
    server = function(
      data_source = NULL,
      client = NULL,
      enable_bookmarking = FALSE,
      ...,
      id = NULL,
      session = shiny::getDefaultReactiveDomain()
    ) {
      check_string(id, allow_null = TRUE, allow_empty = FALSE)
      check_dots_empty()

      if (is.null(session)) {
        cli::cli_abort(
          "{.fn $server} must be called within a Shiny server function"
        )
      }

      if (!is.null(data_source)) {
        tbl_name <- private$.deferred_table_name %||%
          names(private$.data_sources)[[1]]
        self$add_table(data_source, tbl_name, replace = TRUE)
      }

      private$require_initialized("$server")

      private$.server_initialized <- TRUE

      if (is.null(private$.query_executor)) {
        private$.query_executor <- build_query_executor(private$.data_sources)
      }

      resolved_client_spec <- client %||% private$.client_spec

      create_session_client <- function(...) {
        private$create_session_client(
          client_spec = resolved_client_spec,
          ...
        )
      }

      result <- mod_server(
        id %||% self$id,
        data_sources = private$.data_sources,
        executor = private$.query_executor,
        greeting = self$greeting,
        client = create_session_client,
        tools = self$tools,
        enable_bookmarking = enable_bookmarking
      )
      result
    },

    #' @description
    #' Generate a welcome greeting for the chat.
    #'
    #' @param echo Whether to print the greeting to the console.
    #'
    #' @return The greeting string in Markdown format.
    generate_greeting = function(echo = c("none", "output")) {
      private$require_initialized("$generate_greeting")
      chat <- private$create_session_client()
      as.character(chat$chat(GREETING_PROMPT, echo = echo))
    },

    #' @description
    #' Clean up resources associated with the data source.
    #'
    #' @return Invisibly returns `NULL`. Resources are cleaned up internally.
    cleanup = function() {
      if (!is.null(private$.query_executor)) {
        private$.query_executor$cleanup()
      }
      for (source in private$.data_sources) {
        source$cleanup()
      }
      invisible(NULL)
    }
  ),
  active = list(
    #' @field system_prompt Get the system prompt.
    system_prompt = function() {
      private$require_initialized("$system_prompt")
      private$.system_prompt$render(tools = self$tools)
    },

    #' @field data_source Removed. Use `$table('name')$data_source` instead.
    data_source = function(value) {
      if (missing(value)) {
        cli::cli_abort(
          c(
            "The {.field $data_source} property has been removed.",
            "i" = "Use {.code qc$table('name')$data_source} to access a table's data source.",
            "i" = "Use {.code qc$add_table(df, 'name')} to add a new table."
          )
        )
      } else {
        cli::cli_abort(
          c(
            "The {.field $data_source} setter has been removed.",
            "i" = "Use {.code qc$add_table(df, 'name')} to add a new table.",
            "i" = "Use {.code qc$add_table(df, 'name', replace = TRUE)} to replace one."
          )
        )
      }
    }
  )
)

#' QueryChat convenience functions
#'
#' Convenience functions for wrapping [QueryChat] creation (i.e., `querychat()`)
#' and app launching (i.e., `querychat_app()`).
#'
#' @examplesIf rlang::is_interactive() && rlang::is_installed("RSQLite")
#' # Quick start - chat with mtcars dataset in one line
#' querychat_app(mtcars)
#'
#' @param data_source Either a data.frame or a database connection (e.g., DBI
#'   connection).
#' @param table_name A string specifying the table name to use in SQL queries.
#' @param ... Additional arguments (currently unused).
#' @param id Optional module ID for the QueryChat instance.
#' @param greeting Optional initial message to display to users.
#' @param client Optional chat client.
#' @param tools Which querychat tools to include in the chat client.
#' @param data_description Optional description of the data.
#' @param categorical_threshold For text columns, the maximum number of unique
#'   values to consider as a categorical variable. Default is 20.
#' @param extra_instructions Optional additional instructions for the chat model.
#' @param prompt_template Optional path to or string of a custom prompt template.
#' @param data_dict Optional data dictionary. A path to a YAML file or a list of paths.
#' @param cleanup Whether or not to automatically run `$cleanup()` when the
#'   Shiny session/app stops.
#'
#' @return A `QueryChat` object. See [QueryChat] for available methods.
#'
#' @rdname querychat-convenience
#' @export
querychat <- function(
  data_source,
  table_name = missing_arg(),
  ...,
  id = NULL,
  greeting = NULL,
  client = NULL,
  tools = c("filter", "query"),
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  data_dict = NULL,
  cleanup = NA
) {
  if (is_missing(table_name)) {
    if (inherits(data_source, "DataSource")) {
      table_name <- data_source$table_name
    } else if (is.data.frame(data_source) || inherits(data_source, "tbl_sql")) {
      table_name <- deparse1(substitute(data_source))
    } else if (inherits(data_source, "pins_board")) {
      cli::cli_abort(
        "{.arg table_name} (the pin name) is required when {.arg data_source} is a pins board."
      )
    }
  }

  QueryChat$new(
    data_source = data_source,
    table_name = table_name,
    ...,
    id = id,
    greeting = greeting,
    client = client,
    tools = tools,
    data_description = data_description,
    categorical_threshold = categorical_threshold,
    extra_instructions = extra_instructions,
    prompt_template = prompt_template,
    data_dict = data_dict,
    cleanup = cleanup
  )
}

#' @rdname querychat-convenience
#' @param bookmark_store The bookmarking storage method. Default is `"url"`.
#' @return Invisibly returns the chat object after the app stops.
#'
#' @export
querychat_app <- function(
  data_source,
  table_name = missing_arg(),
  ...,
  id = NULL,
  greeting = NULL,
  client = NULL,
  tools = c("filter", "query"),
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  data_dict = NULL,
  cleanup = NA,
  bookmark_store = "url"
) {
  if (shiny::isRunning()) {
    cli::cli_abort(
      "{.fn querychat_app} cannot be called from within a Shiny app. Use {.fn querychat} instead."
    )
  }

  if (is_missing(table_name)) {
    if (inherits(data_source, "DataSource")) {
      table_name <- data_source$table_name
    } else if (is.data.frame(data_source)) {
      table_name <- deparse1(substitute(data_source))
    } else if (inherits(data_source, "pins_board")) {
      cli::cli_abort(
        "{.arg table_name} (the pin name) is required when {.arg data_source} is a pins board."
      )
    }
  }

  check_bool(cleanup, allow_na = TRUE)
  if (is.data.frame(data_source)) {
    cleanup <- TRUE
  } else if (is.na(cleanup)) {
    cleanup <- FALSE
  }

  qc <- QueryChat$new(
    data_source = data_source,
    table_name = table_name,
    ...,
    id = id,
    greeting = greeting,
    client = client,
    tools = tools,
    data_description = data_description,
    categorical_threshold = categorical_threshold,
    extra_instructions = extra_instructions,
    prompt_template = prompt_template,
    data_dict = data_dict,
    cleanup = cleanup
  )

  qc$app(bookmark_store = bookmark_store)
}

normalize_tools <- function(tools) {
  if (is.null(tools)) {
    return(NULL)
  }
  tools[tools == "filter"] <- "update"
  unique(tools)
}

normalize_data_source <- function(data_source, table_name) {
  if (is_data_source(data_source)) {
    return(data_source)
  }

  if (inherits(data_source, "pins_board")) {
    rlang::check_installed(
      "pins",
      reason = "to use a pins board as a data source."
    )
    return(PinSource$new(data_source, table_name))
  }

  check_sql_table_name(table_name, call = caller_env())

  if (is.data.frame(data_source)) {
    return(DataFrameSource$new(data_source, table_name))
  }

  if (inherits(data_source, "tbl_sql")) {
    return(TblSqlSource$new(data_source, table_name))
  }

  if (inherits(data_source, "DBIConnection")) {
    return(DBISource$new(data_source, table_name))
  }

  cli::cli_abort(
    "{.arg data_source} must be a {.cls DataSource}, {.cls data.frame}, or {.cls DBIConnection}, not {.obj_type_friendly {data_source}}."
  )
}

normalize_data_dicts <- function(data_dict) {
  if (is.null(data_dict)) {
    return(list())
  }
  if (is.character(data_dict)) {
    return(list(read_data_dict(data_dict)))
  }
  if (is.list(data_dict)) {
    result <- vector("list", length(data_dict))
    for (i in seq_along(data_dict)) {
      item <- data_dict[[i]]
      if (!is.character(item)) {
        cli::cli_abort(
          "Each element of {.arg data_dict} must be a file path string."
        )
      }
      result[[i]] <- read_data_dict(item)
    }
    return(result)
  }
  cli::cli_abort(
    "{.arg data_dict} must be a file path or a list of file paths."
  )
}

namespaced_id <- function(id, session = shiny::getDefaultReactiveDomain()) {
  if (is.null(session)) {
    id
  } else {
    session$ns(id)
  }
}
