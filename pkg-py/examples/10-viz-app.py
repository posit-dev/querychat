from pathlib import Path

from querychat.data import titanic
from querychat.express import QueryChat
from shiny.express import ui

greeting = Path(__file__).parent / "greeting-viz.md"

# Omits "update" tool — this demo focuses on query + visualization only
qc = QueryChat(
    titanic(),
    "titanic",
    greeting=greeting,
    tools=("query", "visualize"),
)

qc.ui()

ui.page_opts(fillable=True, title="QueryChat Visualization Demo")
