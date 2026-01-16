import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from querychat.dash import QueryChat
from querychat.data import titanic
from querychat.types import AppStateDict

from dash import Dash, Input, Output, html

qc = QueryChat(titanic(), "titanic")

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                # Left column: Chat
                dbc.Col(qc.ui(), width=4),
                # Right column: Data display
                dbc.Col(
                    [
                        html.H3(id="data-title"),
                        dag.AgGrid(
                            id="data-table",
                            className="ag-theme-balham",
                            defaultColDef={"filter": True, "sortable": True},
                            dashGridOptions={
                                "pagination": True,
                                "paginationPageSize": 10,
                            },
                            columnSize="responsiveSizeToFit",
                        ),
                        html.Pre(id="sql-display"),
                    ],
                    width=8,
                ),
            ]
        )
    ],
    fluid=True,
)

# Register querychat's internal callbacks
qc.init_app(app)


# Add your own callbacks using qc.store_id
@app.callback(
    [
        Output("data-title", "children"),
        Output("data-table", "rowData"),
        Output("data-table", "columnDefs"),
        Output("sql-display", "children"),
    ],
    Input(qc.store_id, "data"),
)
def update_display(state: AppStateDict):
    df = qc.df(state).to_pandas()
    sql = qc.sql(state) or f"SELECT * FROM {qc.data_source.table_name}"
    title = qc.title(state) or "All Data"

    columns = [{"field": c} for c in df.columns]
    return title, df.to_dict("records"), columns, sql


if __name__ == "__main__":
    app.run(debug=True)
