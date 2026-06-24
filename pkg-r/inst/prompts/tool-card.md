Add, replace, patch, or remove a persistent card in the dashboard cards area

Cards live in a developer-placed dashboard area and stay visible across queries. Use them to surface insights the user wants to keep in view (a key metric, a notable ranking, a trend, or a written takeaway), not to echo every query result. Add a card when the user asks to "pin", "save", or "add to the dashboard", or when you have answered a question and a persistent summary would clearly add lasting value.

Match the display to the finding:

- **value_box**: a single key metric. The SQL query must return exactly 1 row. The displayed number comes from the `value` column (or the first column if no `value` column). Columns named `title`, `caption`, `theme`, or `icon` override the static card fields, enabling dynamic theming (e.g. `CASE WHEN ... THEN 'danger' ELSE 'success' END AS theme`).
- **table**: a ranked or comparative result set the user wants to see at a glance.
- **visualization**: a trend, distribution, or comparison that reads better as a chart.
- **markdown**: a written takeaway or note. Use the `text` field for the markdown body. Optionally supply a `query` (SQL returning exactly 1 row) whose columns become `{{var}}` placeholders in `text` for live interpolation (e.g. `Revenue grew {{pct}}% to {{total}}`).

For a small set of related metrics (roughly 3-4 or fewer), add a separate value_box for each one; a row of value boxes reads better than one table of headline numbers.

Query-backed cards (table, visualization, value_box) are validated by running the query before the card is added, replaced, or patched. If a query fails you receive the error message; fix the query and retry at least once before reporting failure to the user.
