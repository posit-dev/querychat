"""
Streamlit example app for querychat.

Run with: streamlit run 04-streamlit-app.py
Requires: pip install streamlit (or uv sync --group streamlit)
"""

from querychat.data import titanic
from querychat.streamlit import QueryChat

qc = QueryChat(titanic(), "titanic")
qc.app()
