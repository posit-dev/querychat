# Python demo for verifying handoff restore + download regeneration.
#
# Serve from the repo root:
#   .venv/bin/shiny run restore_demo/app.py --port 8080
# To run against the dev-branch shinychat instead of the installed one:
#   PYTHONPATH=/Users/cpsievert/github/shinychat/.worktrees/querychat-pr311-history-save/pkg-py/src \
#     .venv/bin/shiny run restore_demo/app.py --port 8081
#
# history=True => shinychat history with restore_mode="browser" (localStorage),
# so reloading the page restores the conversation automatically.

from querychat import QueryChat
from querychat.data import titanic

qc = QueryChat(
    titanic(),
    "titanic",
    greeting="Ask me about the Titanic passengers. Try a visualization, then /handoff.",
    tools=("filter", "query", "visualize"),
)

app = qc.app(history=True)
