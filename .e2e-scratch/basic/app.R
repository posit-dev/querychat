library(querychat)
library(palmerpenguins)

qc <- QueryChat$new(
  penguins,
  greeting = "Ask me about the penguins data. I can filter or run SQL queries.",
  client = "anthropic/claude-haiku-4-5"
)
qc$app()
