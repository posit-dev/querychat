"""
Gradio example app for querychat.

Run with: python 05-gradio-app.py
Requires: pip install gradio (or uv sync --group gradio)
"""

from querychat.data import titanic
from querychat.gradio import QueryChat

qc = QueryChat(titanic(), "titanic")
qc.app().launch()
