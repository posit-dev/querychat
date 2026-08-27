library(querychat)

qc <- QueryChat$new(
  mtcars,
  "mtcars",
  greeting = "Ask me about mtcars. I can make charts too.",
  client = "anthropic/claude-haiku-4-5",
  tools = c("filter", "query", "visualize")
)
qc$app()
