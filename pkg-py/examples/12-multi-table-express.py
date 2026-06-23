"""Minimal multi-table querychat example using Shiny Express.

Two related tables (orders + customers) are registered with a single QueryChat
instance. The LLM can query either table or write joins across them.
Per-table filtered data is accessed with `qc.table("name").df()`.

Usage:
    cd pkg-py
    uv run shiny run examples/12-multi-table-express.py
"""

import pandas as pd
from shiny.express import render, ui

from querychat.express import QueryChat

orders = pd.DataFrame(
    {
        "order_id": [1, 2, 3, 4, 5],
        "customer_id": [101, 102, 101, 103, 102],
        "amount": [250.0, 180.0, 320.0, 90.0, 450.0],
        "status": ["shipped", "pending", "shipped", "delivered", "pending"],
    }
)

customers = pd.DataFrame(
    {
        "customer_id": [101, 102, 103],
        "name": ["Alice", "Bob", "Carol"],
        "city": ["Boston", "Chicago", "Denver"],
    }
)

qc = QueryChat(orders, "orders")
qc.add_table(customers, "customers")
qc.sidebar()

with ui.navset_card_underline():
    with ui.nav_panel("Orders"):

        @render.data_frame
        def orders_table():
            return qc.table("orders").df()

    with ui.nav_panel("Customers"):

        @render.data_frame
        def customers_table():
            return qc.table("customers").df()

ui.page_opts(
    title="Orders & Customers",
    fillable=True,
)
