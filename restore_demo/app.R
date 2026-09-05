# R demo for verifying handoff restore + download regeneration.
#
# Serve from the repo root (with the branch loaded/installed):
#   shiny::runApp("restore_demo/app.R", port = 8082)
#
# history = TRUE => shinychat history with restore_mode = "browser"
# (localStorage), so reloading the page restores the conversation
# automatically. (The $app_obj() default is restore_mode = "bookmark", which
# needs server-side bookmarking; TRUE keeps reload-restore simple.)

library(querychat)

qc <- QueryChat$new(
  mtcars,
  "mtcars",
  greeting = "Ask me about mtcars. Try a visualization, then /handoff.",
  tools = c("filter", "query", "visualize")
)

qc$app_obj(history = TRUE)
