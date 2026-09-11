from pathlib import Path

from querychat import QueryChat
from querychat.data import titanic
from shinychat import chat_nav_panel

from shiny import App, render, ui

greeting = Path(__file__).parent / "greeting.md"

# 1. Provide data source to QueryChat
qc = QueryChat(titanic(), "titanic", greeting=greeting)

# 2. Create a chat-first page (the chat owns the full window), with the
#    reactive data view on a secondary page
app_ui = qc.page(
    "Titanic Explorer",
    pages_navbar=[
        chat_nav_panel(
            "Data",
            ui.card(
                ui.card_header(ui.output_text("title")),
                ui.output_data_frame("data_table"),
                fill=True,
            ),
            value="data",
            sidebar=False,
            content_width="100%",
        ),
    ],
)


def server(input, output, session):
    # 3. Add server logic (to get reactive data frame and title)
    qc_vals = qc.server()

    # 4. Use the filtered/sorted data frame reactively
    @render.data_frame
    def data_table():
        return qc_vals.df()

    @render.text
    def title():
        return qc_vals.title() or "Titanic Dataset"


app = App(app_ui, server)
