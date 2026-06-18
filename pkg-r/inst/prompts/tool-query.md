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
