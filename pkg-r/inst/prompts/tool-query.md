Execute a SQL query and return the results

This tool executes a {{db_type}} SQL SELECT query against the database and returns the raw result data for analysis.

**Returns:** The tabular data results from executing the SQL query. The query results will be visible to the user in the interface, so you must interpret and explain the data in natural language after receiving it.

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
- After receiving results, provide an explanation of the answer and an overview of how you arrived at it, if not already explained in SQL comments
- The user can see your SQL query, they will follow up with detailed explanations if needed
