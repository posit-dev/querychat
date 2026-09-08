# Like apps/handoff/app.R, but with browser-mode history enabled so the
# handoff snapshot round-trips through shinychat's conversation record
# across a page reload. shinychat's browser-mode store writes a
# `.shinychat/` directory next to this file; tests must clean it up.

library(shiny)
library(bslib)
library(querychat)

ContentJsonClass <- asNamespace("ellmer")[["ContentJson"]]

delayed_value <- function(value, delay = 0.15) {
  promises::promise(function(resolve, reject) {
    later::later(function() resolve(value), delay = delay)
  })
}

handoff_source_lines <- function(marker = NULL) {
  paste(
    "---",
    "title: Sales Handoff",
    "---",
    "",
    if (!is.null(marker)) paste0("<!-- ", marker, " -->") else "",
    "",
    "```{r}",
    "#| label: setup",
    "library(DBI)",
    "```",
    "",
    "```{r}",
    "#| label: sales-by-region",
    "dbGetQuery(con, 'select region, sum(amount) from sales group by region')",
    "```",
    sep = "\n"
  )
}

state <- new.env(parent = emptyenv())
state$recommendation <- list(
  selected_ids = "query-0",
  format_id = "quarto-dashboard",
  directions = "Keep it short."
)
state$responses <- list(
  list(
    source = handoff_source_lines(),
    language = "r",
    summary = "A dashboard summarizing sales.",
    run_instructions = "Run with `quarto preview handoff.qmd`.",
    referenced_tables = "sales"
  ),
  list(
    source = handoff_source_lines("RESTORED_REVISION"),
    language = "r",
    summary = "A revised dashboard summarizing sales.",
    run_instructions = "Run with `quarto preview handoff.qmd`.",
    referenced_tables = "sales"
  )
)

HandoffTestChat <- R6::R6Class(
  "HandoffTestChat",
  inherit = asNamespace("ellmer")[["Chat"]],
  public = list(
    state = NULL,

    initialize = function(state, ...) {
      self$state <- state
      super$initialize(...)
    },

    stream_async = function(
      ...,
      type = NULL,
      tool_mode = c("concurrent", "sequential"),
      stream = c("text", "content"),
      controller = NULL
    ) {
      if (!is.null(type)) {
        return(private$stream_structured())
      }
      private$stream_main()
    },

    chat_structured_async = function(..., type, echo = "none", convert = TRUE) {
      delayed_value(self$state$recommendation, delay = 0.4)
    },

    chat_async = function(..., echo = "none") {
      promises::promise_resolve("Sales handoff")
    }
  ),
  private = list(
    stream_structured = function() {
      responses <- self$state$responses
      item <- responses[[1]]
      self$state$responses <- responses[-1]

      json_text <- as.character(jsonlite::toJSON(item, auto_unbox = TRUE))
      content_json <- ContentJsonClass(data = item, string = NULL)
      user_turn <- ellmer::UserTurn("handoff request")
      assistant_turn <- ellmer::AssistantTurn(list(content_json))
      self$add_turn(user_turn, assistant_turn, log_tokens = FALSE)

      list(delayed_value(json_text, delay = 0.1))
    },

    stream_main = function() {
      request <- ellmer::ContentToolRequest(
        id = "query-call",
        name = "querychat_query",
        arguments = list(
          query = "SELECT * FROM sales",
          title = "All sales"
        )
      )
      result <- ellmer::ContentToolResult(
        value = '[{"amount":10},{"amount":20},{"amount":30}]',
        request = request
      )
      user_turn <- ellmer::UserTurn("Show me the sales data")
      assistant_turn <- ellmer::AssistantTurn(
        list(result, ellmer::ContentText("Here are the sales results."))
      )
      self$add_turn(user_turn, assistant_turn, log_tokens = FALSE)
      "Here are the sales results."
    }
  )
)

sales <- data.frame(
  amount = c(10, 20, 30),
  region = c("east", "west", "east"),
  stringsAsFactors = FALSE
)

qc <- QueryChat$new(
  sales,
  "sales",
  id = "mod1",
  greeting = "Welcome!",
  client = HandoffTestChat$new(
    state,
    ellmer::Provider("test", "test"),
    model = ellmer::Model(name = "test")
  ),
  history = TRUE
)

ui <- page_fluid(
  card(card_header("Module"), qc$ui(), height = "600px")
)

server <- function(input, output, session) {
  qc$server()
}

shinyApp(ui, server)
