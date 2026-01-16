import dash_bootstrap_components as dbc
import plotly.express as px
from querychat.dash import QueryChat
from querychat.data import titanic
from querychat.types import AppStateDict

from dash import Dash, Input, Output, dcc

qc = QueryChat(titanic(), "titanic")

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(qc.ui(), width=4),
                dbc.Col(
                    [
                        dcc.Graph(id="age-histogram"),
                        dcc.Graph(id="class-survival"),
                    ],
                    width=8,
                ),
            ]
        )
    ],
    fluid=True,
)

qc.init_app(app)


@app.callback(
    [Output("age-histogram", "figure"), Output("class-survival", "figure")],
    Input(qc.store_id, "data"),
)
def update_charts(state: AppStateDict):
    df = qc.df(state).to_pandas()
    fig1 = px.histogram(df, x="age", color="survived", title="Age Distribution")
    fig2 = px.bar(
        df.groupby("pclass")["survived"].mean().reset_index(),
        x="pclass",
        y="survived",
        title="Survival by Class",
    )
    return fig1, fig2


if __name__ == "__main__":
    app.run(debug=True)
