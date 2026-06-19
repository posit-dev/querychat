"""USDA Foundation Foods nutrition dashboard with querychat.

Real nutrition data from the USDA Foundation Foods dataset (via the {foodbank}
R package), organized across six tables:
  foods, food_categories, nutrients, food_nutrients, food_portions, measure_units

The main content area shows reactive value boxes and Plotly Express charts that
update whenever querychat filters the data.

Usage:
    cd pkg-py
    uv run shiny run examples/multi-table-nutrition.py
"""
from pathlib import Path

import plotly.express as px
import polars as pl
import shinychat
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

from querychat import QueryChat

# ── Data ─────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent / "data" / "foodbank"

foods = pl.read_parquet(_DATA_DIR / "foods.parquet")
food_categories = pl.read_parquet(_DATA_DIR / "food_categories.parquet")
nutrients = pl.read_parquet(_DATA_DIR / "nutrients.parquet")
food_nutrients = pl.read_parquet(_DATA_DIR / "food_nutrients.parquet")
food_portions = pl.read_parquet(_DATA_DIR / "food_portions.parquet")
measure_units = pl.read_parquet(_DATA_DIR / "measure_units.parquet")

# Mapping from USDA nutrient ID to friendly column name
_NUTRIENT_ID_TO_COL = {
    1008: "energy_kcal",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carbs_g",
    1079: "fiber_g",
    1063: "sugars_g",
    1258: "sat_fat_g",
    1087: "calcium_mg",
    1089: "iron_mg",
    1093: "sodium_mg",
    1162: "vitamin_c_mg",
    1092: "potassium_mg",
}

_col_map = pl.DataFrame(
    {
        "nutrient_id": list(_NUTRIENT_ID_TO_COL.keys()),
        "col": list(_NUTRIENT_ID_TO_COL.values()),
    }
).with_columns(pl.col("nutrient_id").cast(pl.Int32))

_wide_nutrients = (
    food_nutrients.join(_col_map, on="nutrient_id", how="left").pivot(
        index="fdc_id", on="col", values="amount"
    )
)

foods_wide = (
    foods.join(
        food_categories.select(["id", "description"]).rename(
            {"description": "category"}
        ),
        left_on="food_category_id",
        right_on="id",
        how="left",
    ).join(_wide_nutrients, on="fdc_id", how="left")
)

# ── QueryChat ─────────────────────────────────────────────────────────────────

qc = QueryChat(
    foods,
    "foods",
    data_dict=Path(__file__).parent / "nutrition-data-dict.yaml",
    greeting="",
)
qc.add_table(food_categories, "food_categories")
qc.add_table(nutrients, "nutrients")
qc.add_table(food_nutrients, "food_nutrients")
qc.add_table(food_portions, "food_portions")
qc.add_table(measure_units, "measure_units")

_GREETING = shinychat.chat_greeting(
    "## USDA Foundation Foods Explorer\n\n"
    "Real nutrition data for **436 foods** across 19 categories — "
    "macronutrients, minerals, vitamins, and serving sizes.\n\n"
    "**Filter this view**\n\n"
    '<span class="suggestion">Show only foods where fiber exceeds sugar</span>\n\n'
    '<span class="suggestion">High-protein, low-fat foods: protein > 20g and fat < 5g per 100g</span>\n\n'
    '<span class="suggestion">Foods higher in potassium than sodium</span>\n\n'
    "**Dig deeper**\n\n"
    '<span class="suggestion">Which fruits or vegetables beat whole milk for calcium?</span>\n\n'
    '<span class="suggestion">Rank all foods by protein per calorie</span>\n\n'
    '<span class="suggestion">For 1 cup of oats, how much protein and fiber am I getting?</span>\n\n'
)

# ── App ───────────────────────────────────────────────────────────────────────


