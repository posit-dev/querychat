Render a ggsql query inline in the chat. All data transformations must happen in the SELECT clause — VISUALISE and MAPPING accept column names only, not SQL expressions or functions.

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
