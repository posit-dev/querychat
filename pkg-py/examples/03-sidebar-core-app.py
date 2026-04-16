from pathlib import Path

from shiny import App, render, ui
from querychat import QueryChat
from querychat.data import titanic

greeting = Path(__file__).parent / "greeting.md"

# 1. Provide data source to QueryChat
qc = QueryChat(titanic(), "titanic", greeting=greeting)

app_ui = ui.page_sidebar(
    # 2. Create sidebar chat control
    qc.sidebar(),
    ui.card(
        ui.card_header(ui.output_text("title")),
        ui.output_data_frame("data_table"),
        fill=True,
    ),
    fillable=True
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
