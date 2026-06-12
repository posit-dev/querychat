# Dashboard drawer demo. Run: shiny run pkg-py/examples/11-dashboard-app.py

from querychat import QueryChat
from querychat.data import titanic

from shiny import App, render, ui

qc = QueryChat(
    titanic(),
    "titanic",
    client="anthropic/claude-sonnet-4-6",
    tools=("filter", "query", "visualize", "canvas"),
    greeting=(
        "Ask about the Titanic data — try pinning results or charts, "
        "then say `/dashboard` to open the dashboard drawer."
    ),
)

app_ui = ui.page_sidebar(
    qc.sidebar(),
    ui.card(
        ui.card_header(ui.output_text("title")),
        ui.output_data_frame("table"),
        fill=True,
    ),
    fillable=True,
    title="QueryChat Dashboard Demo",
)


def server(input, output, session):
    vals = qc.server()

    @render.text
    def title():
        return vals.title() or "All data"

    @render.data_frame
    def table():
        return vals.df()


app = App(app_ui, server)
