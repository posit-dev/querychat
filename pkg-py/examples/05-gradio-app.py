"""
Gradio example app for querychat.

Run with: python 05-gradio-app.py
Requires: pip install gradio (or uv sync --group gradio)
"""

from pathlib import Path

from querychat.data import titanic
from querychat.gradio import QueryChat

greeting = Path(__file__).parent / "greeting.md"

qc = QueryChat(titanic(), "titanic", greeting=greeting)
app = qc.app()

if __name__ == "__main__":
    app.launch()
