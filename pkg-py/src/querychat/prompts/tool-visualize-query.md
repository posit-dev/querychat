Render a ggsql query inline in the chat. See the "Visualization with ggsql" section of the system prompt for usage guidance, best practices, and the ggsql syntax reference.

Parameters
----------
ggsql :
    A full ggsql query with SELECT and VISUALISE clauses. The SELECT portion follows standard {{db_type}} SQL syntax. The VISUALISE portion specifies the chart configuration. Do NOT include `LABEL title => ...` in the query — use the `title` parameter instead.
title :
    A brief, user-friendly title for this visualization. This is displayed as the card header above the chart.

Returns
-------
:
    If successful, a static image of the rendered plot. If not, an error message.
