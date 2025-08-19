#' A Simple App for Chatting with Data
#'
#' Creates a Shiny app that allows users to interact with a data source using
#' natural language queries. The app uses a pre-configured Shiny app built on
#' [querychat_sidebar()] and [querychat_server()] to provide a quick-and-easy
#' way to chat with your data.
#'
#' @examplesIf rlang::is_interactive()
#' # Pass in a data frame to start querychatting
#' querychat_app(mtcars)
#'
#' # Or choose your LLM client using ellmer::chat_*() functions
#' querychat_app(mtcars, client = ellmer::chat_anthropic())
#'
#' @param config A `querychat_config` object or a data source that can be used
#'   to create one.
#' @param ... Additional arguments passed to [querychat_init()] if `config` is
#'   not already a `querychat_config` object.
#' @inheritParams shinychat::chat_app
#'
#' @return Invisibly returns the `chat` object containing the chat history.
#'
#' @export
querychat_app <- function(config, ..., bookmark_store = "url") {
  rlang::check_installed("DT")
  rlang::check_installed("bsicons")

  if (!inherits(config, "querychat_config")) {
    if (inherits(config, "querychat_data_source")) {
      data_source <- config
    } else {
      data_source <- querychat_data_source(
        config,
        table_name = deparse(substitute(config))
      )
    }
    config <- querychat_init(data_source, ...)
  }

  ui <- function(req) {
    bslib::page_sidebar(
      title = shiny::HTML(paste0(
        "<span>querychat with <code>",
        config$data_source$table_name,
        "</code></span>"
      )),
      class = "bslib-page-dashboard",
      sidebar = querychat_sidebar("chat"),
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
    qc <- querychat_server("chat", config)
    chat <<- qc$chat

    output$query_title <- shiny::renderText({
      if (shiny::isTruthy(qc$title())) {
        qc$title()
      } else {
        "SQL Query"
      }
    })

    output$ui_reset <- shiny::renderUI({
      shiny::req(qc$sql())

      shiny::actionButton(
        "reset_query",
        label = "Reset Query",
        class = "btn btn-outline-danger btn-sm lh-1"
      )
    })

    shiny::observeEvent(input$reset_query, {
      qc$update_query("", NULL)
    })

    output$dt <- DT::renderDT({
      DT::datatable(qc$df())
    })

    output$sql_output <- shiny::renderUI({
      sql <- if (shiny::isTruthy(qc$sql())) {
        qc$sql()
      } else {
        paste("SELECT * FROM", config$data_source$table_name)
      }

      sql_code <- paste(c("```sql", sql, "```"), collapse = "\n")

      shinychat::output_markdown_stream(
        "sql_code",
        content = sql_code,
        auto_scroll = FALSE,
        width = "100%"
      )
    })

    shiny::observeEvent(input$close_btn, {
      shiny::stopApp()
    })
  }

  app <- shiny::shinyApp(ui, server, enableBookmarking = bookmark_store)
  tryCatch(shiny::runGadget(app), interrupt = function(cnd) NULL)
  invisible(chat)
}
