library(querychat)

qc <- QueryChat$new(
  mtcars,
  "mtcars",
  greeting = "Ask me about mtcars.",
  client = "anthropic/claude-haiku-4-5"
)
qc$app_obj(history = shinychat::history_options(restore_mode = "bookmark"))
