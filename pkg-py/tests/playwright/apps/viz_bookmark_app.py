"""Test app for viz bookmark restore: uses server-side bookmarking to avoid URL length limits."""

from pathlib import Path

from querychat import QueryChat
from querychat.data import titanic

from shiny import App, ui

greeting = Path(__file__).parents[3] / "examples" / "greeting-viz.md"

qc = QueryChat(
    titanic(),
    "titanic",
    greeting=greeting,
    tools=("query", "visualize"),
)


def app_ui(request):
    return ui.page_fillable(
        qc.ui(),
    )


def server(input, output, session):
    qc.server(enable_bookmarking=True)


app = App(app_ui, server, bookmark_store="server")
