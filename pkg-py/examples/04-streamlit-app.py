"""
Streamlit example app for querychat.

Run this app with:
    streamlit run 04-streamlit-app.py

Note: This requires streamlit to be installed:
    pip install streamlit
    # or
    uv pip install --group streamlit
"""

from querychat import QueryChat
from querychat.data import titanic

# 1. Create QueryChat instance with data
qc = QueryChat(titanic(), "titanic")

# 2. Call streamlit_app() to create the Streamlit interface
qc.streamlit_app()
