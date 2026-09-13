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
    .table_set = NULL,
    # Instance sets swapped out by $add_table()/$add_tables() after a session
    # started. A running session may still hold one, so $cleanup() closes them.
    .superseded_table_sets = list(),
    .sessions_started = FALSE,
    .deferred_table_name = NULL,
    .client_spec = NULL,
    .client_console = NULL,
    # Store init parameters for deferred system prompt building
    .prompt_template = NULL,
    .data_description = NULL,
    .data_description_mode = "empty", # "supplied", "inferred", or "empty"
    .extra_instructions = NULL,
    .categorical_threshold = NULL,
    .data_dicts = list(),
    .greeter = NULL,

    data_sources = function() {
      if (is.null(private$.table_set)) {
        return(list())
      }
      private$.table_set$data_sources
    },

    require_table_set = function(method_name) {
      if (is.null(private$.table_set)) {
        cli::cli_abort(
          "{.arg data_source} must be set before calling {.fn ${method_name}}.
           Either pass {.arg data_source} to {.fn $new}, or call {.fn $add_table}."
        )
      }
      private$.table_set
    },

    require_initialized = function(method_name) {
      private$require_table_set(method_name)
      invisible(NULL)
    },

    # Non-mutating counterpart of auto_fill_data_description(): the single
    # source of truth for "what description should this set of sources get",
    # given the instance's current mode/description. Used both to compute the
    # value auto_fill_data_description() mutates in, and to build sets on
    # behalf of a session (which must never mutate the instance).
    #
    # When sources isn't a single table and the mode isn't "supplied", this
    # falls back to whatever description is already stored (bug-for-bug with
    # auto_fill_data_description()'s historical early return): a multi-table
    # set doesn't clear a stale single-source "inferred" description.
    resolve_data_description = function(sources) {
      if (private$.data_description_mode == "supplied") {
        return(private$.data_description)
      }
      if (length(sources) != 1) {
        return(private$.data_description)
      }
      desc <- sources[[1]]$get_data_description()
      if (nzchar(desc %||% "")) {
        return(desc)
      }
      NULL
    },

    auto_fill_data_description = function(sources = private$data_sources()) {
      if (private$.data_description_mode == "supplied") {
        return(invisible(NULL))
      }
      if (length(sources) != 1) {
        return(invisible(NULL))
      }
      private$.data_description <- private$resolve_data_description(sources)
      private$.data_description_mode <- if (
        is.null(private$.data_description)
      ) {
        "empty"
      } else {
        "inferred"
      }
      invisible(NULL)
    },

    build_table_set = function(
      sources,
      data_description = private$.data_description
    ) {
      if (length(sources) == 0) {
        cli::cli_abort("Cannot build system prompt without data sources")
      }
      validate_source_group_compatibility(sources)
      prompt_template <- private$.prompt_template %||%
        system.file("prompts", "prompt.md", package = "querychat")
      system_prompt <- QueryChatSystemPrompt$new(
        prompt_template = prompt_template,
        data_sources = sources,
        data_description = data_description,
        extra_instructions = private$.extra_instructions,
        categorical_threshold = private$.categorical_threshold,
        data_dicts = private$.data_dicts
      )
      TableSet$new(sources, system_prompt, data_description = data_description)
    },

    check_late_change = function(method_name, destructive) {
      if (!private$.sessions_started) {
        return(invisible(NULL))
      }
      if (destructive) {
        cli::cli_abort(c(
          "Cannot call {.fn ${method_name}} to replace or remove a table while sessions may be using it.",
          "i" = "Configure all tables before calling {.fn $server} or {.fn $app}."
        ))
      }
      cli::cli_warn(c(
        "{.fn ${method_name}} called after a session has started.",
        "i" = "Sessions that are already running keep the tables they started with; only new sessions will see this change."
      ))
      invisible(NULL)
    },

    swap_table_set = function(new_set, replaced = list()) {
      old_set <- private$.table_set
      private$.table_set <- new_set
      if (is.null(old_set)) {
        return(invisible(NULL))
      }
      if (private$.sessions_started) {
        # `replaced` is empty here: check_late_change() rejects replacement
        # once sessions have started.
        private$.superseded_table_sets <- c(
          private$.superseded_table_sets,
          list(old_set)
        )
        return(invisible(NULL))
      }
      warn_on_cleanup_failure(old_set$cleanup_executor(), "query executor")
      for (source in replaced) {
        warn_on_cleanup_failure(source$cleanup(), "data source")
      }
      invisible(NULL)
    },

    create_session_client = function(
      table_set,
      client_spec = NULL,
      tools = NA,
      handoff_available = FALSE,
      session = NULL,
      update_dashboard = function(query, title, table) {},
      reset_dashboard = function(table) {},
      visualize = function(data) {}
    ) {
      spec <- client_spec %||% private$.client_spec
      chat <- create_client(spec)

      if (is_na(tools)) {
        tools <- self$tools
      }
      tools <- check_viz_deps(tools)

      chat$set_system_prompt(
        table_set$system_prompt$render(
          tools = tools,
          handoff_available = handoff_available
        )
      )

      if (is.null(tools)) {
        return(chat)
      }

      executor <- table_set$executor()
      tbl_names <- table_set$table_names()

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
    #' @field history Conversation history configuration.
    history = NULL,
    #' @field id ID for the QueryChat instance.
    id = NULL,
    #' @field id_override Whether the ID was explicitly set by the user.
    id_override = NULL,
    #' @field tools The allowed tools for the chat client.
    tools = c("filter", "query", "visualize"),

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
    #'   be inferred from the variable name for data.frame inputs. Required for
    #'   database connections. Optional when `data_source` is `NULL`: if
    #'   omitted, `$id` falls back to a generic default, and a table name must
    #'   be supplied later via `$add_table()` or `$server(data_source =,
    #'   table_name = )`.
    #' @param ... Additional arguments (currently unused).
    #' @param id Optional module ID for the QueryChat instance. If not provided,
    #'   will be auto-generated from `table_name` (or a generic default when
    #'   `data_source` is `NULL` and `table_name` is also omitted). The ID is
    #'   used to namespace the Shiny module.
    #' @param greeting Optional initial message to display to users. Can be a
    #'   character string (in Markdown format) or a file path. If not provided,
    #'   a greeting will be generated at the start of each conversation using
    #'   the LLM, which adds latency and cost. Use `$generate_greeting()` to
    #'   create a greeting to save and reuse.
    #' @param history Conversation history configuration: `NULL` (default;
    #'   resolves to `TRUE` when `$server()`/`$app()` is called and nothing else
    #'   was set), `TRUE`/`FALSE`, or a [shinychat::history_options()] object.
    #'   Passed straight through to `shinychat::chat_server(history = )`.
    #' @param client Optional chat client. Can be:
    #'   - An [ellmer::Chat] object
    #'   - A string to pass to [ellmer::chat()] (e.g., `"openai/gpt-4o"`)
    #'   - `NULL` (default): Uses the `querychat.client` option, the
    #'     `QUERYCHAT_CLIENT` environment variable, or defaults to
    #'     [ellmer::chat_openai()]
    #' @param tools Which querychat tools to include in the chat client, by
    #'   default. `"filter"` includes the tools for filtering and resetting the
    #'   dashboard, `"query"` includes the tool for executing SQL queries, and
    #'   `"visualize"` includes the tool for rendering visualizations (requires
    #'   the \pkg{ggsql} package; if it is not installed, the tool is dropped
    #'   with a warning). The default is `c("filter", "query", "visualize")`.
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
      history = NULL,
      client = NULL,
      tools = c("filter", "query", "visualize"),
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
      check_history(history)
      arg_match(
        tools,
        values = c("filter", "update", "query", "visualize"),
        multiple = TRUE
      )
      tools <- normalize_tools(tools)
      tools <- check_viz_deps(tools)
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
      self$history <- history

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
        sources <- stats::setNames(list(normalized), normalized$table_name)
        private$auto_fill_data_description(sources)
        private$.table_set <- private$build_table_set(sources)
        self$greeter$tables <- c(self$greeter$tables, normalized$table_name)
        self$id <- id %||% sprintf("querychat_%s", normalized$table_name)
      } else {
        # Deferred pattern: data_source is NULL. table_name is optional here;
        # explicit NULL is treated the same as omitting it.
        table_name_given <- !is_missing(table_name) && !is.null(table_name)
        if (table_name_given) {
          private$.deferred_table_name <- table_name
        }
        default_id <- if (table_name_given) {
          sprintf("querychat_%s", table_name)
        } else {
          "querychat"
        }
        self$id <- id %||% default_id
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
    #' Replacing or removing an existing table after a session has started is
    #' an error; adding a new one warns.
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
      check_bool(include_in_greeting)
      check_sql_table_name(table_name)
      current <- private$data_sources()
      exists <- table_name %in% names(current)
      if (exists && !replace) {
        cli::cli_abort(
          "Table {.val {table_name}} already exists. Use {.code replace = TRUE} to replace."
        )
      }

      if (
        is_data_source(data_source) &&
          !identical(data_source$table_name, table_name)
      ) {
        cli::cli_abort(
          c(
            "{.arg data_source}'s own table name ({.val {data_source$table_name}}) does not match the given {.arg table_name} ({.val {table_name}}).",
            "i" = "Pass a matching {.arg table_name}, or omit it to use {.val {data_source$table_name}}."
          )
        )
      }

      normalized <- normalize_data_source(data_source, table_name)
      cleanup_normalized <- function() {
        if (!inherits(data_source, "DataSource")) {
          normalized$cleanup()
        }
      }
      next_sources <- current
      next_sources[[table_name]] <- normalized
      private$auto_fill_data_description(next_sources)
      new_set <- tryCatch(
        private$build_table_set(next_sources),
        error = function(e) {
          cleanup_normalized()
          stop(e)
        }
      )

      # Only after the change is known to be valid do we check whether it's
      # too late to apply it, so a rejected/failed add_table() doesn't warn.
      tryCatch(
        private$check_late_change("add_table", destructive = exists),
        error = function(e) {
          new_set$cleanup_executor()
          cleanup_normalized()
          stop(e)
        }
      )

      old_source <- current[[table_name]]
      replaced <- if (
        !is.null(old_source) && !identical(old_source, normalized)
      ) {
        list(old_source)
      } else {
        list()
      }
      private$swap_table_set(new_set, replaced = replaced)

      if (isTRUE(include_in_greeting) && !table_name %in% self$greeter$tables) {
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
    #' Replacing or removing an existing table after a session has started is
    #' an error; adding a new one warns.
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
      current <- private$data_sources()
      for (table_name in tables) {
        check_sql_table_name(table_name)
      }
      existing <- intersect(tables, names(current))
      if (length(existing) > 0 && !replace) {
        cli::cli_abort(
          "Table {.val {existing[[1]]}} already exists. Use {.code replace = TRUE} to replace."
        )
      }
      private$check_late_change(
        "add_tables",
        destructive = length(existing) > 0
      )

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
      next_sources <- current
      for (table_name in tables) {
        next_sources[[table_name]] <- normalized[[table_name]]
      }
      private$auto_fill_data_description(next_sources)
      new_set <- private$build_table_set(next_sources)

      replaced <- list()
      for (table_name in tables) {
        old_source <- current[[table_name]]
        if (
          !is.null(old_source) &&
            !identical(old_source, normalized[[table_name]])
        ) {
          replaced <- c(replaced, list(old_source))
        }
      }
      private$swap_table_set(new_set, replaced = replaced)

      new_greeting <- self$greeter$tables
      for (name in greeting_tbls) {
        if (!name %in% new_greeting) {
          new_greeting <- c(new_greeting, name)
        }
      }
      self$greeter$tables <- new_greeting

      invisible(self)
    },

    #' @description
    #' Remove a table from this QueryChat instance.
    #'
    #' Removing an existing table after a session has started is an error.
    #'
    #' @param table_name The name of the table to remove.
    #'
    #' @return Invisibly returns `self` for chaining.
    remove_table = function(table_name) {
      private$check_late_change("remove_table", destructive = TRUE)
      current <- private$data_sources()
      if (!table_name %in% names(current)) {
        cli::cli_abort("Table {.val {table_name}} not found.")
      }
      if (length(current) == 1) {
        cli::cli_abort(
          "Cannot remove last table. At least one table is required."
        )
      }
      removed <- current[[table_name]]
      next_sources <- current[names(current) != table_name]
      new_set <- private$build_table_set(next_sources)
      private$swap_table_set(new_set, replaced = list(removed))
      if (!is.null(private$.greeter)) {
        private$.greeter$tables <- setdiff(private$.greeter$tables, table_name)
      }
      invisible(self)
    },

    #' @description
    #' Return the names of all registered tables.
    table_names = function() names(private$data_sources()) %||% character(),

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
      update_dashboard = function(query, title, table) {},
      reset_dashboard = function(table) {},
      visualize = function(data) {},
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
        table_set = private$require_table_set("$client"),
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
    #' @param history Conversation history configuration for the generated app.
    #'   Defaults to `shinychat::history_options(restore_mode = "bookmark")` when
    #'   neither this nor `$new()`'s `history` was set, since `$app()`'s whole
    #'   purpose is a single, shareable demo. When the resolved value has
    #'   `restore_mode = "bookmark"`, the generated app automatically enables
    #'   Shiny's own server-side bookmarking.
    #'
    #' @return Invisibly returns a list of session-specific values.
    app = function(..., history = NULL) {
      app <- self$app_obj(..., history = history)
      vals <- tryCatch(shiny::runGadget(app), interrupt = function(cnd) NULL)
      invisible(vals)
    },

    #' @description
    #' A streamlined Shiny app for chatting with data
    #'
    #' @param ... Additional arguments (currently unused).
    #' @param history Conversation history configuration for the generated app.
    #'   See `$app()`.
    #'
    #' @return A Shiny app object that can be run with `shiny::runApp()`.
    app_obj = function(..., history = NULL) {
      private$require_initialized("$app_obj")
      check_installed("DT")
      check_dots_empty()
      check_history(history)
      resolved_history <- history %||%
        self$history %||%
        shinychat::history_options(restore_mode = "bookmark")
      enable_shiny_bookmarking <- inherits(
        resolved_history,
        "chat_history_config"
      ) &&
        identical(resolved_history$restore_mode, "bookmark")

      first_table_name <- names(private$data_sources())[[1]]
      table_names <- names(private$data_sources())
      multi_table <- length(table_names) > 1

      ui <- function(req) {
        self$page(
          title = shiny::HTML(
            sprintf(
              "<span>querychat with <code>%s</code></span>",
              first_table_name
            )
          ),
          window_title = "querychat",
          drawer = shinychat::chat_drawer(
            bslib::card(
              full_screen = TRUE,
              bslib::card_header(
                bsicons::bs_icon("table"),
                "Data \u2014 ",
                shiny::textOutput("data_card_header_text", inline = TRUE)
              ),
              DT::DTOutput("dt"),
              show_query_footer(
                target = "sql_query_section",
                content = shiny::uiOutput("sql_output"),
                right = shiny::uiOutput("ui_reset", inline = TRUE)
              )
            ),
            if (multi_table) {
              bslib::accordion(
                !!!lapply(table_names, function(name) {
                  bslib::accordion_panel(
                    shiny::tags$span(
                      name,
                      shiny::uiOutput(
                        paste0("active_badge_", name),
                        inline = TRUE
                      )
                    ),
                    DT::DTOutput(paste0("dt_", name)),
                    show_query_footer(
                      target = paste0("sql_query_section_", name),
                      content = shiny::uiOutput(paste0("sql_view_", name))
                    ),
                    value = name
                  )
                }),
                id = "data_sources_accordion",
                open = FALSE
              )
            },
            title = "Data Sources",
            open = FALSE,
            width = "calc(min(clamp(360px, 55vw, 720px), 100%))"
          ),
          footer = htmltools::tagList(
            shiny::useBusyIndicators(pulse = TRUE, spinners = FALSE),
            if (rlang::is_interactive()) {
              shiny::actionButton(
                "close_btn",
                label = "",
                class = "btn-close",
                style = "position: fixed; top: 6px; right: 6px;"
              )
            }
          )
        )
      }

      server <- function(input, output, session) {
        shiny::setBookmarkExclude(c(
          "close_btn",
          "reset_query",
          "sql_editor",
          if (multi_table) paste0("sql_view_editor_", table_names)
        ))
        qc_vals <- self$server(history = resolved_history)

        active_table_name <- shiny::reactive({
          ct <- qc_vals$current_table()
          if (!is.null(ct)) ct else first_table_name
        })

        # Auto-open the data drawer when a new query lands
        shiny::observe(label = "auto_open_drawer", {
          name <- active_table_name()
          if (shiny::isTruthy(qc_vals$.tables[[name]]$sql())) {
            shinychat::chat_drawer_show(shiny::NS(self$id)("chat"))
          }
        })

        output$data_card_header_text <- shiny::renderText({
          active_table_name()
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

        if (multi_table) {
          # One data grid, read-only query view, and "active" badge per
          # registered table, for the drawer's data-sources accordion. The
          # accordion is fully static (built once in `ui`), so each output
          # is bound to a literal table name via `local()`.
          for (name in table_names) {
            local({
              tbl_name <- name

              output[[paste0("active_badge_", tbl_name)]] <- shiny::renderUI({
                if (identical(active_table_name(), tbl_name)) {
                  shiny::tags$span(class = "badge bg-primary ms-2", "Active")
                }
              })

              output[[paste0("dt_", tbl_name)]] <- DT::renderDT({
                df <- qc_vals$.tables[[tbl_name]]$df()
                if (inherits(df, "tbl_sql")) {
                  df <- dplyr::collect(df)
                }
                DT::datatable(
                  df,
                  fillContainer = TRUE,
                  options = list(pageLength = 25, scrollX = TRUE)
                )
              })

              output[[paste0("sql_view_", tbl_name)]] <- shiny::renderUI({
                bslib::input_code_editor(
                  paste0("sql_view_editor_", tbl_name),
                  value = sql_text_for_editor(tbl_name),
                  language = "sql",
                  read_only = TRUE,
                  line_numbers = FALSE,
                  height = "auto"
                )
              })
            })
          }
        }

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

      shiny::shinyApp(
        ui,
        server,
        enableBookmarking = if (enable_shiny_bookmarking) {
          "server"
        } else {
          "disable"
        }
      )
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
    #' Create a full-window page containing the querychat UI.
    #'
    #' This wraps [shinychat::page_chat()], making the chat the primary
    #' surface of the app, with optional navigation pages, sidebars, and a
    #' drawer. Use this instead of `$sidebar()` or `$ui()` when the chat
    #' should own the full browser window.
    #'
    #' @param title Page title displayed in the header. When it is a string
    #'   and `window_title` is omitted, it is also used as the document title.
    #' @param ... Additional arguments passed to [shinychat::page_chat()].
    #' @param id Optional ID for the QueryChat instance.
    #'
    #' @return A fillable page UI component suitable for use as the app's UI.
    page = function(title, ..., id = NULL) {
      check_string(id, allow_null = TRUE, allow_empty = FALSE)

      id <- id %||% namespaced_id(self$id)

      ns <- shiny::NS(id)
      # Extras must ride in the footer slot; tagList() siblings of
      # page_chat() would render outside <body>.
      dots <- add_footer_and_class(rlang::list2(...), ns)
      rlang::exec(
        shinychat::page_chat,
        title,
        !!!dots,
        id = ns("chat")
      )
    },

    #' @description
    #' Initialize the querychat server logic.
    #'
    #' @param data_source Optional data source to register for this session
    #'   only, for the deferred pattern where the source can't be created
    #'   until the server function runs (for example a per-user database
    #'   connection). The instance's own tables are not modified; a
    #'   same-named instance table is shadowed for this session; any
    #'   connection querychat created for it is cleaned up when the session
    #'   ends.
    #' @param client Optional chat client override for this session.
    #' @param history Conversation history configuration for this call. Overrides
    #'   the value set on `$new()`. Resolves to `TRUE` when neither this nor the
    #'   constructor's `history` was set.
    #' @param enable_bookmarking `r lifecycle::badge("deprecated")` Use `history =
    #'   shinychat::history_options(restore_mode = "bookmark")` instead (set on
    #'   `$new()`, or passed here).
    #' @param ... Ignored.
    #' @param table_name Table name to register `data_source` under. Only
    #'   used when `data_source` is provided. Named-only (placed after `...`)
    #'   so it can't shift the meaning of existing positional calls.
    #' @param id Optional module ID override.
    #' @param session The Shiny session object.
    #'
    #' @return A list containing session-specific reactive values and the chat
    #'   client. For single-table usage, includes `df`, `sql`, `title` directly.
    #'   For multi-table, use `qc_vals$table("name")` to get a [TableAccessor]
    #'   with per-table reactive state. Also includes `table_names()` to list tables.
    #'   `current_table()` returns the name of the most recently queried table,
    #'   or `NULL` before any query.
    server = function(
      data_source = NULL,
      client = NULL,
      history = NULL,
      enable_bookmarking = NULL,
      ...,
      table_name = NULL,
      id = NULL,
      session = shiny::getDefaultReactiveDomain()
    ) {
      check_string(table_name, allow_null = TRUE, allow_empty = FALSE)
      check_string(id, allow_null = TRUE, allow_empty = FALSE)
      check_dots_empty()

      if (is.null(session)) {
        cli::cli_abort(
          "{.fn $server} must be called within a Shiny server function"
        )
      }

      table_set <- private$.table_set
      greeting_tables <- self$greeter$tables
      session_source <- NULL

      if (!is.null(data_source)) {
        tbl_name <- table_name %||% private$.deferred_table_name
        if (is.null(tbl_name)) {
          existing_tables <- names(private$data_sources())
          if (length(existing_tables) > 0) {
            tbl_name <- existing_tables[[1]]
          }
        }
        if (is.null(tbl_name)) {
          cli::cli_abort(
            c(
              "{.arg table_name} is required when {.arg data_source} is provided and no table name can be inferred.",
              "i" = "Pass {.arg table_name} to {.fn $server}, or {.arg table_name} to {.fn QueryChat$new}, or register a table first with {.fn $add_table}."
            )
          )
        }
        check_sql_table_name(tbl_name)
        if (
          is_data_source(data_source) &&
            !identical(data_source$table_name, tbl_name)
        ) {
          cli::cli_abort(
            c(
              "{.arg data_source}'s own table name ({.val {data_source$table_name}}) does not match the given {.arg table_name} ({.val {tbl_name}}).",
              "i" = "Pass a matching {.arg table_name}, or omit it to use {.val {data_source$table_name}}."
            )
          )
        }
        session_source <- normalize_data_source(data_source, tbl_name)
        next_sources <- private$data_sources()
        next_sources[[tbl_name]] <- session_source
        table_set <- tryCatch(
          private$build_table_set(
            next_sources,
            data_description = private$resolve_data_description(next_sources)
          ),
          error = function(e) {
            if (!inherits(data_source, "DataSource")) {
              session_source$cleanup()
            }
            stop(e)
          }
        )
        if (!tbl_name %in% greeting_tables) {
          greeting_tables <- c(greeting_tables, tbl_name)
        }
      }

      if (is.null(table_set)) {
        private$require_table_set("$server")
      }

      if (!is.null(session_source)) {
        session_table_set <- table_set
        # Mirrors the tryCatch() guard above: querychat only owns (and so
        # only closes) sources it normalized itself from a raw connection or
        # data.frame, never a DataSource the caller constructed and passed in.
        owns_session_source <- !inherits(data_source, "DataSource")
        session$onSessionEnded(function() {
          warn_on_cleanup_failure(
            session_table_set$cleanup_executor(),
            "session query executor"
          )
          if (owns_session_source) {
            warn_on_cleanup_failure(
              session_source$cleanup(),
              "session data source"
            )
          }
        })
      }

      resolved_client_spec <- client %||% private$.client_spec
      base_client <- as_querychat_client(resolved_client_spec)

      create_session_client <- function(...) {
        private$create_session_client(
          table_set = table_set,
          client_spec = base_client,
          ...
        )
      }

      check_history(history)

      if (!is.null(enable_bookmarking)) {
        lifecycle::deprecate_warn(
          when = "0.4.0",
          what = "QueryChat$server(enable_bookmarking = )",
          with = "QueryChat$server(history = )",
          details = 'Use history = shinychat::history_options(restore_mode = "bookmark") for the equivalent behavior.'
        )
      }

      resolved_history <- history %||%
        self$history %||%
        (if (isTRUE(enable_bookmarking)) {
          shinychat::history_options(restore_mode = "bookmark")
        }) %||%
        TRUE

      private$.sessions_started <- TRUE
      mod_server(
        id %||% self$id,
        table_set = table_set,
        greeting = self$greeting,
        client = create_session_client,
        tools = self$tools,
        history = resolved_history,
        greeter = self$greeter,
        greeting_base = base_client,
        greeting_tables = greeting_tables
      )
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
    #' Clean up resources this object created.
    #'
    #' Closes the query executors and data-source connections querychat opened
    #' (in-memory DuckDB), including those of table sets superseded by a late
    #' `$add_table()`. Connections you passed in are never closed.
    #'
    #' @return Invisibly returns `NULL`.
    cleanup = function() {
      for (ts in private$.superseded_table_sets) {
        warn_on_cleanup_failure(ts$cleanup_executor(), "query executor")
      }
      private$.superseded_table_sets <- list()
      if (!is.null(private$.table_set)) {
        warn_on_cleanup_failure(
          private$.table_set$cleanup_executor(),
          "query executor"
        )
        for (source in private$.table_set$data_sources) {
          warn_on_cleanup_failure(source$cleanup(), "data source")
        }
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
        client_factory <- function(
          tables,
          prompt,
          base = NULL,
          table_set = NULL
        ) {
          ts <- table_set %||% private$.table_set
          sp <- QueryChatSystemPrompt$new(
            prompt_template = prompt,
            data_sources = if (is.null(ts)) list() else ts$data_sources,
            data_description = if (is.null(ts)) {
              private$.data_description
            } else {
              ts$data_description
            },
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
      private$require_table_set("$system_prompt")$system_prompt$render(
        tools = self$tools
      )
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
#' @param id Optional module ID for the QueryChat instance.
#' @param greeting Optional initial message to display to users.
#' @param history Conversation history configuration. See [QueryChat]'s
#'   `$new()` method.
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
  history = NULL,
  client = NULL,
  tools = c("filter", "query", "visualize"),
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
    history = history,
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
#' @param history Conversation history configuration for the generated app. See
#'   [QueryChat]'s `$app()` method.
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
  tools = c("filter", "query", "visualize"),
  data_description = NULL,
  categorical_threshold = 20,
  extra_instructions = NULL,
  prompt_template = NULL,
  data_dict = NULL,
  cleanup = NA,
  history = NULL
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

  qc$app(history = history)
}

show_query_footer <- function(target, content, right = NULL) {
  bslib::card_footer(
    shiny::div(
      class = "querychat-footer-buttons",
      shiny::div(
        class = "querychat-footer-left",
        shiny::tags$button(
          class = "querychat-show-query-btn",
          `data-querychat-action` = "show-query",
          `data-target` = target,
          bsicons::bs_icon("chevron-down", class = "querychat-query-chevron"),
          shiny::tags$span(class = "querychat-query-label", "Show Query")
        )
      ),
      shiny::div(class = "querychat-footer-right", right)
    ),
    shiny::div(class = "querychat-query-section", id = target, content),
    viz_dep()
  )
}

normalize_tools <- function(tools) {
  if (is.null(tools)) {
    return(NULL)
  }
  tools[tools == "filter"] <- "update"
  unique(tools)
}

check_viz_deps <- function(tools) {
  if (
    is.null(tools) || !"visualize" %in% tools || rlang::is_installed("ggsql")
  ) {
    return(tools)
  }
  rlang::warn(
    c(
      'The "visualize" tool requires the {.pkg ggsql} package.',
      "i" = 'Install it with `install.packages("ggsql")`; continuing without the "visualize" tool.'
    ),
    .frequency = "once",
    .frequency_id = "querychat_viz_ggsql_missing"
  )
  setdiff(tools, "visualize")
}

# Runs one teardown step, warning instead of erroring so the rest still runs.
warn_on_cleanup_failure <- function(expr, what) {
  tryCatch(
    expr,
    error = function(e) {
      cli::cli_warn("Failed to clean up {what}: {conditionMessage(e)}")
    }
  )
  invisible(NULL)
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
