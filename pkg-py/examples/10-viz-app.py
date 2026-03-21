from querychat import QueryChat
from querychat.data import titanic

from shiny import App, ui

# Omits "update" tool — this demo focuses on query + visualization only
qc = QueryChat(
    titanic(),
    "titanic",
    tools=("query", "visualize_query"),
)

app_ui = ui.page_fillable(
    qc.ui(),
)


def server(input, output, session):
    qc.server()


app = App(app_ui, server)
