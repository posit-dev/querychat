Execute a SQL query and return the results

This tool executes a {{db_type}} SQL SELECT query against the database and returns the raw result data for analysis.

**When to use:** Call this tool whenever the user asks a question that requires data analysis, aggregation, or calculations. Use this for questions like:
- "What is the average...?"
- "How many records...?"
- "Which item has the highest/lowest...?"
- "What's the total sum of...?"
- "What percentage of ...?"

Always use SQL for counting, averaging, summing, and other calculations—NEVER attempt manual calculations on your own. Use this tool repeatedly if needed to avoid any kind of manual calculation.

**When not to use:** Do NOT use this tool for filtering or sorting the dashboard display. If the user wants to "Show me..." or "Filter to..." certain records in the dashboard, use the `querychat_update_dashboard` tool instead.

**Important guidelines:**

- Queries must be valid {{db_type}} SQL SELECT statements
- Optimize for readability over efficiency—use clear column aliases and SQL comments to explain complex logic
- Subqueries and CTEs are acceptable and encouraged for complex calculations
- After receiving results, always present the key findings in your response text — the tool result starts collapsed by default, so don't assume the user has seen the raw data
- When the result is a single value or small summary, state it directly in prose. When the result is a table that IS the answer, either use a Markdown table in your response or set `collapsed` to `false` — not both
- Do not reproduce large result sets in your response — summarize the key takeaways instead

Parameters
----------
query :
    A valid {{db_type}} SQL SELECT statement. Must follow the database schema provided in the system prompt. Use clear column aliases (e.g., 'AVG(price) AS avg_price') and include SQL comments for complex logic. Subqueries and CTEs are encouraged for readability.
collapsed :
    Optional (default: true). The result card starts collapsed by default; the user can expand it to see the query and results. Set to false when the query result table is the primary answer to the user's question and should be immediately visible without expanding.
_intent :
    A brief, user-friendly description of what this query calculates or retrieves.

Returns
-------
:
    The tabular data results from executing the SQL query. Present the key findings in your response — the tool result may be collapsed, so don't assume the user has seen the raw data.
