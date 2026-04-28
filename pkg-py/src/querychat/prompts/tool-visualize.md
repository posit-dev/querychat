Create a data visualization

Render a ggsql query (SQL with a VISUALISE clause) as an Altair chart displayed inline in the chat.

**When to use:** Call this tool when the user's question involves comparisons, distributions, or trends — even for small result sets, a chart is often clearer than a table.{{#has_tool_query}} For single-value answers (averages, counts, totals, specific lookups) or when the user needs exact values, use `querychat_query` instead.{{/has_tool_query}}

**Key constraints:**

- All data transformations must happen in the SELECT clause — VISUALISE and MAPPING accept column names only, not SQL expressions or functions
- Do NOT include `LABEL title => ...` in the query — use the `title` parameter instead
- If a visualization fails, read the error message carefully and retry with a corrected query. Common fixes: correcting column names, adding `SCALE DISCRETE` for integer categories, using single quotes for strings, moving SQL expressions out of VISUALISE into the SELECT clause.{{#has_tool_query}} If the error persists, fall back to `querychat_query` for a tabular answer.{{/has_tool_query}}

Parameters
----------
ggsql :
    A full ggsql query. Must include a VISUALISE clause and at least one DRAW clause. The SELECT portion uses {{db_type}} SQL; VISUALISE and MAPPING accept column names only, not expressions. Do NOT include `LABEL title => ...` in the query — use the `title` parameter instead.
title :
    A brief, user-friendly title for this visualization. This is displayed as the card header above the chart.

Returns
-------
:
    If successful, a static image of the rendered plot. If not, an error message.
