# QueryChat maps capability demo — chat-forward, using Shiny Express.
#
# Two real-world tables are registered:
#
# - ``earthquakes``: every magnitude 2.5+ earthquake worldwide from the past
#   month, from the USGS real-time feed (lon/lat point data).
# - ``gdp``: GDP by country (World Bank, via the plotly datasets repo) with
#   ISO 3166-1 alpha-3 codes, suitable for choropleths joined to the builtin
#   ``ggsql:world`` country boundaries.
#
# The opt-in ``"maps"`` capability lets the LLM draw choropleths and point maps
# through ggsql's spatial support. Try asking:
#
# - "Map the earthquakes from the past month, sized by magnitude"
# - "Draw a choropleth of GDP by country"
#
# Usage:
#     cd pkg-py
#     uv run shiny run examples/13-maps-app.py

import pandas as pd
from querychat.express import QueryChat
from shiny.express import render, ui
from shinychat import chat_nav_panel

# Real-time USGS feed: all magnitude 2.5+ earthquakes, past 30 days
earthquakes = pd.read_csv(
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.csv"
)

# World Bank GDP (current US$) by country with ISO alpha-3 codes
gdp = pd.read_csv(
    "https://raw.githubusercontent.com/plotly/datasets/master/2014_world_gdp_with_codes.csv"
)
gdp.columns = ["country", "gdp_billions_usd", "iso_a3"]

greeting = r"""
Welcome! I'm chatting with two live datasets:

* **earthquakes** — every magnitude 2.5+ earthquake worldwide from the past
  month (USGS real-time feed)
* **gdp** — GDP by country (World Bank), with ISO country codes

Maps are enabled! Try asking:

* <span class='suggestion'>Map the earthquakes from the past month, sized by magnitude</span>
* <span class='suggestion'>Draw a choropleth of GDP by country</span>
"""

# 1. Provide data sources to QueryChat, with the opt-in "maps" capability
qc = QueryChat(earthquakes, "earthquakes", greeting=greeting, tools=("default", "maps"))
qc.add_table(gdp, "gdp")

# 2. Hold the reactive data views for the secondary pages (qc.page() owns the
#    entire page, so outputs can't live at the top level)
with ui.hold() as earthquakes_view, ui.card(fill=True):

    @render.data_frame
    def earthquakes_table():
        return qc.table("earthquakes").df()

with ui.hold() as gdp_view, ui.card(fill=True):

    @render.data_frame
    def gdp_table():
        return qc.table("gdp").df()

# 3. Create a chat-first page (the chat owns the full window)
qc.page(
    "QueryChat Maps Demo",
    pages_navbar=[
        chat_nav_panel(
            "Earthquakes",
            earthquakes_view,
            value="earthquakes",
            sidebar=False,
            content_width="100%",
        ),
        chat_nav_panel(
            "GDP",
            gdp_view,
            value="gdp",
            sidebar=False,
            content_width="100%",
        ),
    ],
)
