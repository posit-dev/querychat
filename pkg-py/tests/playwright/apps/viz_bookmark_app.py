"""Test app for viz bookmark restore: uses server-side bookmarking to avoid URL length limits."""

from querychat import QueryChat
from querychat.data import titanic

from shiny import App, ui

qc = QueryChat(
    titanic(),
    "titanic",
    tools=("query", "visualize"),
)


def app_ui(request):
    return ui.page_fillable(
        qc.ui(),
    )


def server(input, output, session):
    qc.server(enable_bookmarking=True)


app = App(app_ui, server, bookmark_store="server")
