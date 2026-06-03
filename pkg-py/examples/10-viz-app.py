from pathlib import Path

from querychat.express import QueryChat
from querychat.data import titanic

from shiny.express import ui, app_opts

app_opts(bookmark_store="server")

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
