"""Test app for stream cancellation."""

from querychat import QueryChat
from querychat.data import titanic

from shiny import App, ui

qc = QueryChat(
    titanic(),
    "titanic",
    greeting="Ask me anything about the Titanic dataset.",
)


def app_ui(request):
    return ui.page_fillable(
        qc.ui(),
    )


def server(input, output, session):
    qc.server()


app = App(app_ui, server)
