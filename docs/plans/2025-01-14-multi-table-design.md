# Multi-Table Support for QueryChat

**Date**: 2025-01-14
**Status**: Draft

## Overview and Motivation

QueryChat currently operates on a single table. Users pass one data source and receive a chat interface for querying and filtering that table. This design simplifies the API and implementation but limits users who need to:

1. **Ask questions across related tables** - "Which customers placed orders over $500?" requires joining `customers` and `orders`
2. **Explore multiple datasets in one session** - Switch between unrelated tables without creating separate QueryChat instances
3. **Drill down from summary to detail** - Start with aggregates, then explore underlying records

This design extends QueryChat to support multiple tables while preserving backwards compatibility for single-table use cases.

### Core Principles

- **Progressive complexity**: Single-table usage remains unchanged. Multi-table features are additive.
- **LLM handles JOINs for queries**: The Query tool can JOIN/aggregate across tables to answer questions
- **Independent filters**: Each table maintains its own filter state. Users coordinate cross-table filtering if needed.
- **Fail loudly**: Ambiguous operations (like `.df()` with multiple tables) raise helpful errors rather than guessing

### Scope

This design covers:
- API for adding multiple data sources
- Relationship specification between tables
- Filter behavior across tables
- Accessor APIs (`.df()`, `.sql()`, `.title()`)
- UI considerations

Out of scope (future work):
- Coordinated/cascading filters across related tables
- SQL-like visualization language integration

---

## API for Adding Tables

### Constructor (unchanged for single table)

```python
# Python
qc = QueryChat(orders_df, "orders")

# R
qc <- QueryChat$new(orders_df, "orders")
```

### Adding Additional Tables

```python
# Python
qc.add_table(customers_df, "customers")

# R
qc$add_table(customers_df, "customers")
```

### Removing Tables

```python
qc.remove_table("customers")
```

### Specifying Relationships

Three mechanisms, usable together:

```python
# 1. Explicit foreign keys
qc.add_table(orders_df, "orders",
    relationships={"customer_id": "customers.id"})

# 2. Auto-detect (database connections, on by default)
qc.add_table("orders")  # Infers relationships from DB metadata
qc.add_table("orders", infer_relationships=False)  # Opt-out

# 3. Free-text description
qc.add_table(orders_df, "orders",
    description="Each order links to customers via customer_id")
```

### Database Connections

For database connections, no tables are included by default. Users add tables explicitly, gaining auto-detected relationships:

```python
qc = QueryChat(db_connection)
qc.add_table("orders")     # Relationships inferred from FK metadata
qc.add_table("customers")  # Same
```

### Timing Constraint

Tables must be added before `.server()` is called.

---

## Accessor API

### The `.table()` Compound Accessor

Each table's state is accessed through `.table("name")`:

```python
# Python
qc.table("orders").df()      # Filtered dataframe (reactive)
qc.table("orders").sql()     # Current filter SQL (reactive)
qc.table("orders").title()   # Filter description (reactive)

# R
qc$table("orders")$df()
qc$table("orders")$sql()
qc$table("orders")$title()
```

### Backwards Compatibility for Single-Table

When only one table exists, the existing shortcut methods continue to work:

```python
# These work with single table
qc.df()
qc.sql()
qc.title()
```

### Error on Ambiguity

With multiple tables, bare accessors raise a helpful error:

```python
qc.add_table(customers_df, "customers")  # Now have 2 tables
qc.df()  # Raises: "Multiple tables present. Use qc.table('name').df()"
```

### Listing Available Tables

```python
qc.table_names()  # Returns ["orders", "customers"]
```

### What `.table()` Returns

The `.table("name")` method returns a lightweight object (e.g., `TableAccessor`) that holds a reference to the parent `QueryChat` and the table name. It provides `.df()`, `.sql()`, `.title()` methods that delegate to the appropriate internal state.

---

## Tool Changes

### Query Tool (Q&A)

The query tool remains largely unchanged but gains access to multi-table schema and relationship information. The LLM can write JOINs and aggregations across tables to answer questions:

```
User: "Which customers placed orders over $500?"

LLM uses query tool with:
SELECT c.name, c.email, SUM(o.amount) as total
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id
HAVING SUM(o.amount) > 500
```

The system prompt includes all table schemas plus relationship information (explicit, inferred, or described).

### Update Dashboard Tool (Filtering)

This tool gains a required `table` parameter:

```python
# Current tool signature
def update_dashboard(sql_query: str, title: str) -> dict

# New tool signature
def update_dashboard(table: str, sql_query: str, title: str) -> dict
```

The LLM infers which table from context:

```
User: "Show me California customers"
LLM calls: update_dashboard(table="customers", sql_query="SELECT * FROM customers WHERE state = 'CA'", title="California customers")
```

### Validation

- Query must reference the specified table
- Query must return all columns from that table's schema (existing constraint)
- Invalid table name raises error

### Reset Dashboard Tool

Also gains a `table` parameter to reset a specific table's filter:

```python
def reset_dashboard(table: str) -> dict
```

Only per-table reset is supported (no "reset all" operation).

---

## UI Design

### Default Layout: Tabs

The `.app()` method renders multiple tables as tabs:

```python
qc = QueryChat(orders_df, "orders")
qc.add_table(customers_df, "customers")
qc.app()  # Shows chat + tabbed data view
```

Each tab displays:
- Table name as tab label
- Filtered data table
- Current SQL query (collapsed/expandable)
- Filter title/description

Tabs appear in add-order (first added = first tab = focused on load).

### Auto-Switch on Filter

When the LLM filters a table, the UI automatically switches to that tab. User asks "Show California customers" → customers tab becomes active.

