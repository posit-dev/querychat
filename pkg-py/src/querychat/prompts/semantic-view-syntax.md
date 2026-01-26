## SEMANTIC_VIEW() Query Syntax

When Semantic Views are available, use the `SEMANTIC_VIEW()` table function instead of raw SQL.

### Basic Syntax

```sql
SELECT * FROM SEMANTIC_VIEW(
    {view_name}
    METRICS {logical_table}.{metric_name}
    DIMENSIONS {logical_table}.{dimension_name}
    [WHERE {dimension} = 'value']  -- Optional: pre-aggregation filter
)
[WHERE {column} = 'value']  -- Optional: post-aggregation filter
```

### Key Rules

1. **Use `SEMANTIC_VIEW()` function** - Not direct SELECT FROM the view
2. **No GROUP BY needed** - Semantic layer handles aggregation via DIMENSIONS
3. **No JOINs needed within model** - Relationships are pre-defined
4. **No aggregate functions needed** - Metrics are pre-aggregated
5. **Use DDL-defined names** - Metrics and dimensions must match the DDL exactly

### WHERE Clause: Inside vs Outside

- **Inside** (pre-aggregation): Filters base data BEFORE metrics are computed
- **Outside** (post-aggregation): Filters results AFTER metrics are computed

```sql
-- Pre-aggregation: only include 'EXT' accounts in the calculation
SELECT * FROM SEMANTIC_VIEW(
    MODEL_NAME
    METRICS T_DATA.NET_REVENUE
    DIMENSIONS REF_ENTITIES.ACC_TYPE_CD
    WHERE REF_ENTITIES.ACC_TYPE_CD = 'EXT'
)

-- Post-aggregation: compute all, then filter results
SELECT * FROM SEMANTIC_VIEW(
    MODEL_NAME
    METRICS T_DATA.NET_REVENUE
    DIMENSIONS REF_ENTITIES.ACC_TYPE_CD
)
WHERE NET_REVENUE > 1000000
```

### Common Patterns

**Single metric (total):**
```sql
SELECT * FROM SEMANTIC_VIEW(MODEL_NAME METRICS T_DATA.NET_REVENUE)
```

**Metric by dimension:**
```sql
SELECT * FROM SEMANTIC_VIEW(
    MODEL_NAME
    METRICS T_DATA.NET_REVENUE
    DIMENSIONS REF_ENTITIES.ACC_TYPE_CD
)
```

**Multiple metrics and dimensions:**
```sql
SELECT * FROM SEMANTIC_VIEW(
    MODEL_NAME
    METRICS T_DATA.NET_REVENUE, T_DATA.GROSS_REVENUE
    DIMENSIONS REF_ENTITIES.ACC_TYPE_CD, T_DATA.LOG_DT
)
ORDER BY LOG_DT ASC
```

**Time series:**
```sql
SELECT * FROM SEMANTIC_VIEW(
    MODEL_NAME
    METRICS T_DATA.NET_REVENUE
    DIMENSIONS T_DATA.LOG_DT
)
ORDER BY LOG_DT ASC
```

**Join results with other data:**
```sql
SELECT sv.*, lookup.category_name
FROM SEMANTIC_VIEW(
    MODEL_NAME
    METRICS T_DATA.NET_REVENUE
    DIMENSIONS REF_ENTITIES.ACC_TYPE_CD
) AS sv
JOIN category_lookup AS lookup ON sv.ACC_TYPE_CD = lookup.code
```

### Troubleshooting

- **"Invalid identifier"**: Verify metric/dimension names match exactly what's in the DDL
- **Syntax error**: Use SEMANTIC_VIEW() function, GROUP BY isn't needed
