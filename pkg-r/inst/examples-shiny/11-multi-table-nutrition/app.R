library(shiny)
library(bslib)
library(querychat)
library(arrow)
library(dplyr)
library(tidyr)
library(plotly)
library(DT)

# ── Data ──────────────────────────────────────────────────────────────────────

data_dir <- file.path("data", "foodbank")

foods <- read_parquet(file.path(data_dir, "foods.parquet"))
food_categories <- read_parquet(file.path(data_dir, "food_categories.parquet"))
nutrients <- read_parquet(file.path(data_dir, "nutrients.parquet"))
food_nutrients <- read_parquet(file.path(data_dir, "food_nutrients.parquet"))
food_portions <- read_parquet(file.path(data_dir, "food_portions.parquet"))
measure_units <- read_parquet(file.path(data_dir, "measure_units.parquet"))

nutrient_id_to_col <- c(
  "1008" = "energy_kcal",
  "1003" = "protein_g",
  "1004" = "fat_g",
  "1005" = "carbs_g",
  "1079" = "fiber_g",
  "1063" = "sugars_g",
  "1258" = "sat_fat_g",
  "1087" = "calcium_mg",
  "1089" = "iron_mg",
  "1093" = "sodium_mg",
  "1162" = "vitamin_c_mg",
  "1092" = "potassium_mg"
)

wide_nutrients <- food_nutrients |>
  mutate(col = nutrient_id_to_col[as.character(nutrient_id)]) |>
  filter(!is.na(col)) |>
  select(fdc_id, col, amount) |>
  pivot_wider(names_from = col, values_from = amount)

foods_wide <- foods |>
  left_join(
    food_categories |>
      select(id, description) |>
      rename(category = description),
    by = c("food_category_id" = "id")
  ) |>
  left_join(wide_nutrients, by = "fdc_id")

# ── QueryChat ─────────────────────────────────────────────────────────────────

greeting <- paste0(
  "## USDA Foundation Foods Explorer\n\n",
  "Real nutrition data for **436 foods** across 19 categories — ",
  "macronutrients, minerals, vitamins, and serving sizes.\n\n",
  "**Filter this view**\n\n",
  '<span class="suggestion">Show only foods where fiber exceeds sugar</span>\n\n',
  '<span class="suggestion">High-protein, low-fat foods: protein > 20g and fat < 5g per 100g</span>\n\n',
  '<span class="suggestion">Foods higher in potassium than sodium</span>\n\n',
  "**Dig deeper**\n\n",
  '<span class="suggestion">Which fruits or vegetables beat whole milk for calcium?</span>\n\n',
  '<span class="suggestion">Rank all foods by protein per calorie</span>\n\n',
  '<span class="suggestion">For 1 cup of oats, how much protein and fiber am I getting?</span>\n\n'
)

qc <- QueryChat$new(
  foods,
  "foods",
  data_dict = "nutrition-data-dict.yaml",
  greeting = greeting
)
qc$add_table(food_categories, "food_categories")
qc$add_table(nutrients, "nutrients")
qc$add_table(food_nutrients, "food_nutrients")
qc$add_table(food_portions, "food_portions")
qc$add_table(measure_units, "measure_units")

# ── App ───────────────────────────────────────────────────────────────────────

ui <- page_navbar(
  title = "USDA Foundation Foods",
  sidebar = sidebar(
    qc$ui(),
    width = 400,
    fillable = TRUE,
    class = "querychat-sidebar"
  ),
  nav_panel(
    "Overview",
    layout_columns(
      value_box(
        "Foods",
        textOutput("n_foods"),
        showcase = bsicons::bs_icon("grid"),
        theme = "primary"
      ),
      value_box(
        "Avg Protein",
        textOutput("avg_protein"),
        showcase = bsicons::bs_icon("egg-fried"),
        theme = "success"
      ),
      value_box(
        "Avg Fiber",
        textOutput("avg_fiber"),
        showcase = bsicons::bs_icon("tree"),
        theme = "info"
      ),
      value_box(
        "Avg Calories",
        textOutput("avg_calories"),
        showcase = bsicons::bs_icon("fire"),
        theme = "warning"
      ),
      col_widths = c(3, 3, 3, 3)
    ),
    layout_columns(
      card(
        full_screen = TRUE,
        card_header(textOutput("protein_chart_title", inline = TRUE)),
        plotlyOutput("protein_chart")
      ),
      card(
        full_screen = TRUE,
        card_header("Avg protein by category (top 10)"),
        plotlyOutput("macro_chart")
      )
    )
  ),
  nav_panel(
    "Data",
    do.call(
      navset_card_underline,
      c(
        lapply(qc$table_names(), function(name) {
          nav_panel(name, DTOutput(paste0("dt_", name)))
        }),
        list(id = "table_tabs", full_screen = TRUE)
      )
    )
  ),
  fillable = TRUE
)

