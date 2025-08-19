from pathlib import Path

import chatlas
import querychat
from seaborn import load_dataset
from shiny import App, render, ui

titanic = load_dataset("titanic")

greeting = Path(__file__).parent / "greeting.md"
data_desc = Path(__file__).parent / "data_description.md"

# 1. Configure querychat

def use_github_models(system_prompt: str) -> chatlas.Chat:
    # GitHub models give us free rate-limited access to the latest LLMs
    # you will need to have GITHUB_PAT defined in your environment
    return chatlas.ChatGithub(
        model="gpt-4.1",
        system_prompt=system_prompt,
    )

qc_config = querychat.init(
    titanic,
    "titanic",
    greeting=greeting,
    data_description=data_desc,
    client=use_github_models,
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
    title="querychat with Python",
    fillable=True,
    class_="bslib-page-dashboard",
)


# Define server logic
def server(input, output, session):
    # 3. Initialize querychat server with the config from step 1
    qc = querychat.server("chat", qc_config)

    # 4. Display the filtered dataframe
    @render.data_frame
    def data_table():
        # Access filtered data via chat.df() reactive
        return qc.df()


# Create Shiny app
app = App(app_ui, server)
