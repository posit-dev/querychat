import plotly.express as px
from querychat.data import titanic
from querychat.streamlit import QueryChat

import streamlit as st

st.set_page_config(page_title="Titanic Explorer", layout="wide")

qc = QueryChat(titanic(), "titanic")

# Sidebar with chat and reset
with st.sidebar:
    qc.ui()
    st.divider()
    if st.button("Reset Filters", use_container_width=True):
        qc.reset()

# Main content
st.header(qc.title() or "Titanic Dataset")

# Metrics row
df = qc.df().to_pandas()
col1, col2, col3 = st.columns(3)
col1.metric("Passengers", len(df))
col2.metric("Survivors", df["survived"].sum())
col3.metric("Survival Rate", f"{df['survived'].mean():.1%}")

# Visualizations
col1, col2 = st.columns(2)

with col1:
    fig1 = px.histogram(
        df, x="age", color="survived", title="Age Distribution by Survival"
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.bar(
        df.groupby("pclass")["survived"].mean().reset_index(),
        x="pclass",
        y="survived",
        title="Survival by Class",
    )
    st.plotly_chart(fig2, use_container_width=True)
