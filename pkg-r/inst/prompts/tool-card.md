Add, replace, patch, or remove a persistent card in the dashboard cards area

This tool manages cards in a developer-placed dashboard area. Cards persist across queries and are visible to the user at all times — use them to surface insights worth keeping, not to echo every query result.

**When to use:** Call this tool when the user asks to "pin", "save", or "add to the dashboard" a finding, or when you've answered a question and a persistent summary card would genuinely add value. Do not add a card for routine lookups — reserve cards for key metrics and insights the user wants to keep visible.

**Card types:**

- **value_box** — A single prominent number or label. Use for one key metric (e.g., total revenue, record count). The SQL query must return exactly 1 row and 1 column.
- **table** — A ranked or comparative result set. Use when the user wants to see multiple rows side-by-side at a glance.
- **visualization** — A chart. Use for trends, distributions, or comparisons where a visual is clearer than numbers.
- **markdown** — Free-form text. Use for written takeaways, interpretations, or notes that don't involve a live query.

**When to replace, patch, or remove:** Use `action:"patch"` to change only a few fields of an existing card (e.g., its `title`, `icon`, or `value`) without resending the rest. Use `action:"replace"` to fully rewrite a card, including clearing optional fields. Use `action:"remove"` to drop a card that is no longer relevant.

**On failure:** Query-backed cards (table, visualization, value_box) are executed to validate before being added, replaced, or patched. If a query fails, you will receive an error message — fix the query and retry. Do not report failure to the user until you have retried at least once.

Parameters
----------
action :
    One of `"add"`, `"replace"`, `"patch"`, or `"remove"`.
    - `"add"`: create a new card. Requires `type` (and `display` when `type` is `"card"`), `title`, and `value`.
    - `"replace"`: fully overwrite an existing card. Requires `id` plus all fields for the replacement card (same requirements as `"add"`; type changes are allowed). Fields you omit are cleared, so use this to remove an optional field such as a `footer` or `subtitle`.
    - `"patch"`: change only the fields you supply on an existing card; omitted fields keep their current values. Requires `id` and at least one field to change. Cannot clear an optional field — use `"replace"` for that.
    - `"remove"`: delete a card. Requires only `id`.
id :
    The short card identifier returned in `cards_summary`. Required for `"replace"`, `"patch"`, and `"remove"`; omit for `"add"`.
type :
    `"card"` for table, visualization, and markdown cards; `"value_box"` for a single-metric highlight. Required for `"add"` and `"replace"`.
display :
    Required when `type` is `"card"`. One of:
    - `"table"` — renders the query result as a table.
    - `"visualization"` — renders a ggsql query as a chart.
    - `"markdown"` — renders `value` as markdown text (no query).
title :
    A brief, user-friendly card heading. Required for `"add"` and `"replace"`.
value :
    The card content. Interpretation depends on `type`/`display`:
    - `type:"card"`, `display:"table"` — a valid {{db_type}} SQL SELECT query.
    - `type:"card"`, `display:"visualization"` — a full ggsql query (SQL with a VISUALISE clause). Do NOT include `LABEL title => ...`; use the `title` parameter instead.
    - `type:"card"`, `display:"markdown"` — markdown text (no query).
    - `type:"value_box"` — a {{db_type}} SQL SELECT query that MUST return exactly 1 row and 1 column.
    Required for `"add"` and `"replace"`.
footer :
    Optional. A short note displayed below the card content. Applies to all `type:"card"` displays. Not available for `type:"value_box"`.
subtitle :
    Optional. A secondary label shown below the main value. Applies to `type:"value_box"` only.
theme :
    Optional. A bslib theme name for the value box background. One of: `primary`, `secondary`, `success`, `danger`, `warning`, `info`. Applies to `type:"value_box"` only.
icon :
    Optional. A bsicons icon name (e.g., `"bar-chart"`, `"currency-dollar"`, `"people-fill"`). Applies to `type:"value_box"` only.

Returns
-------
:
    A `cards_summary` string listing all cards currently on the dashboard, e.g.:
    `3 cards: [a3f7] Total Revenue (value_box), [b2c1] Top Customers (table), [d4e5] Monthly Trend (visualization)`
    Use the bracketed `id` values to target cards with `"replace"`, `"patch"`, or `"remove"`.
    If a query-backed card fails validation, an error message is returned instead and no card is created or changed.
