Filter and sort the dashboard data

This tool executes a {{db_type}} SQL SELECT query to filter or sort the data used in the dashboard.

**When to use:** Call this tool whenever the user requests filtering, sorting, or data manipulation on the dashboard with questions like "Show me..." or "Which records have...". This tool is appropriate for any request that involves showing a subset of the data or reordering it.

**When not to use:** Do NOT use this tool for general questions about the data that can be answered with a single value or summary statistic. For those questions, use the `querychat_query` tool instead.

**Important constraints:**

- All original schema columns must be present in the SELECT output
- Use a single SQL query. You can use CTEs but you cannot chain multiple queries
- For statistical filters (stddev, percentiles), use CTEs to calculate thresholds within the query
- Assume the user will only see the original columns in the dataset


Parameters
----------
query :
    A {{db_type}} SQL SELECT query that MUST return all existing schema columns (use SELECT * or explicitly list all columns). May include additional computed columns, subqueries, CTEs, WHERE clauses, ORDER BY, and any {{db_type}}-supported SQL functions.
title :
    A brief title for display purposes, summarizing the intent of the SQL query.

Returns
-------
:
    A confirmation that the dashboard was updated successfully, or the error that occurred when running the SQL query. The results of the query will update the data shown in the dashboard.

