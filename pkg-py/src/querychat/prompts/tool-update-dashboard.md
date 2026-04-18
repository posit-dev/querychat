Filter and sort the dashboard data by executing a {{db_type}} SQL SELECT query.

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