server <- function(input, output, session) {
  qc_vals <- qc$server()

  current_subset <- reactive({
    ids <- qc_vals$table("foods")$df()[["fdc_id"]]
    foods_wide[foods_wide$fdc_id %in% ids, ]
  })

  output$n_foods <- renderText(nrow(current_subset()))

  output$avg_protein <- renderText({
    v <- mean(current_subset()$protein_g, na.rm = TRUE)
    if (is.nan(v)) "—" else sprintf("%.1f g", v)
  })

  output$avg_fiber <- renderText({
    v <- mean(current_subset()$fiber_g, na.rm = TRUE)
    if (is.nan(v)) "—" else sprintf("%.1f g", v)
  })

  output$avg_calories <- renderText({
    v <- mean(current_subset()$energy_kcal, na.rm = TRUE)
    if (is.nan(v)) "—" else sprintf("%.0f kcal", v)
  })

  output$protein_chart_title <- renderText({
    n <- sum(!is.na(current_subset()$protein_g))
    sprintf("Top %d foods by protein (g/100g)", min(n, 15L))
  })

  output$protein_chart <- renderPlotly({
    df <- current_subset() |>
      filter(!is.na(protein_g)) |>
      arrange(desc(protein_g)) |>
      head(15) |>
      mutate(label = substr(description, 1, 35))

    plot_ly(
      df,
      x = ~protein_g,
      y = ~ reorder(label, protein_g),
      type = "bar",
      orientation = "h",
      marker = list(color = "#2196F3")
    ) |>
      layout(
        showlegend = FALSE,
        xaxis = list(title = "Protein (g/100g)"),
        yaxis = list(title = ""),
        margin = list(l = 10, r = 40, t = 10, b = 40)
      )
  })

  output$macro_chart <- renderPlotly({
    subset <- current_subset()
    top_cats <- subset |>
      count(category, sort = TRUE) |>
      head(10) |>
      pull(category)

    agg <- subset |>
      filter(category %in% top_cats) |>
      group_by(category) |>
      summarise(
        avg_protein = mean(protein_g, na.rm = TRUE),
        .groups = "drop"
      ) |>
      arrange(desc(avg_protein))

    plot_ly(
      agg,
      x = ~avg_protein,
      y = ~ reorder(category, avg_protein),
      type = "bar",
      orientation = "h",
      marker = list(color = "#4CAF50")
    ) |>
      layout(
        showlegend = FALSE,
        xaxis = list(title = "Avg protein (g/100g)"),
        yaxis = list(title = ""),
        margin = list(l = 10, r = 10, t = 10, b = 10)
      )
  })

  # Auto-switch tab when LLM queries a table.
  observe({
    ct <- qc_vals$current_table()
    if (!is.null(ct)) {
      nav_select("table_tabs", selected = ct, session = session)
    }
  })

  # Register one DT render per table.
  # Value boxes and charts above remain tied to the `foods` table — they
  # use foods-specific wide-format joins and are not generic per-table views.
  for (tbl_name in qc$table_names()) {
    local({
      name <- tbl_name
      output[[paste0("dt_", name)]] <- renderDT({
        qc_vals$table(name)$df() |>
          datatable(
            fillContainer = TRUE,
            options = list(pageLength = 25, scrollX = TRUE)
          )
      })
    })
  }
}

shinyApp(ui, server)
