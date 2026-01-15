import plotly.express as px
from querychat.data import titanic
from querychat.gradio import QueryChat
from querychat.types import AppStateDict

import gradio as gr

qc = QueryChat(titanic(), "titanic")

with gr.Blocks() as app:
    with gr.Row():
        with gr.Column():
            state = qc.ui()

        with gr.Column():
            plot1 = gr.Plot(label="Age Distribution")
            plot2 = gr.Plot(label="Survival by Class")

    def update_views(state_dict: AppStateDict):
        df = qc.df(state_dict).to_pandas()
        fig1 = px.histogram(df, x="age", color="survived", title="Age Distribution")
        fig2 = px.bar(
            df.groupby("pclass")["survived"].mean().reset_index(),
            x="pclass", y="survived", title="Survival by Class"
        )
        return fig1, fig2

    state.change(fn=update_views, inputs=[state], outputs=[plot1, plot2])

app.launch(css=qc.css, head=qc.head)
