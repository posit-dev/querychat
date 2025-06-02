from pathlib import Path

import querychat
from querychat.datasource import SQLAlchemySource
from seaborn import load_dataset
from shiny import App, render, ui
from sqlalchemy import create_engine

# Load titanic data and create SQLite database
db_path = Path(__file__).parent / "titanic.db"
engine = create_engine("sqlite:///" + str(db_path))

if not db_path.exists():
    # For example purposes, we'll create the database if it doesn't exist. Don't
    # do this in your app!
    titanic = load_dataset("titanic")
    titanic.to_sql("titanic", engine, if_exists="replace", index=False)

with open(Path(__file__).parent / "greeting.md", "r") as f:
    greeting = f.read()
with open(Path(__file__).parent / "data_description.md", "r") as f:
    data_desc = f.read()

# 1. Configure querychat
querychat_config = querychat.init(
    SQLAlchemySource(engine, "titanic"),
    greeting=greeting,
    data_description=data_desc,
)

# Create UI
app_ui = ui.page_sidebar(
    # 2. Place the chat component in the sidebar
    querychat.sidebar("chat"),
    # Main panel with data viewer
    ui.card(
        ui.output_data_frame("data_table"),
        fill=True,
    ),
    title="querychat with Python (SQLite)",
    fillable=True,
)


# Define server logic
def server(input, output, session):
    # 3. Initialize querychat server with the config from step 1
    chat = querychat.server("chat", querychat_config)

    # 4. Display the filtered dataframe
    @render.data_frame
    def data_table():
        # Access filtered data via chat.df() reactive
        return chat["df"]()


# Create Shiny app
app = App(app_ui, server)
