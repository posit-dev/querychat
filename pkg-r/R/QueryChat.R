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
#'   values (use `qc_vals$table("name")` for multi-table access)
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
    .greeter = NULL,
    .seed_cards = NULL,

    require_initialized = function(method_name) {
      if (length(private$.data_sources) == 0) {
        cli::cli_abort(
          "{.arg data_source} must be set before calling {.fn ${method_name}}.
           Either pass {.arg data_source} to {.fn $new}, or call {.fn $add_table}."
        )
      }
    },

    auto_fill_data_description = function(sources = private$.data_sources) {
      if (length(sources) != 1) {
        return()
      }
      if (private$.data_description_mode == "inferred") {
        private$.data_description <- NULL
        private$.data_description_mode <- "empty"
      }
      if (private$.data_description_mode == "empty") {
        desc <- sources[[1]]$get_data_description()
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
      update_dashboard = function(query, title, table) {},
      reset_dashboard = function(table) {},
      visualize = function(data) {},
      card = function(action, id = NULL, card = NULL) {}
    ) {
      spec <- client_spec %||% private$.client_spec
      chat <- create_client(spec)

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

      if ("cards" %in% tools) {
        chat$register_tool(
          tool_card(executor, manage_card = card)
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
    #' @param cards Optional initial set of cards to display in the Insights
    #'   panel before any LLM interaction. Accepts:
    #'   - A list of named lists, where each named list contains the card fields
    #'     (`display`, `title`, `value`, and optionally `caption`, `theme`,
    #'     `icon`).
    #'   - A JSON string encoding such a list.
    #'   - A path to a `.json` file containing such a list.
    #'
    #'   Structural checks (e.g. each element is a named list) run at
    #'   construction time. Full field and query validation runs at app startup
    #'   and aborts loudly naming the 1-based card index on failure.
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
      cards = NULL,
      cleanup = NA
    ) {
      check_dots_empty()

      # Validate arguments
      check_string(id, allow_null = TRUE)
      check_string(greeting, allow_null = TRUE)
      arg_match(
        tools,
        values = c("filter", "update", "query", "visualize", "cards"),
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

      # Normalize and structurally validate seed cards; full field/query
      # validation is deferred to mod_server() where the executor is available.
      private$.seed_cards <- normalize_seed_cards(cards)

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
        self$greeter$tables <- c(self$greeter$tables, normalized$table_name)
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
    #' @param include_in_greeting Whether to include this table in the greeting
    #'   context. Default is `FALSE`.
    #'
    #' @return Invisibly returns `self` for chaining.
    add_table = function(
      data_source,
      table_name,
      replace = FALSE,
      include_in_greeting = FALSE
    ) {
      if (private$.server_initialized) {
        cli::cli_abort("Cannot add tables after server initialization.")
      }
      check_bool(include_in_greeting)
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

      private$auto_fill_data_description(next_sources)
      tryCatch(
        {
          private$build_system_prompt(data_sources = next_sources)
        },
        error = function(e) {
          if (!inherits(data_source, "DataSource")) {
            normalized$cleanup()
          }
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

      if (isTRUE(include_in_greeting)) {
        self$greeter$tables <- c(self$greeter$tables, table_name)
      }

      invisible(self)
    },

    #' @description
    #' Add multiple tables from a DBI connection in a single call.
    #'
    #' Unlike calling `$add_table()` repeatedly, this method builds the
    #' system prompt exactly once after all tables have been staged, avoiding
    #' N-1 spurious intermediate rebuilds.
    #'
    #' @param conn A DBI connection. Only DBI connections are supported; pass
    #'   individual data frames or other sources via `$add_table()`.
    #' @param tables Table names to register. When `NULL`, all tables returned
    #'   by `DBI::dbListTables(conn)` are used.
    #' @param replace Whether to replace existing tables with the same name.
    #'   Default is `FALSE`.
    #' @param include_in_greeting Whether to include added tables in the greeting
    #'   context. `TRUE` includes all tables; `FALSE` (default) includes none;
    #'   a character vector includes only those named tables (intersected with
    #'   the tables being added). Any other type raises an error.
    #'
    #' @return Invisibly returns `self` for chaining.
    add_tables = function(
      conn,
      tables = NULL,
      replace = FALSE,
      include_in_greeting = FALSE
    ) {
      if (private$.server_initialized) {
        cli::cli_abort("Cannot add tables after server initialization.")
      }
      if (!inherits(conn, "DBIConnection")) {
        cli::cli_abort(
          "{.fn add_tables} requires a {.cls DBIConnection}, not {.obj_type_friendly {conn}}.",
          "i" = "Use {.fn add_table} for data frames and other source types."
        )
      }
      if (is.null(tables)) {
        tables <- DBI::dbListTables(conn)
      }
      if (length(tables) == 0) {
        cli::cli_abort("No tables found in database.")
      }
      for (table_name in tables) {
        check_sql_table_name(table_name)
        if (table_name %in% names(private$.data_sources) && !replace) {
          cli::cli_abort(
            "Table {.val {table_name}} already exists. Use {.code replace = TRUE} to replace."
          )
        }
      }

      if (
        !rlang::is_bool(include_in_greeting) &&
          !is.character(include_in_greeting)
      ) {
        cli::cli_abort(
          "{.arg include_in_greeting} must be {.code TRUE}, {.code FALSE}, or a character vector of table names."
        )
      }
      greeting_tbls <- if (isTRUE(include_in_greeting)) {
        tables
      } else if (is.character(include_in_greeting)) {
        intersect(include_in_greeting, tables)
      } else {
        character()
      }

      normalized <- stats::setNames(
        lapply(tables, function(tbl) normalize_data_source(conn, tbl)),
        tables
      )

      staged <- list()
      for (table_name in tables) {
        other_sources <- private$.data_sources[
          names(private$.data_sources) != table_name
        ]
        check_source_compatibility(
          c(other_sources, staged),
          normalized[[table_name]],
          table_name
        )
        staged[[table_name]] <- normalized[[table_name]]
      }

      next_sources <- private$.data_sources
      for (table_name in tables) {
        next_sources[[table_name]] <- normalized[[table_name]]
      }

      private$auto_fill_data_description(next_sources)
      private$build_system_prompt(data_sources = next_sources)

      for (table_name in tables) {
        old_source <- private$.data_sources[[table_name]]
        if (
          !is.null(old_source) &&
            !identical(old_source, normalized[[table_name]])
        ) {
          old_source$cleanup()
        }
      }
      private$.data_sources <- next_sources

      if (!is.null(private$.query_executor)) {
        tryCatch(private$.query_executor$cleanup(), error = function(e) NULL)
        private$.query_executor <- NULL
      }

      if (length(greeting_tbls) > 0) {
        self$greeter$tables <- c(self$greeter$tables, greeting_tbls)
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
      if (!is.null(private$.greeter)) {
        private$.greeter$tables <- setdiff(
          private$.greeter$tables,
          table_name
        )
      }
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
    #' @param card Optional function to call when the `querychat_card` tool
    #'   performs an `add`, `update`, or `remove` action. The function signature
    #'   must be `function(action, id = NULL, card = NULL)`.
    #' @param session A Shiny session object. Required when `"visualize"` is
    #'   in `tools` and you want interactive chart rendering. When `NULL`
    #'   (the default), visualizations still execute but are not rendered
    #'   as Shiny outputs.
    client = function(
      tools = NA,
      update_dashboard = function(query, title, table) {},
      reset_dashboard = function(table) {},
      visualize = function(data) {},
      card = function(action, id = NULL, card = NULL) {},
      session = NULL
    ) {
      private$require_initialized("$client")

      if (!is_na(tools) && !is.null(tools)) {
        tools <- arg_match(
          tools,
          values = c("filter", "update", "query", "visualize", "cards"),
          multiple = TRUE
        )
        tools <- normalize_tools(tools)
      }

      private$create_session_client(
        tools = tools,
        session = session,
        update_dashboard = update_dashboard,
        reset_dashboard = reset_dashboard,
        visualize = visualize,
        card = card
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
    #' @param bookmark_enable Which categories of state to bookmark. Passed to
    #'   `$server()`; see its documentation for accepted values. Default is
    #'   `TRUE` (bookmark everything). Nothing is bookmarked when this is `FALSE`
    #'   or when `bookmark_store` is `"disable"`.
    #' @param bookmark_store Where bookmarked state is stored. Passed to
    #'   [shiny::enableBookmarking()]: `"url"` stores state in the URL, `"server"`
    #'   stores it server-side, and `"disable"` turns off bookmarking entirely.
    #'   Default is `NULL`, which defers to a store set via
    #'   [shiny::enableBookmarking()] if present, otherwise picks a sensible
    #'   default (`"server"` when the conversation is bookmarked or when running
    #'   on a hosting platform, `"url"` otherwise). Use `bookmark_enable` to
    #'   choose *which* state is saved.
    #'
    #' @return Invisibly returns a list of session-specific values:
    #'  - `df`: The final filtered data frame
    #'  - `sql`: The final SQL query string
    #'  - `title`: The final title
    #'  - `client`: The session-specific chat client instance
    app = function(..., bookmark_enable = TRUE, bookmark_store = NULL) {
      app <- self$app_obj(
        ...,
        bookmark_enable = bookmark_enable,
        bookmark_store = bookmark_store
      )
      vals <- tryCatch(shiny::runGadget(app), interrupt = function(cnd) NULL)
      invisible(vals)
    },

    #' @description
    #' A streamlined Shiny app for chatting with data
    #'
    #' Creates a Shiny app designed for chatting with data, with:
    #' - A sidebar containing the chat interface
    #' - A "Data" tab with the current SQL query, a reset button, and the
    #'   filtered data table
    #' - An "Insights" tab displaying LLM-curated cards, when the `"cards"` tool
    #'   is enabled
    #'
    #' ```r
    #' library(querychat)
    #'
    #' qc <- QueryChat$new(mtcars)
    #' app <- qc$app_obj()
    #' shiny::runApp(app)
    #' ```
    #'
    #' @param ... Additional arguments (currently unused).
    #' @param bookmark_enable Which categories of state to bookmark. Passed to
    #'   `$server()`; see its documentation for accepted values. Default is
    #'   `TRUE` (bookmark everything). Nothing is bookmarked when this is `FALSE`
    #'   or when `bookmark_store` is `"disable"`.
    #' @param bookmark_store Where bookmarked state is stored. Passed to
    #'  [shiny::enableBookmarking()]: `"url"` stores state in the URL, `"server"`
    #'  stores it server-side, and `"disable"` turns off bookmarking entirely.
    #'  Default is `NULL`, which defers to a store set via
    #'  [shiny::enableBookmarking()] if present, otherwise picks a sensible
    #'  default (`"server"` when the conversation is bookmarked or when running
    #'  on a hosting platform, `"url"` otherwise). Use `bookmark_enable` to
    #'  choose *which* state is saved.
    #'
    #' @return A Shiny app object that can be run with `shiny::runApp()`.
    app_obj = function(..., bookmark_enable = TRUE, bookmark_store = NULL) {
      private$require_initialized("$app_obj")
      check_installed("DT")
      check_dots_empty()

      first_table_name <- names(private$.data_sources)[[1]]
      cards_enabled <- "cards" %in% self$tools

      ui <- function(req) {
        sql_card <- bslib::card(
          fill = FALSE,
          style = bslib::css(max_height = "33%"),
          bslib::card_header(
            shiny::div(
              class = "hstack w-100",
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
        )

        data_nav <- bslib::nav_panel(
          title = list(bsicons::bs_icon("table"), "Data"),
          class = "bslib-page-dashboard",
          sql_card,
          bslib::card(
            full_screen = TRUE,
            DT::DTOutput("dt")
          )
        )

        insights_nav <- if (cards_enabled) {
          bslib::nav_panel(
            title = list(bsicons::bs_icon("lightbulb"), "Insights"),
            class = "bslib-page-dashboard",
            self$ui_cards(),
            shiny::uiOutput("cards_share_link")
          )
        }

        close_nav <- if (rlang::is_interactive()) {
          bslib::nav_item(
            shiny::actionButton(
              "close_btn",
              label = "",
              class = "btn-close",
              style = "align-self: center;"
            )
          )
        }

        rlang::inject(bslib::page_navbar(
          title = shiny::HTML(
            sprintf(
              "<span>querychat with <code>%s</code></span>",
              first_table_name
            )
          ),
          window_title = paste("querychat with", first_table_name),
          sidebar = self$sidebar(),
          header = shiny::useBusyIndicators(pulse = TRUE, spinners = FALSE),
          bslib::nav_spacer(),
          !!!compact(list(data_nav, insights_nav)),
          close_nav
        ))
      }

      # `bookmark_store` selects where state is stored; `bookmark_enable`
      # selects whether and what is stored. `resolve_bookmark_store()` picks a
      # default when `bookmark_store` is NULL and defers to a store the author
      # already set via shiny::enableBookmarking() (returning NULL in that case).
      bookmark_cats <- normalize_bookmark_categories(bookmark_enable)
      effective_store <- resolve_bookmark_store(bookmark_store, bookmark_cats)

      server <- function(input, output, session) {
        shiny::setBookmarkExclude(c(
          "close_btn",
          "reset_query",
          "sql_editor"
        ))
        qc_vals <- self$server(
          bookmark_enable = if (identical(effective_store, "disable")) {
            FALSE
          } else {
            bookmark_enable
          }
        )

        active_table_name <- shiny::reactive({
          ct <- qc_vals$current_table()
          if (!is.null(ct)) ct else first_table_name
        })

        output$data_card_header_text <- shiny::renderText({
          active_table_name()
        })

        output$query_title <- shiny::renderText({
          title <- qc_vals$.tables[[active_table_name()]]$title()
          if (shiny::isTruthy(title)) title else "SQL Query"
        })

        output$ui_reset <- shiny::renderUI({
          shiny::req(qc_vals$.tables[[active_table_name()]]$sql())
          shiny::actionButton(
            "reset_query",
            label = "Reset Query",
            class = "btn btn-outline-danger btn-sm lh-1"
          )
        })

        shiny::observeEvent(input$reset_query, label = "on_reset_query", {
          name <- active_table_name()
          qc_vals$.tables[[name]]$sql(NULL)
          qc_vals$.tables[[name]]$title(NULL)
        })

        output$dt <- DT::renderDT({
          df <- qc_vals$.tables[[active_table_name()]]$df()
          if (inherits(df, "tbl_sql")) {
            df <- dplyr::collect(df)
          }
          DT::datatable(
            df,
            fillContainer = TRUE,
            options = list(pageLength = 25, scrollX = TRUE)
          )
        })

        sql_text_for_editor <- function(name) {
          sql <- qc_vals$.tables[[name]]$sql()
          if (shiny::isTruthy(sql)) sql else paste("SELECT * FROM", name)
        }

        output$sql_output <- shiny::renderUI({
          name <- active_table_name()
          sql_text <- shiny::isolate(sql_text_for_editor(name))
          bslib::input_code_editor(
            "sql_editor",
            value = sql_text,
            language = "sql",
            line_numbers = FALSE,
            height = "auto"
          )
        })

        if (cards_enabled) {
          output$cards_share_link <- shiny::renderUI({
            current_cards <- qc_vals$cards()
            if (length(current_cards) == 0) {
              return(NULL)
            }
            url <- self$cards_url(current_cards)
            htmltools::div(
              class = "mt-2 text-end",
              htmltools::a(
                href = url,
                target = "_blank",
                rel = "noopener",
                bsicons::bs_icon("box-arrow-up-right"),
                "Open these insights in a new tab"
              )
            )
          })
        }

        shiny::observe(label = "sync_sql_editor", {
          name <- active_table_name()
          bslib::update_code_editor(
            "sql_editor",
            value = sql_text_for_editor(name)
          )
        })

        shiny::observeEvent(input$sql_editor, label = "on_sql_editor", {
          name <- active_table_name()
          query <- input$sql_editor
          default_query <- paste("SELECT * FROM", name)
          qc_vals$.tables[[name]]$sql(
            if (nzchar(query %||% "") && trimws(query) != default_query) {
              query
            } else {
              NULL
            }
          )
        })

        if (rlang::is_interactive()) {
          shiny::observeEvent(input$close_btn, label = "on_close_btn", {
            name <- active_table_name()
            shiny::stopApp(
              list(
                df = qc_vals$.tables[[name]]$df(),
                sql = qc_vals$.tables[[name]]$sql(),
                title = qc_vals$.tables[[name]]$title(),
                client = qc_vals$client
              )
            )
          })
        }
      }

      shiny::shinyApp(ui, server, enableBookmarking = effective_store)
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

      mod_ui(id, ..., greeting = self$greeting)
    },

    #' @description
    #' Create the UI for the querychat cards area.
    #'
    #' This method generates the output area where cards created by the LLM are
    #' displayed. Place it in your app's main panel, next to `$sidebar()`.
    #'
    #' ```r
    #' qc <- QueryChat$new(mtcars)
    #'
    #' ui <- bslib::page_sidebar(
    #'   sidebar = qc$sidebar(),
    #'   qc$ui_cards()
    #' )
    #' ```
    #'
    #' The placeholder text is configured on `$server()` via `card_placeholder`.
    #' Card layout is handled automatically.
    #'
    #' @param ... Additional arguments passed to [shiny::uiOutput()].
    #' @param id Optional ID for the QueryChat instance. If not provided,
    #'   will use the ID provided at initialization. If using `$ui_cards()` in a
    #'   Shiny module, you'll need to provide `id = ns("your_id")` where `ns` is
    #'   the namespacing function from [shiny::NS()].
    #'
    #' @return A UI component containing the cards output area.
    ui_cards = function(..., id = NULL) {
      check_string(id, allow_null = TRUE, allow_empty = FALSE)
      id <- id %||% namespaced_id(self$id)
      mod_ui_cards(id, ...)
    },

    #' @description
    #' Build a shareable URL that opens the app with the given cards pre-loaded.
    #'
    #' The cards list is encoded as a compact gzip+base64 query parameter.
    #' When visited, `$server()` seeds the cards reactive from this parameter
    #' before the first render — so the app opens with the shared insight cards
    #' already visible, without requiring a bookmark.
    #'
    #' @param cards A list of card field-lists, or a JSON string that encodes
    #'   such a list. Required; there is no default.
    #' @param ... Must be empty.
    #' @param id Optional module ID override. Defaults to `self$id`.
    #'
    #' @return A URL string (absolute when called from a session, relative
    #'   otherwise).
    cards_url = function(cards = NULL, ..., id = NULL) {
      rlang::check_dots_empty()
      if (is.null(cards)) {
        cli::cli_abort(
          "{.arg cards} is required: pass a list of cards or a JSON string."
        )
      }
      if (is.character(cards) && length(cards) == 1) {
        cards <- jsonlite::fromJSON(cards, simplifyVector = FALSE)
      }
      id <- id %||% self$id
      # shiny::NS(id)("querychat_cards") == paste0(id, "-querychat_cards")
      key <- paste0(id, "-querychat_cards")
      payload <- cards_to_payload(cards)
      encoded_key <- utils::URLencode(key, reserved = TRUE)
      encoded_val <- utils::URLencode(payload, reserved = TRUE)
      qs <- sprintf("?%s=%s", encoded_key, encoded_val)
      session <- shiny::getDefaultReactiveDomain()
      if (!is.null(session)) {
        cd <- session$clientData
        port <- cd$url_port
        host <- if (nzchar(port %||% "")) {
          paste0(cd$url_hostname, ":", port)
        } else {
          cd$url_hostname
        }
        paste0(cd$url_protocol, "//", host, cd$url_pathname, qs)
      } else {
        qs
      }
    },

    #' @description
    #' Update the browser URL to a shareable cards link.
    #'
    #' A thin wrapper around `$cards_url()` that calls
    #' [shiny::updateQueryString()] with the resulting URL. Must be called
    #' from within a Shiny server function.
    #'
    #' @param cards A list of card field-lists, or a JSON string. Required.
    #' @param ... Passed to `$cards_url()`.
    #' @param id Optional module ID override.
    #'
    #' @return Invisibly returns the URL string.
    cards_set_url = function(cards = NULL, ..., id = NULL) {
      url <- self$cards_url(cards, ..., id = id)
      shiny::updateQueryString(url)
      invisible(url)
    },

    #' @description
    #' Initialize the querychat server logic.
    #'
    #' This method must be called within a Shiny server function. It sets up the
    #' reactive logic for the chat interface and returns session-specific
    #' reactive values.
    #'
    #' ```r
    #' qc <- QueryChat$new(mtcars)
    #'
    #' server <- function(input, output, session) {
    #'   qc_vals <- qc$server(bookmark_enable = TRUE)
    #'
    #'   output$data <- renderDataTable(qc_vals$df())
    #'   output$query <- renderText(qc_vals$sql())
    #'   output$title <- renderText(qc_vals$title() %||% "No Query")
    #' }
    #' ```
    #'
    #' @param data_source Optional data source to use. If provided, sets the
    #'   data_source property before initializing server logic. This is useful
    #'   for the deferred pattern where data_source is not known at
    #'   initialization time (e.g., when the data source depends on session-
    #'   specific authentication).
    #' @param client Optional chat client override for this session. Can be an
    #'   [ellmer::Chat] object or a string (e.g., `"openai/gpt-4o"`). If provided,
    #'   overrides the client set at initialization for this session only —
    #'   other sessions are unaffected. This is useful when the client must be
    #'   created within a session scope (e.g., Posit Connect managed credentials).
    #' @param bookmark_enable Which categories of state to bookmark. Default
    #'   is `FALSE` (no bookmarking). Accepts:
    #'   - `TRUE` to bookmark everything (equivalent to
    #'     `c("conversation", "cards")`).
    #'   - `FALSE` or `NULL` to disable bookmarking.
    #'   - A character vector subset of `c("conversation", "cards")` to bookmark
    #'     only those categories. `"conversation"` covers the chat transcript,
    #'     the active dashboard filter (query and title), the generated greeting,
    #'     and inline visualization widgets. `"cards"` covers the insight cards
    #'     created with the `querychat_card` tool.
    #'
    #'   Bookmarking categories independently enables share patterns such as
    #'   `bookmark_enable = "cards"`, which produces links that open the app
    #'   with the same insights but a fresh conversation.
    #'
    #'   This requires that the Shiny app has bookmarking enabled via
    #'   `shiny::enableBookmarking()` or the `enableBookmarking` parameter of
    #'   `shiny::shinyApp()`.
    #' @param enable_bookmarking `r lifecycle::badge("deprecated")` Renamed to
    #'   `bookmark_enable`.
    #' @param card_placeholder Text shown in the `$ui_cards()` area when no
    #'   cards exist. Set to `NULL` for no placeholder.
    #' @param ... Ignored.
    #' @param id Optional module ID override.
    #' @param session The Shiny session object.
    #'
    #' @return A list containing session-specific reactive values and the chat
    #'   client. For single-table usage, includes `df`, `sql`, `title` directly.
    #'   For multi-table, use `qc_vals$table("name")` to get a [TableAccessor]
    #'   with per-table reactive state. Also includes `table_names()` to list tables,
    #'   `current_table()` which returns the name of the most recently queried table
    #'   (or `NULL` before any query), and `cards`, a reactive value holding the
    #'   current list of cards.
    #'
    server = function(
      data_source = NULL,
      client = NULL,
      bookmark_enable = FALSE,
      card_placeholder = "Insights will appear here",
      ...,
      id = NULL,
      session = shiny::getDefaultReactiveDomain(),
      enable_bookmarking = lifecycle::deprecated()
    ) {
      check_string(id, allow_null = TRUE, allow_empty = FALSE)
      check_dots_empty()

      if (lifecycle::is_present(enable_bookmarking)) {
        if (!missing(bookmark_enable)) {
          cli::cli_abort(c(
            "Can't supply both {.arg bookmark_enable} and the deprecated {.arg enable_bookmarking}.",
            "i" = "Use only {.arg bookmark_enable}."
          ))
        }
        lifecycle::deprecate_warn(
          when = "0.4.0",
          what = "QueryChat$server(enable_bookmarking = )",
          with = "QueryChat$server(bookmark_enable = )"
        )
        bookmark_enable <- enable_bookmarking
      }

      if (is.null(session)) {
        cli::cli_abort(
          "{.fn $server} must be called within a Shiny server function"
        )
      }

      if (!is.null(data_source)) {
        tbl_name <- private$.deferred_table_name %||%
          names(private$.data_sources)[[1]]
        self$add_table(
          data_source,
          tbl_name,
          replace = TRUE,
          include_in_greeting = TRUE
        )
      }

      private$require_initialized("$server")

      private$.server_initialized <- TRUE

      if (is.null(private$.query_executor)) {
        private$.query_executor <- build_query_executor(private$.data_sources)
      }

      resolved_client_spec <- client %||% private$.client_spec
      base_client <- as_querychat_client(resolved_client_spec)

      create_session_client <- function(...) {
        private$create_session_client(
          client_spec = base_client,
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
        greeter = self$greeter,
        greeting_base = base_client,
        bookmark_enable = bookmark_enable,
        card_placeholder = card_placeholder,
        seed_cards = private$.seed_cards
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
      greeting <- self$greeter$generate(echo = echo)
      self$greeting <- greeting
      greeting
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
    #' @field greeter The QueryChatGreeter controlling greeting generation;
    #'   access its `$tables` and `$prompt`.
    greeter = function(value) {
      if (!missing(value)) {
        # The greeter is read-only. Sub-field assignments like
        # `qc$greeter$tables <- x` mutate the greeter by reference and
        # trigger a write-back of the (unchanged) binding, which we ignore.
        return(invisible(value))
      }
      if (is.null(private$.greeter)) {
        client_factory <- function(tables, prompt, base = NULL) {
          sp <- QueryChatSystemPrompt$new(
            prompt_template = prompt,
            data_sources = private$.data_sources,
            data_description = private$.data_description,
            extra_instructions = NULL,
            categorical_threshold = private$.categorical_threshold,
            data_dicts = private$.data_dicts,
            include_tables = tables,
            include_relationships = FALSE,
            include_glossary = FALSE
          )
          chat <- create_client(base %||% private$.client_spec)
          chat$set_system_prompt(sp$render(tools = NULL))
          chat
        }
        private$.greeter <- QueryChatGreeter$new(
          client_factory = client_factory
        )
      }
      private$.greeter
    },

    #' @field system_prompt Get the system prompt.
    system_prompt = function() {
      private$require_initialized("$system_prompt")
      private$.system_prompt$render(tools = self$tools)
    },

    #' @field data_source Removed. Use `$add_table()` and `$remove_table()` to manage tables.
    data_source = function(value) {
      if (missing(value)) {
        cli::cli_abort(
          c(
            "The {.field $data_source} property has been removed.",
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
#' @param tools Which querychat tools to include in the chat client, by
#'   default. `"filter"` includes the tools for filtering and resetting the
#'   dashboard and `"query"` includes the tool for executing SQL queries.
#'   Use `tools = "filter"` when you only want the dashboard filtering tools,
#'   or when you want to disable the querying tool entirely to prevent the
#'   LLM from seeing any of the data in your dataset. The legacy name
#'   `"update"` is still accepted as an alias for `"filter"`.
#'   `querychat_app()` defaults to
#'   `c("filter", "query", "visualize", "cards")` so the bundled app's Insights
#'   tab is populated; pass `tools` explicitly to override.
#' @param data_description Optional description of the data in plain text or
#'   Markdown. Can be a string or a file path. This provides context to the
#'   LLM about what the data represents.
#' @param categorical_threshold For text columns, the maximum number of unique
#'   values to consider as a categorical variable. Default is 20.
#' @param extra_instructions Optional additional instructions for the chat model.
#' @param prompt_template Optional path to or string of a custom prompt template.
#' @param data_dict Optional data dictionary. A path to a YAML file or a list of paths.
#' @param cards Optional initial set of cards to display in the Insights panel
#'   before any LLM interaction. A list of named card field-lists, a JSON
#'   string, or a path to a `.json` file. See `QueryChat$new()` for details.
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
  cards = NULL,
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
    cards = cards,
    cleanup = cleanup
  )
}

#' @rdname querychat-convenience
#' @param bookmark_enable Which categories of state to bookmark. Passed to
#'   `QueryChat$server()`; see its documentation for accepted values. Default is
#'   `TRUE` (bookmark everything). Nothing is bookmarked when this is `FALSE` or
#'   when `bookmark_store` is `"disable"`.
#' @param bookmark_store Where bookmarked state is stored. Passed to
#'   [shiny::enableBookmarking()]: `"url"` stores state in the URL, `"server"`
#'   stores it server-side, and `"disable"` turns off bookmarking entirely.
#'   Default is `NULL`, which defers to a store set via
#'   [shiny::enableBookmarking()] if present, otherwise picks a sensible default
#'   (`"server"` when the conversation is bookmarked or when running on a
#'   hosting platform, `"url"` otherwise). Use `bookmark_enable` to choose
#'   *which* state is saved.
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
  tools = c("filter", "query", "visualize", "cards"),
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  data_dict = NULL,
  cleanup = NA,
  bookmark_enable = TRUE,
  bookmark_store = NULL
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

  qc$app(
    bookmark_enable = bookmark_enable,
    bookmark_store = bookmark_store
  )
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
