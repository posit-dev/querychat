# Smoke test for the drawer-based $app() layout (branch: drawer-app).
#
# What to verify:
#   1. App opens as a chat-primary page (no sidebar dashboard).
#   2. The data drawer starts closed.
#   3. Ask "What are the first 5 rows?" (or any filtering question) -- when the
#      LLM runs a query, the drawer auto-opens with the SQL editor + data table.
#   4. "Reset Query" clears the query; the drawer stays open showing full data.
#   5. The drawer is resizable via its left edge.
#
# Run with the package loaded from this branch (e.g. pkgload::load_all()).
library(querychat)
library(palmerpenguins)

qc <- QueryChat$new(
  penguins,
  greeting = "Ask me anything about the Palmer Penguins dataset!"
)
qc$app()
