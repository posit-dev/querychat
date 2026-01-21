from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import chevron

if TYPE_CHECKING:
    from ._datasource import DataSource
    from ._querychat_base import TOOL_GROUPS


# Reference documentation for SEMANTIC_VIEW() query syntax
SEMANTIC_VIEW_SYNTAX = """
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
"""


class QueryChatSystemPrompt:
    """Manages system prompt template and component assembly."""

    def __init__(
        self,
        prompt_template: str | Path,
        data_source: DataSource,
        data_description: str | Path | None = None,
        extra_instructions: str | Path | None = None,
        categorical_threshold: int = 10,
    ):
        """
        Initialize with prompt components.

        Args:
            prompt_template: Mustache template string or path to template file
            data_source: DataSource instance for schema generation
            data_description: Optional data context (string or path)
            extra_instructions: Optional custom LLM instructions (string or path)
            categorical_threshold: Threshold for categorical column detection

        """
        if isinstance(prompt_template, Path):
            self.template = prompt_template.read_text()
        else:
            self.template = prompt_template

        if isinstance(data_description, Path):
            self.data_description = data_description.read_text()
        else:
            self.data_description = data_description

        if isinstance(extra_instructions, Path):
            self.extra_instructions = extra_instructions.read_text()
        else:
            self.extra_instructions = extra_instructions

        self.schema = data_source.get_schema(
            categorical_threshold=categorical_threshold
        )

        self.categorical_threshold = categorical_threshold
        self.data_source = data_source

    def render(self, tools: tuple[TOOL_GROUPS, ...] | None) -> str:
        """
        Render system prompt with tool configuration.

        Args:
            tools: Normalized tuple of tool groups to enable (already normalized by caller)

        Returns:
            Fully rendered system prompt string

        """
        db_type = self.data_source.get_db_type()
        is_duck_db = db_type.lower() == "duckdb"
        is_snowflake = db_type.lower() == "snowflake"

        # Check for semantic views (only available with SnowflakeSource)
        # Use getattr to safely access the property that only exists on SnowflakeSource
        has_semantic_views: bool = getattr(self.data_source, "has_semantic_views", False)

        context = {
            "db_type": db_type,
            "is_duck_db": is_duck_db,
            "is_snowflake": is_snowflake,
            "has_semantic_views": has_semantic_views,
            "semantic_view_syntax": SEMANTIC_VIEW_SYNTAX if has_semantic_views else "",
            "schema": self.schema,
            "data_description": self.data_description,
            "extra_instructions": self.extra_instructions,
            "has_tool_update": "update" in tools if tools else False,
            "has_tool_query": "query" in tools if tools else False,
            "include_query_guidelines": len(tools or ()) > 0,
        }

        return chevron.render(self.template, context)
