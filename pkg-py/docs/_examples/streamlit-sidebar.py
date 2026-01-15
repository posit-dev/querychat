import plotly.express as px
from querychat.data import titanic
from querychat.streamlit import QueryChat

import streamlit as st

qc = QueryChat(titanic(), "titanic")
qc.sidebar()

st.header(qc.title() or "Titanic Explorer")
st.dataframe(qc.df())

df = qc.df().to_pandas()
fig = px.histogram(df, x="age", color="survived", title="Age Distribution")
st.plotly_chart(fig)
