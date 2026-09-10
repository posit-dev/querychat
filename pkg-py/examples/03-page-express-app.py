from pathlib import Path

from querychat.data import titanic
from querychat.express import QueryChat
from shiny.express import render, ui
from shinychat import chat_nav_panel

greeting = Path(__file__).parent / "greeting.md"

# 1. Provide data source to QueryChat
qc = QueryChat(titanic(), "titanic", greeting=greeting)

# 2. Hold the reactive data view for the secondary page (page_chat() owns the
#    entire page, so outputs can't live at the top level)
with ui.hold() as data_view, ui.card(fill=True):
    with ui.card_header():

        @render.text
        def title():
            return qc.title() or "Titanic Dataset"

    @render.data_frame
    def data_table():
        return qc.df()


# 3. Create a chat-first page (the chat owns the full window)
qc.page(
    "Titanic Explorer",
    pages_navbar=[
        chat_nav_panel(
            "Data",
            data_view,
            value="data",
            sidebar=False,
            content_width="100%",
        ),
    ],
)
