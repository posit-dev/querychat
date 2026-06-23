Retrieve full column details for a table

Returns column names, types, value ranges, categorical values, and descriptions for the specified table.

**When to use this tool:**

- Before writing any SQL query involving a table you have not yet inspected
- When you are unsure which table is most relevant to the user's request — call this tool on candidate tables to understand their contents before deciding

Parameters
----------
table_name
    The name of the table to retrieve schema for. Must match one of the table names shown in the system prompt.

Returns
-------
:
    Full column details for the specified table, including column names, types, value ranges, categorical values, and descriptions.
