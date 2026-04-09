Execute a {{db_type}} SQL SELECT query and return the results for analysis.

**Important guidelines:**

- Queries must be valid {{db_type}} SQL SELECT statements
- Optimize for readability over efficiency—use clear column aliases and SQL comments to explain complex logic
- Subqueries and CTEs are acceptable and encouraged for complex calculations
- After receiving results, provide an explanation of the answer and an overview of how you arrived at it, if not already explained in SQL comments
- The user can see your SQL query, they will follow up with detailed explanations if needed

Parameters
----------
query :
    A valid {{db_type}} SQL SELECT statement. Must follow the database schema provided in the system prompt. Use clear column aliases (e.g., 'AVG(price) AS avg_price') and include SQL comments for complex logic. Subqueries and CTEs are encouraged for readability.
collapsed :
    Optional (default: false). Set to true for exploratory or preparatory queries (e.g., inspecting data before visualization, checking row counts, previewing column values) whose results aren't the primary answer. When true, the result card starts collapsed so it doesn't clutter the conversation.
_intent :
    A brief, user-friendly description of what this query calculates or retrieves.

Returns
-------
:
    The tabular data results from executing the SQL query. The query results will be visible to the user in the interface, so you must interpret and explain the data in natural language after receiving it.
