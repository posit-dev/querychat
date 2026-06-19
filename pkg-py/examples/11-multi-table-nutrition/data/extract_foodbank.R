#!/usr/bin/env Rscript
# Extract USDA Foundation Foods data from the {foodbank} R package and write
# as parquet files for use in the multi-table-nutrition Shiny for Python app.
#
# Run from the pkg-py/examples directory:
#   Rscript data/extract_foodbank.R
#
# Requires: foodbank (github::hadley/foodbank), nanoparquet
#   pak::pkg_install(c("hadley/foodbank", "nanoparquet"))

library(foodbank)
library(nanoparquet)

script_dir <- tryCatch(
  dirname(normalizePath(sys.frame(1)$ofile)),
  error = function(e) getwd()
)
out_dir <- file.path(script_dir, "foodbank")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# Key nutrient IDs to include (a curated subset of the 477 available)
key_ids <- c(
  1008L,  # Energy (kcal)
  1003L,  # Protein (g)
  1004L,  # Total lipid / fat (g)
  1005L,  # Carbohydrate, by difference (g)
  1079L,  # Fiber, total dietary (g)
  1063L,  # Sugars, Total (g)
  1258L,  # Fatty acids, total saturated (g)
  1087L,  # Calcium, Ca (mg)
  1089L,  # Iron, Fe (mg)
  1093L,  # Sodium, Na (mg)
  1162L,  # Vitamin C, total ascorbic acid (mg)
  1092L   # Potassium, K (mg)
)

write_parquet(food,          file.path(out_dir, "foods.parquet"))
write_parquet(food_category, file.path(out_dir, "food_categories.parquet"))
write_parquet(
  nutrient[nutrient$id %in% key_ids, c("id", "name", "unit_name")],
  file.path(out_dir, "nutrients.parquet")
)
write_parquet(
  food_nutrient[food_nutrient$nutrient_id %in% key_ids,
                c("fdc_id", "nutrient_id", "amount")],
  file.path(out_dir, "food_nutrients.parquet")
)
write_parquet(
  food_portion[, c("fdc_id", "seq_num", "amount", "measure_unit_id",
                   "gram_weight", "modifier")],
  file.path(out_dir, "food_portions.parquet")
)
used_unit_ids <- unique(food_portion$measure_unit_id)
write_parquet(
  measure_unit[measure_unit$id %in% used_unit_ids, ],
  file.path(out_dir, "measure_units.parquet")
)

cat("Wrote parquet files to", out_dir, "\n")
