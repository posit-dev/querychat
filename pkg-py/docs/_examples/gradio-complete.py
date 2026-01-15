import plotly.express as px
from querychat.data import titanic
from querychat.gradio import QueryChat
from querychat.types import AppStateDict

import gradio as gr

qc = QueryChat(titanic(), "titanic")

with gr.Blocks(title="Titanic Explorer") as app:
    gr.Markdown("# Titanic Dataset Explorer")

    with gr.Row():
        with gr.Column(scale=1):
            state = qc.ui()

        with gr.Column(scale=2):
            title_display = gr.Markdown("## All Data")

            with gr.Row():
                passengers_box = gr.Textbox(label="Passengers", interactive=False)
                survivors_box = gr.Textbox(label="Survivors", interactive=False)
                rate_box = gr.Textbox(label="Survival Rate", interactive=False)

            with gr.Row():
                plot1 = gr.Plot()
                plot2 = gr.Plot()

    def update_all(state_dict: AppStateDict):
        df = qc.df(state_dict).to_pandas()
        title = qc.title(state_dict) or "All Data"

        # Metrics
        n_passengers = str(len(df))
        n_survivors = str(int(df["survived"].sum()))
        survival_rate = f"{df['survived'].mean():.1%}"

        # Visualizations
        fig1 = px.histogram(
            df, x="age", color="survived", title="Age Distribution by Survival"
        )
        fig2 = px.bar(
            df.groupby("pclass")["survived"].mean().reset_index(),
            x="pclass",
            y="survived",
            title="Survival by Class",
        )

        return (
            f"## {title}",
            n_passengers,
            n_survivors,
            survival_rate,
            fig1,
            fig2,
        )

    state.change(
        fn=update_all,
        inputs=[state],
        outputs=[
            title_display,
            passengers_box,
            survivors_box,
            rate_box,
            plot1,
            plot2,
        ],
    )

app.launch(css=qc.css, head=qc.head)
