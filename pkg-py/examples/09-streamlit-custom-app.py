"""
Streamlit example with custom UI layout.

Uses `.sidebar()` for chat and `.df()`, `.sql()`, `.title()`, `.reset()` for state.

Run with: streamlit run 09-streamlit-custom-app.py
Requires: pip install streamlit (or uv sync --group streamlit)
"""

from pathlib import Path

from querychat.data import titanic
from querychat.streamlit import QueryChat

import streamlit as st

greeting = Path(__file__).parent / "greeting.md"

st.set_page_config(
    page_title="Titanic Explorer",
    layout="wide",
    initial_sidebar_state="expanded",
)

qc = QueryChat(titanic(), "titanic", greeting=greeting)
qc.sidebar()

st.title("Titanic Data Explorer")
st.header(qc.title() or "Full Dataset")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Current Query")
    st.code(qc.sql() or "SELECT * FROM titanic", language="sql")

with col2:
    st.subheader("Quick Stats")
    df = qc.df()
    st.metric("Total Rows", f"{len(df):,}")
    st.metric("Total Columns", len(df.columns))
    if qc.sql() and st.button("Reset Filter"):
        qc.reset()

st.subheader("Data Preview")
st.dataframe(df, use_container_width=True, height=400, hide_index=True)

with st.expander("Column Information"):
    for col in df.columns:
        st.write(f"**{col}** ({df[col].dtype}) - {df[col].is_null().sum()} nulls")
