"""
Dash example with custom UI layout.

Uses ``.ui()`` for the chat component and ``.init_app()`` to register callbacks.
The ``.store_id`` property is used for callback wiring to react to state changes.

Run with: python 08-dash-custom-app.py
Requires: pip install dash dash-bootstrap-components (or uv sync --group dash)
"""

import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dash_table, dcc, html

from querychat.dash import QueryChat
from querychat.data import titanic
from querychat.types import AppStateDict

qc = QueryChat(titanic(), "titanic")

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Titanic Explorer",
)

app.layout = dbc.Container(
    [
        html.H1("Titanic Data Explorer", className="mt-4 mb-4"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(html.H4("Chat")),
                            dbc.CardBody(qc.ui()),
                        ],
                    ),
                    width=4,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(html.H4(id="query-title")),
                                dbc.CardBody(
                                    dcc.Markdown(id="sql-display")
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H6("Rows", className="card-subtitle"),
                                                html.H3(id="row-count", className="card-title"),
                                            ]
                                        )
                                    ),
                                    width=6,
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H6("Columns", className="card-subtitle"),
                                                html.H3(id="col-count", className="card-title"),
                                            ]
                                        )
                                    ),
                                    width=6,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Card(
                            [
                                dbc.CardHeader(html.H4("Data Preview")),
                                dbc.CardBody(html.Div(id="data-table")),
                            ]
                        ),
                    ],
                    width=8,
                ),
            ]
        ),
    ],
    fluid=True,
)

# Register chat callbacks
qc.init_app(app)


@app.callback(
    [
        Output("query-title", "children"),
        Output("sql-display", "children"),
        Output("row-count", "children"),
        Output("col-count", "children"),
        Output("data-table", "children"),
    ],
    Input(qc.store_id, "data"),
)
def update_display(state_data: AppStateDict):
    df = qc.df(state_data)
    sql = qc.sql(state_data)
    title = qc.title(state_data)

    # Convert narwhals DataFrame to pandas for Dash DataTable compatibility
    display_df = df.head(100).to_pandas()
    table = dash_table.DataTable(
        data=display_df.to_dict("records"),
        columns=[{"name": col, "id": col} for col in display_df.columns],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        page_size=20,
        filter_action="native",
        sort_action="native",
    )

    sql_display = sql or "SELECT * FROM titanic"
    sql_markdown = f"```sql\n{sql_display}\n```"

    return (
        title or "Full Dataset",
        sql_markdown,
        f"{df.shape[0]:,}",
        str(df.shape[1]),
        table,
    )


if __name__ == "__main__":
    port = int(os.environ.get("DASH_PORT", "8050"))
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=port)
