import dash_bootstrap_components as dbc
import plotly.express as px
from querychat.dash import QueryChat
from querychat.data import titanic
from querychat.types import AppStateDict

from dash import Dash, Input, Output, dcc, html

qc = QueryChat(titanic(), "titanic")

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        html.H1("Titanic Dataset Explorer", className="my-3"),
        dbc.Row(
            [
                dbc.Col(qc.ui(), width=4),
                dbc.Col(
                    [
                        html.H3(id="data-title", className="mb-3"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Passengers"),
                                            dbc.CardBody(
                                                html.H4(id="metric-passengers")
                                            ),
                                        ]
                                    )
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Survivors"),
                                            dbc.CardBody(
                                                html.H4(id="metric-survivors")
                                            ),
                                        ]
                                    )
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Survival Rate"),
                                            dbc.CardBody(html.H4(id="metric-rate")),
                                        ]
                                    )
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(dcc.Graph(id="age-chart")),
                                dbc.Col(dcc.Graph(id="class-chart")),
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

qc.init_app(app)


@app.callback(
    [
        Output("data-title", "children"),
        Output("metric-passengers", "children"),
        Output("metric-survivors", "children"),
        Output("metric-rate", "children"),
        Output("age-chart", "figure"),
        Output("class-chart", "figure"),
    ],
    Input(qc.store_id, "data"),
)
def update_all(state: AppStateDict):
    df = qc.df(state).to_pandas()
    title = qc.title(state) or "All Data"

    # Metrics
    n_passengers = len(df)
    n_survivors = int(df["survived"].sum())
    survival_rate = f"{df['survived'].mean():.1%}"

    # Charts
    fig1 = px.histogram(
        df, x="age", color="survived", title="Age Distribution by Survival"
    )
    fig2 = px.bar(
        df.groupby("pclass")["survived"].mean().reset_index(),
        x="pclass",
        y="survived",
        title="Survival by Class",
    )

    return (
        title,
        n_passengers,
        n_survivors,
        survival_rate,
        fig1,
        fig2,
    )


if __name__ == "__main__":
    import os

    port = int(os.environ.get("DASH_PORT", "8050"))
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=port)
