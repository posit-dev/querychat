Add, replace, patch, or remove a persistent card in the dashboard cards area

Cards live in a developer-placed dashboard area and stay visible across queries. Use them to surface insights the user wants to keep in view (a key metric, a notable ranking, a trend, or a written takeaway), not to echo every query result. Add a card when the user asks to "pin", "save", or "add to the dashboard", or when you have answered a question and a persistent summary would clearly add lasting value.

Match the display to the finding:

- **value_box**: a single key metric. The SQL query must return exactly 1 row. The displayed number comes from the `value` column (or the first column if no `value` column). Columns named `title`, `text`, `theme`, or `icon` override the static card fields, enabling dynamic theming (e.g. `CASE WHEN ... THEN 'danger' ELSE 'success' END AS theme`).
- **table**: a ranked or comparative result set the user wants to see at a glance.
- **visualization**: a trend, distribution, or comparison that reads better as a chart.
- **markdown**: a written takeaway or note. Use the `text` field for the markdown body. Optionally supply a `query` (SQL returning exactly 1 row) whose columns become `{{var}}` placeholders in `text` for live interpolation (e.g. `Revenue grew {{pct}}% to {{total}}`).

For a small set of related metrics (roughly 3-4 or fewer), add a separate value_box for each one; a row of value boxes reads better than one table of headline numbers.

Query-backed cards (table, visualization, value_box) are validated by running the query before the card is added, replaced, or patched. If a query fails you receive the error message; fix the query and retry at least once before reporting failure to the user.

Parameters
----------
action :
    The operation to perform.
    - `"add"`: create a new card. Requires `display`, `title`, and `query` (or `text` for markdown).
    - `"patch"`: the preferred way to edit a card. Send the `id` and only the fields you are changing; omitted fields keep their current values. Cannot clear an optional field; use `"replace"` for that.
    - `"replace"`: fully overwrite a card. Send the `id` and every field for the new version (same requirements as `"add"`; changing `display` is allowed). Omitted optional fields are cleared.
    - `"remove"`: delete a card. Requires only `id`.
    - `"get"`: read existing cards. Omit `id` for all cards, or pass an `id` for one. Use it to discover card `id`s and their current contents before a patch, replace, or remove.
id :
    The short card identifier. Required for `"replace"`, `"patch"`, and `"remove"`; optional for `"get"` (omit to return all cards); omit for `"add"`.
display :
    Which renderer to use; required for `"add"` and `"replace"`. One of `"table"`, `"visualization"`, `"markdown"`, or `"value_box"`, as described above.
title :
    A brief card heading shown in the card header. Required for `"add"` and `"replace"`.
query :
    The data query; required for table, visualization, and value_box displays; optional for markdown (interpolation). Its meaning depends on `display`:
    - `"table"`: a valid {{db_type}} SQL SELECT query.
    - `"visualization"`: a full ggsql query including a VISUALISE clause. Do NOT include `LABEL title => ...`; use the `title` parameter instead.
    - `"value_box"`: a {{db_type}} SQL SELECT query returning exactly 1 row. The displayed number comes from the `value` column (or the first column). Additional columns named `title`, `text`, `theme`, or `icon` override the static card fields. Format the displayed value as a human-readable string in SQL (thousands separators, currency, rounding, a `%` suffix, etc.).
    - `"markdown"` (optional): a {{db_type}} SQL SELECT query returning exactly 1 row. Its columns become `{{var}}` placeholders in the `text` body.
text :
    Supplementary text; its role depends on `display`:
    - `"markdown"` (required): the body content, rendered as HTML via markdown. If a `query` is also supplied, its single-row columns are interpolated as `{{var}}` placeholders.
    - `"table"` / `"visualization"`: a brief footer shown below the content.
    - `"value_box"`: the subtitle shown under the main value.
theme :
    Optional Bootstrap theme name for a value_box background (e.g. `primary`, `secondary`, `success`, `danger`, `warning`, `info`). Any valid Bootstrap theme class is accepted. Applies to value_box only; ignored for other displays.
icon :
    Optional Bootstrap icon name (e.g., `"bar-chart"`, `"currency-dollar"`, `"people-fill"`). Honored by every display: the showcase icon for value_box, and shown beside the title for table/visualization/markdown.

Returns
-------
:
    For `"add"`, `"replace"`, `"patch"`, and `"remove"`: a JSON object with the
    affected card's `id` and a `status` (e.g. `{"id": "a3f7", "status": "added"}`).
    For `"get"`: a single card object when an `id` is given, otherwise a JSON array
    of all cards. Each card object holds the card's full definition (`id`, `display`,
    `title`, `query`/`text`, and any optional fields), e.g.
    `{"id": "a3f7", "display": "value_box", "title": "Total Revenue", "query": "SELECT ..."}`.
    If a query-backed card fails validation, an error message is returned instead and
    no card is created or changed.
