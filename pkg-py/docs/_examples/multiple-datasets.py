from seaborn import load_dataset
from shiny.express import render, ui
from querychat.express import QueryChat
from querychat.data import titanic

penguins = load_dataset("penguins")

qc_titanic = QueryChat(titanic(), "titanic")
qc_penguins = QueryChat(penguins, "penguins")

with ui.sidebar():
    with ui.panel_conditional("input.navbar == 'Titanic'"):
        qc_titanic.ui()
    with ui.panel_conditional("input.navbar == 'Penguins'"):
        qc_penguins.ui()

with ui.nav_panel("Titanic"):
    @render.data_frame
    def titanic_table():
        return qc_titanic.df()

with ui.nav_panel("Penguins"):
    @render.data_frame
    def penguins_table():
        return qc_penguins.df()

ui.page_opts(
    id="navbar",
    title="Multiple Datasets with querychat",
    fillable=True,
)
