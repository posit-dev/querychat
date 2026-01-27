Run an exploratory visualization query inline in the chat.

## Input Format

Provide a full ggsql query with both SELECT and VISUALISE clauses:

```sql
SELECT <columns>
FROM <table>
[WHERE <conditions>]
[GROUP BY <columns>]
VISUALISE <mappings>
[DRAW <geom>]
[SCALE <scale_config>]
[FACET <facet_config>]
[LABEL <label_config>]
```

## When to Use

Use this tool when:
- The user asks an exploratory question that benefits from visualization
- You want to show a one-off chart without affecting the dashboard filter
- You need to visualize data with specific SQL transformations

Use `visualize_dashboard` instead when:
- The user wants a persistent chart that updates with filter changes
- The visualization should reflect the current filtered data

## ggsql VISUALISE Syntax

See `visualize_dashboard` tool for full syntax reference.

### Quick Reference

**Mappings:** `VISUALISE col1 AS x, col2 AS y, col3 AS color`

**Geoms:** `point`, `line`, `bar`, `area`, `histogram`, `boxplot`, `text`

**Labels:** `LABEL title => 'Title', x => 'X Label', y => 'Y Label'`

## Examples

**Aggregated bar chart:**
```sql
SELECT region, SUM(sales) as total_sales
FROM orders
GROUP BY region
VISUALISE region AS x, total_sales AS y
DRAW bar
LABEL title => 'Total Sales by Region'
```

**Filtered time series:**
```sql
SELECT date, revenue
FROM sales
WHERE year = 2024
VISUALISE date AS x, revenue AS y
DRAW line
LABEL title => '2024 Revenue Trend'
```

**Correlation scatter with subset:**
```sql
SELECT mpg, horsepower, cylinders
FROM cars
WHERE cylinders IN (4, 6, 8)
VISUALISE mpg AS x, horsepower AS y, cylinders AS color
DRAW point
LABEL title => 'MPG vs HP by Cylinder Count'
```

**Distribution comparison:**
```sql
SELECT age, gender
FROM users
WHERE age BETWEEN 18 AND 65
VISUALISE age
DRAW histogram
FACET WRAP gender
LABEL title => 'Age Distribution by Gender'
```

## Behavior

- Executes the SQL query against the data source
- Renders the visualization inline in the chat
- The chart is also accessible via the Query Plot tab
- Does NOT affect the dashboard filter or filtered data
- Each call replaces the previous query visualization

Parameters
----------
ggsql :
    A full ggsql query with SELECT and VISUALISE clauses. The SELECT portion follows standard {{db_type}} SQL syntax. The VISUALISE portion specifies the chart configuration.
title :
    A brief, user-friendly title for this visualization.

Returns
-------
:
    The visualization rendered inline in the chat, or the error that occurred. The chart will also be accessible in the Query Plot tab. Does not affect the dashboard filter state.
