from querychat.express import QueryChat
from querychat.data import titanic

from shiny.express import ui, app_opts

# Omits "update" tool — this demo focuses on query + visualization only
qc = QueryChat(
    titanic(),
    "titanic",
    tools=("query", "visualize")
)

qc.ui()

ui.page_opts(fillable=True, title="QueryChat Visualization Demo")

app_opts(bookmark_store="url")
