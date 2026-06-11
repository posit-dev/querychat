Create or update cards on the user's dashboard canvas (the "drawer").

Each card is a JSON object with these fields:

- `name` (required): stable identifier, lowercase snake_case (e.g. `"avg_mpg"`).
  Reusing an existing name UPDATES that card; a new name CREATES a card.
- `type` (required): one of `"chart"`, `"table"`, `"value_box"`, `"markdown"`.
- `title` (required): short human-readable card title.
- `layout` (optional): `{"x": 0-11, "y": >=0, "w": 1-12, "h": >=1}` on a
  12-column grid. Omit to auto-place at the bottom.
- Source field, depending on `type`:
  - `chart` → `ggsql`: a full ggsql query (SQL + VISUALISE + DRAW). Same
    rules as `querychat_visualize` ({{db_type}} SQL dialect; all transforms
    in the SELECT; no layer-level FROM).
  - `table` → `sql`: a SQL SELECT. Optional `page_size` (default 10).
  - `value_box` → `sql`: SQL returning EXACTLY one row and one column.
    Optional `format` (Python format spec, may start with a currency symbol,
    e.g. `"$,.0f"`), `icon` (bootstrap icon name), `theme`
    (`"primary"`, `"success"`, `"danger"`, `"warning"`), and `delta_sql`
    (a second scalar SQL shown as a comparison line).
  - `markdown` → `text`: markdown narrative (e.g. key takeaways).

All cards are validated before they appear; tables and value boxes are
test-executed against the database, while chart ggsql is validated for
syntax only (execution errors, e.g. unknown columns, surface at render
time). If any validation fails, NOTHING is applied and you get the errors
back — fix and retry.

Typical heights: value_box h=2, chart h=4, table h=4, markdown h=2.
