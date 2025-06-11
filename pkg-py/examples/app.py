import chatlas
from seaborn import load_dataset
from shiny import App, render, ui

import querychat as qc

titanic = load_dataset("titanic")

# 1. Configure querychat. This is where you specify the dataset and can also
#    override options like the greeting message, system prompt, model, etc.


def use_github_models(system_prompt: str) -> chatlas.Chat:
    return chatlas.ChatGithub(
        model="gpt-4o",
        system_prompt=system_prompt,
    )


querychat_config = qc.init(
    data_source=titanic,
    table_name="titanic",
    greeting="Hello, welcome to querychat! Ask me about your data.",
    create_chat_callback=use_github_models,
)

# Create UI
app_ui = ui.page_sidebar(
    # 2. Use qc.sidebar(id) in a ui.page_sidebar.
    #    Alternatively, use qc.ui(id) elsewhere if you don't want your
    #    chat interface to live in a sidebar.
    qc.sidebar("chat"),
    ui.output_data_frame("data_table"),
)


# Define server logic
def server(input, output, session):
    # 3. Create a querychat object using the config from step 1.
    chat = qc.server("chat", querychat_config)

    # 4. Use the filtered/sorted data frame anywhere you wish, via the
    #    chat["df"]() reactive.
    @render.data_frame
    def data_table():
        return chat.df()


# Create Shiny app
app = App(app_ui, server)