def app_ui(request):
    return ui.page_sidebar(
        ui.sidebar(
            qc.ui(greeting=_GREETING),
            width=400,
            height="100%",
            fillable=True,
            class_="querychat-sidebar",
        ),
        ui.layout_columns(
            ui.value_box(
                "Foods",
                ui.output_text("n_foods"),
                showcase=ui.tags.span("🍽️", style="font-size:2rem"),
                theme="primary",
            ),
            ui.value_box(
                "Avg Protein",
                ui.output_text("avg_protein"),
                showcase=ui.tags.span("🥩", style="font-size:2rem"),
                theme="success",
            ),
            ui.value_box(
                "Avg Fiber",
                ui.output_text("avg_fiber"),
                showcase=ui.tags.span("🥦", style="font-size:2rem"),
                theme="info",
            ),
            ui.value_box(
                "Avg Calories",
                ui.output_text("avg_calories"),
                showcase=ui.tags.span("🔥", style="font-size:2rem"),
                theme="warning",
            ),
            col_widths=[3, 3, 3, 3],
            gap="1rem",
            fill=False,
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header(ui.output_text("protein_chart_title")),
                output_widget("protein_chart"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header("Avg protein by category (top 10)"),
                output_widget("macro_chart"),
                full_screen=True,
            ),
        ),
        ui.navset_card_underline(
            *[
                ui.nav_panel(name, ui.output_data_frame(f"dt_{name}"))
                for name in qc.table_names()
            ],
            id="table_tabs",
            full_screen=True,
        ),
        title="USDA Foundation Foods",
        fillable=True,
        class_="bslib-page-dashboard",
    )


def server(input, output, session):
    qc_vals = qc.server()

    @reactive.calc
    def current_subset() -> pl.DataFrame:
        queried = qc_vals.tables["foods"].df()
        # queried may be polars or pandas depending on the data source
        if hasattr(queried, "to_pandas"):  # polars DataFrame
            ids = queried["fdc_id"].to_list()
        else:  # pandas DataFrame
            ids = queried["fdc_id"].tolist()
        return foods_wide.filter(pl.col("fdc_id").is_in(ids))

    @render.text
    def n_foods():
        return str(current_subset().height)

    @render.text
    def avg_protein():
        v = current_subset()["protein_g"].drop_nulls().mean()
        return f"{v:.1f} g" if v is not None else "—"

    @render.text
    def avg_fiber():
        v = current_subset()["fiber_g"].drop_nulls().mean()
        return f"{v:.1f} g" if v is not None else "—"

    @render.text
    def avg_calories():
        v = current_subset()["energy_kcal"].drop_nulls().mean()
        return f"{v:.0f} kcal" if v is not None else "—"

    @render.text
    def protein_chart_title():
        n = current_subset().filter(pl.col("protein_g").is_not_null()).height
        shown = min(n, 15)
        return f"Top {shown} foods by protein (g/100g)"

    @render_plotly
    def protein_chart():
        df = (
            current_subset()
            .filter(pl.col("protein_g").is_not_null())
            .sort("protein_g", descending=True)
            .head(15)
            .with_columns(
                pl.col("description")
                .str.slice(0, 35)
                .str.replace(r"(.{35}).+", "${1}…")
                .alias("label")
            )
        )
        fig = px.bar(
            df,
            x="protein_g",
            y="label",
            orientation="h",
            hover_data={"category": True, "label": False, "description": True},
            labels={"protein_g": "Protein (g/100g)", "label": ""},
            color_discrete_sequence=["#2196F3"],
        )
        fig.update_layout(
            showlegend=False,
            yaxis={"categoryorder": "total ascending"},
            margin={"l": 10, "r": 40, "t": 10, "b": 40},
        )
        return fig

    @render_plotly
    def macro_chart():
        subset = current_subset()
        # Limit to top 10 categories by food count to keep the chart readable
        top_cats = (
            subset.group_by("category")
            .len()
            .sort("len", descending=True)
            .head(10)["category"]
        )
        agg = (
            subset.filter(pl.col("category").is_in(top_cats))
            .group_by("category")
            .agg(pl.col("protein_g").mean().alias("avg_protein"))
            .sort("avg_protein", descending=True)
        )
        fig = px.bar(
            agg,
            x="avg_protein",
            y="category",
            orientation="h",
            labels={"avg_protein": "Avg protein (g/100g)", "category": ""},
            color_discrete_sequence=["#4CAF50"],
        )
        fig.update_layout(
            showlegend=False,
            yaxis={"categoryorder": "total ascending"},
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
        )
        return fig

    # Auto-switch tab when LLM queries a table
    @reactive.effect
    def _switch_tab():
        name = qc_vals.current_table()
        if name is not None:
            ui.update_navs("table_tabs", selected=name)

    # Register one data frame render per table.
    # Value boxes and charts above remain tied to the `foods` table — they
    # use foods-specific wide-format joins and are not generic per-table views.
    def _make_dt_renderer(table_name: str):
        @render.data_frame
        def _renderer():
            return qc_vals.table(table_name).df()

        return _renderer

    for _tname in qc.table_names():
        output[f"dt_{_tname}"] = _make_dt_renderer(_tname)


app = App(app_ui, server)
