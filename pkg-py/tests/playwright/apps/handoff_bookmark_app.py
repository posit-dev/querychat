from pathlib import Path

from querychat import QueryChat
from querychat.data import titanic

from shiny import App, reactive, ui

greeting = Path(__file__).parents[3] / "examples" / "greeting.md"
qc = QueryChat(titanic(), "titanic", greeting=greeting)


def app_ui(request):
    return ui.page_fillable(
        qc.ui(),
        ui.input_action_button("bookmark_now", "Bookmark"),
    )


def server(input, output, session):
    qc.server(history=False)

    @reactive.effect
    @reactive.event(input.bookmark_now)
    async def bookmark_now():
        await session.bookmark()


app = App(app_ui, server, bookmark_store="server")
