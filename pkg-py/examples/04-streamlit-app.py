"""
Streamlit example app for querychat.

Run with: streamlit run 04-streamlit-app.py
Requires: pip install streamlit (or uv sync --group streamlit)
"""

from pathlib import Path

from querychat.data import titanic
from querychat.streamlit import QueryChat

greeting = Path(__file__).parent / "greeting.md"

qc = QueryChat(titanic(), "titanic", greeting=greeting)
qc.app()
