"""
Gradio example with custom UI layout.

Uses `.ui()` which returns gr.State for wiring state changes to custom components.

Run with: python 07-gradio-custom-app.py
Requires: pip install gradio (or uv sync --group gradio)
"""

from pathlib import Path

import gradio as gr

from querychat.data import titanic
from querychat.gradio import QueryChat
from querychat.types import AppStateDict

greeting = Path(__file__).parent / "greeting.md"

qc = QueryChat(titanic(), "titanic", greeting=greeting)

with gr.Blocks(title="Titanic Explorer") as app:
    gr.Markdown("# Titanic Data Explorer")

    with gr.Row():
        with gr.Column(scale=1):
            state = qc.ui()

        with gr.Column(scale=2):
            with gr.Group():
                query_title = gr.Markdown("### Full Dataset")
                sql_display = gr.Code(
                    value="SELECT * FROM titanic",
                    language="sql",
                    label="Current Query",
                    interactive=False,
                )

            with gr.Row():
                row_count = gr.Textbox(label="Rows", interactive=False)
                col_count = gr.Textbox(label="Columns", interactive=False)

            data_table = gr.Dataframe(label="Data Preview", interactive=False, wrap=True)

    def update_display(state_dict: AppStateDict):
        df = qc.df(state_dict)
        sql = qc.sql(state_dict)
        title = qc.title(state_dict)

        # Convert narwhals DataFrame to native (pandas) for Gradio compatibility
        display_df = df.head(100).to_native()
        return (
            f"### {title or 'Full Dataset'}",
            sql or "SELECT * FROM titanic",
            f"{df.shape[0]:,}",
            str(df.shape[1]),
            display_df,
        )

    state.change(
        fn=update_display,
        inputs=[state],
        outputs=[query_title, sql_display, row_count, col_count, data_table],
    )
    app.load(
        fn=update_display,
        inputs=[state],
        outputs=[query_title, sql_display, row_count, col_count, data_table],
    )

# Pass qc.css and qc.head to enable clickable suggestions
if __name__ == "__main__":
    app.launch(css=qc.css, head=qc.head)
