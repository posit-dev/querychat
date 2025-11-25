from seaborn import load_dataset
from shiny.express import render, ui
from querychat.express import QueryChat

titanic = load_dataset("titanic")

# 1. Provide data source to QueryChat
qc = QueryChat(titanic, "titanic")

# 2. Add sidebar chat control
qc.sidebar()

# 3. Add a card with reactive title and data frame
with ui.card():
    with ui.card_header():
        @render.text
        def title():
            return qc.title() or "Titanic Dataset"

    @render.data_frame
    def data_table():
        return qc.df()
    
# 4. Set some page options (optional)
ui.page_opts(
    fillable=True,
    title="Titanic Dataset Explorer"
)
