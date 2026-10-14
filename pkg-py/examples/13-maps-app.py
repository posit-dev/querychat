# QueryChat maps capability demo using Shiny Express.
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
# - "Show a globe of earthquake epicenters"
#
# Usage:
#     cd pkg-py
#     uv run shiny run examples/13-maps-app.py

import pandas as pd
from querychat.express import QueryChat
from shiny.express import render, ui

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
* <span class='suggestion'>Map earthquakes in the Pacific on an orthographic globe</span>
"""

qc = QueryChat(earthquakes, "earthquakes", greeting=greeting, tools=("default", "maps"))
qc.add_table(gdp, "gdp")
qc.sidebar()

with ui.navset_card_underline():
    with ui.nav_panel("Earthquakes"):

        @render.data_frame
        def earthquakes_table():
            return qc.table("earthquakes").df()

    with ui.nav_panel("GDP"):

        @render.data_frame
        def gdp_table():
            return qc.table("gdp").df()


ui.page_opts(title="QueryChat Maps Demo", fillable=True)
