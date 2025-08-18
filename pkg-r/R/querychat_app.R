querychat_app <- function(config, ..., bookmark_store = "url") {
  rlang::check_installed("DT")
  rlang::check_installed("bsicons")

  if (!inherits(config, "querychat_config")) {
    data_source <- querychat_data_source(
      config,
      table_name = deparse(substitute(config))
    )
    config <- querychat_init(data_source, ...)
  }

  ui <- function(req) {
    bslib::page_sidebar(
      sidebar = querychat_sidebar("chat"),
      bslib::card(
        fill = FALSE,
        style = bslib::css(max_height = "33%"),
        bslib::card_header(bsicons::bs_icon("terminal-fill"), "SQL Query"),
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

  app <- shiny::shinyApp(ui, server, ..., enableBookmarking = bookmark_store)
  tryCatch(shiny::runGadget(app), interrupt = function(cnd) NULL)
  invisible(chat)
}
