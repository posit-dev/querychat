import chatlas
from seaborn import load_dataset
from shiny import App, render, ui

import querychat

titanic = load_dataset("titanic")

# 1. Configure querychat.
#    This is where you specify the dataset and can also
#    override options like the greeting message, system prompt, model, etc.


def use_github_models(system_prompt: str) -> chatlas.Chat:
    # GitHub models give us free rate-limited access to the latest LLMs
    # you will need to have GITHUB_PAT defined in your environment
    return chatlas.ChatGithub(
        model="gpt-4.1",
        system_prompt=system_prompt,
    )


qc_config = querychat.init(
    data_source=titanic,
    table_name="titanic",
    client=use_github_models,
)

# Create UI
app_ui = ui.page_sidebar(
    # 2. Use querychat.sidebar(id) in a ui.page_sidebar.
    #    Alternatively, use querychat.ui(id) elsewhere if you don't want your
    #    chat interface to live in a sidebar.
    querychat.sidebar("chat"),
    ui.card(
      ui.card_header("Titanic Data"),
      ui.output_data_frame("data_table"),
      fill=True,
    ),
    fillable=True,
    class_="bslib-page-dashboard"
)


# Define server logic
def server(input, output, session):
    # 3. Create a querychat object using the config from step 1.
    qc = querychat.server("chat", qc_config)

    # 4. Use the filtered/sorted data frame anywhere you wish, via the
    #    chat.df() reactive.
    @render.data_frame
    def data_table():
        return qc.df()


# Create Shiny app
app = App(app_ui, server)
