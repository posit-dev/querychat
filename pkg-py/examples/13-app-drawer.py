# Smoke test for the drawer-based app() layout (branch: drawer-app).
#
# What to verify:
#   1. App opens as a chat-primary page (no sidebar dashboard).
#   2. The data drawer starts closed.
#   3. Ask "What are the first 5 rows?" (or any filtering question) -- when the
#      LLM runs a query, the drawer auto-opens with the SQL editor + data table.
#   4. "Reset Query" clears the query; the drawer stays open showing full data.
#   5. Drawer is resizable via its left edge.
#
# Run from pkg-py/ with the worktree's sources first on the path, using the
# project venv's Python (a bare `shiny` on PATH may come from another env):
#   PYTHONPATH=src /path/to/.venv/bin/python -m shiny run examples/13-app-drawer.py --reload
from pathlib import Path

from querychat import QueryChat
from querychat.data import titanic

greeting = Path(__file__).parent / "greeting.md"

qc = QueryChat(titanic(), "titanic", greeting=greeting)
app = qc.app()
