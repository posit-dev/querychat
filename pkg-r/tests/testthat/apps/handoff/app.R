library(shiny)
library(bslib)
library(querychat)

ContentJsonClass <- asNamespace("ellmer")[["ContentJson"]]
ModelClass <- asNamespace("ellmer")[["Model"]]

# Wrap a value in a promise that resolves after `delay` seconds so streamed
# chunks arrive as separate WebSocket frames instead of all at once, letting
# the browser observe intermediate state (spinner, partial source).
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
    "#| label: sales-summary",
    "dbGetQuery(con, 'select amount, region from sales')",
    "```",
    "",
    "```{r}",
    "#| label: sales-by-region",
    "dbGetQuery(con, 'select region, sum(amount) from sales group by region')",
    "```",
    sep = "\n"
  )
}

new_handoff_test_state <- function(fail_recommendation = FALSE) {
  state <- new.env(parent = emptyenv())
  state$fail_recommendation <- fail_recommendation
  state$recommendation <- list(
    selected_ids = "query-0",
    format_id = "quarto-dashboard",
    directions = "Keep it short."
  )
  # Consumed in order: first by $generate(), then by $revise().
  state$responses <- list(
    list(
      source = handoff_source_lines(),
      language = "r",
      summary = "A dashboard summarizing sales.",
      run_instructions = "Run with `quarto preview handoff.qmd`.",
      referenced_tables = "sales"
    ),
    list(
      source = handoff_source_lines("BROWSER_HISTORY"),
      language = "r",
      summary = "A revised dashboard summarizing sales.",
      run_instructions = "Run with `quarto preview handoff.qmd`.",
      referenced_tables = "sales"
    )
  )
  state
}

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
      if (isTRUE(self$state$fail_recommendation)) {
        return(promises::promise_reject(
          simpleError("The recommendation model is unavailable.")
        ))
      }
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
      breaks <- unique(round(seq(1, nchar(json_text) + 1, length.out = 5)))
      chunks <- lapply(
        seq_len(length(breaks) - 1L),
        function(i) {
          delayed_value(
            substr(json_text, breaks[i], breaks[i + 1L] - 1L),
            # Cumulative, not per-chunk: all promises are created up front,
            # so equal per-chunk delays would all fire in the same instant.
            delay = i * 0.1
          )
        }
      )

      content_json <- ContentJsonClass(data = item, string = NULL)
      user_turn <- ellmer::UserTurn("handoff request")
      assistant_turn <- ellmer::AssistantTurn(list(content_json))
      self$add_turn(user_turn, assistant_turn, log_tokens = FALSE)

      chunks
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
        value = data.frame(amount = c(10, 20, 30)),
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

new_handoff_test_chat <- function(state) {
  HandoffTestChat$new(
    state,
    ellmer::Provider("test", "test", "test"),
    model = ModelClass(name = "test", params = list(), extra_args = list())
  )
}

sales <- data.frame(
  amount = c(10, 20, 30),
  region = c("east", "west", "east"),
  stringsAsFactors = FALSE
)

state_one <- new_handoff_test_state()
state_two <- new_handoff_test_state(fail_recommendation = TRUE)

qc_one <- QueryChat$new(
  sales,
  "sales",
  id = "mod1",
  greeting = "Welcome to module one!",
  client = new_handoff_test_chat(state_one),
  history = FALSE
)
qc_two <- QueryChat$new(
  sales,
  "sales",
  id = "mod2",
  greeting = "Welcome to module two!",
  client = new_handoff_test_chat(state_two),
  history = FALSE
)

ui <- page_fluid(
  layout_columns(
    card(card_header("Module one"), qc_one$ui(), height = "600px"),
    card(card_header("Module two"), qc_two$ui(), height = "600px")
  )
)

server <- function(input, output, session) {
  qc_one$server()
  qc_two$server()
}

shinyApp(ui, server)