### Single Table (unchanged)

With one table, the UI looks identical to today - no tabs, just the data view.

### Building Blocks for Custom Layouts

Power users can construct their own layouts:

```python
# Python (Shiny for Python)
qc.sidebar()                    # Chat interface
qc.table("orders").ui()         # Orders data table + SQL display
qc.table("customers").ui()      # Customers data table + SQL display

# R
qc$sidebar()
qc$table("orders")$ui()
qc$table("customers")$ui()
```

This allows side-by-side layouts, custom tab arrangements, or embedding tables in different pages.

### The `.ui()` Method

Existing `.ui()` method (combined chat + data) continues to work for single table. With multiple tables, it renders the tabbed view. Users wanting full control use the building blocks instead.

---

## System Prompt Changes

### Schema Presentation

The prompt currently describes one table. With multiple tables, schema is presented for each:

```
You have access to a SQL database with the following tables:

<table name="orders">
Columns:
- id (INTEGER)
- customer_id (INTEGER)
- product_id (INTEGER)
- amount (DECIMAL)
- order_date (DATE)
</table>

<table name="customers">
Columns:
- id (INTEGER)
- name (TEXT)
- email (TEXT)
- state (TEXT)
</table>
```

### Relationship Information

Relationships are included after schemas:

```
<relationships>
- orders.customer_id references customers.id
- orders.product_id references products.id
</relationships>
```

For free-text descriptions:

```
<table_descriptions>
- orders: Transaction records. Each order belongs to one customer and contains one product.
- customers: Customer contact information and location.
</table_descriptions>
```

### Tool Instructions

Updated instructions for the filter tool:

```
When filtering data, you must specify which table to filter.
Only one table can be filtered per tool call. The query must
return all columns from the specified table's schema.
```

### Query Tool Instructions

```
For questions spanning multiple tables, use JOINs based on
the relationships provided. Return only the columns needed
to answer the question.
```

---

## Error Handling

### Adding Tables

| Scenario | Behavior |
|----------|----------|
| Duplicate table name | Error: "Table 'orders' already exists" |
| Add after `.server()` called | Error: "Cannot add tables after server initialization" |
| Invalid data source type | Error: "Expected DataFrame or DB connection, got X" |

### Removing Tables

| Scenario | Behavior |
|----------|----------|
| Remove nonexistent table | Error: "Table 'foo' not found" |
| Remove last table | Error: "Cannot remove last table. At least one table required." |
| Remove after `.server()` | Error: "Cannot remove tables after server initialization" |

### Accessor Errors

| Scenario | Behavior |
|----------|----------|
| `.df()` with multiple tables | Error: "Multiple tables present. Use `.table('name').df()`" |
| `.table("foo")` nonexistent | Error: "Table 'foo' not found. Available: orders, customers" |

### Tool Validation Errors

| Scenario | Behavior |
|----------|----------|
| Filter specifies unknown table | Tool returns error to LLM: "Table 'foo' not found" |
| Filter query wrong schema | Tool returns error to LLM: "Query must return all columns from 'orders'" |
| Filter query references wrong table | Tool returns error to LLM: "Query references 'customers' but table='orders'" |

### Relationship Inference Failures

If `infer_relationships=True` but no foreign keys found in DB metadata, silently continue without relationships (not an error - relationships are optional).

---

## Backwards Compatibility

### Fully Backwards Compatible Cases

Existing single-table code works unchanged:

```python
# This continues to work exactly as before
qc = QueryChat(orders_df, "orders")
qc.app()

# Accessors work unchanged
qc.df()
qc.sql()
qc.title()
```

### Breaking Changes

None for single-table usage.

### Soft Breaks (Code Works, But Should Update)

When a user adds a second table to existing code:

```python
qc = QueryChat(orders_df, "orders")
qc.add_table(customers_df, "customers")  # New line

qc.df()  # Now raises error - must use qc.table("orders").df()
```

This is intentional: adding a table is an explicit action, and the error message guides the fix.

### Migration Path

For users adopting multi-table:

1. Add tables with `.add_table()`
2. Update `.df()` → `.table("name").df()` (same for `.sql()`, `.title()`)
3. Optionally add relationship information for better query quality

### Deprecation Strategy

No deprecations needed. The single-table API remains the recommended approach for single-table use cases.

---

## Testing Considerations

### Unit Tests

| Area | Tests |
|------|-------|
| `.add_table()` | Adds table correctly, rejects duplicates, rejects after server init |
| `.remove_table()` | Removes table, errors on nonexistent, errors on last table |
| `.table("name")` | Returns accessor, errors on nonexistent, lists available tables |
| Accessor methods | `.df()`, `.sql()`, `.title()` work via `.table()`, error when ambiguous |
| Relationship parsing | Explicit relationships stored correctly, free-text passed to prompt |

### Integration Tests

| Area | Tests |
|------|-------|
| Multi-table schema in prompt | All tables and relationships appear in system prompt |
| Filter tool with table param | LLM can filter specific table, validation rejects wrong table |
| Query tool with JOINs | LLM can write JOIN queries, results returned correctly |
| Auto-detect relationships | DB foreign keys detected and included in prompt |

### UI Tests

| Area | Tests |
|------|-------|
| Tab rendering | Multiple tables show as tabs |
| Auto-switch | Filtering table X switches to tab X |
| Building blocks | `.table("name").ui()` renders correctly |

### Backwards Compatibility Tests

| Area | Tests |
|------|-------|
| Single-table unchanged | Existing test suite passes without modification |
| Bare accessors | Work with one table, error with multiple |

---

## Open Questions

1. **R/Python parity**: Any language-specific considerations for the API during implementation?
