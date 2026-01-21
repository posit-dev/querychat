#' System Prompt Management for QueryChat
#'
#' @description
#' `QueryChatSystemPrompt` is an R6 class that encapsulates system prompt
#' template and component management for QueryChat. It handles loading of
#' prompt templates, data descriptions, and extra instructions from files or
#' strings, and renders them with tool configuration using Mustache templates.
#'
#' @noRd
QueryChatSystemPrompt <- R6::R6Class(
  "QueryChatSystemPrompt",

  public = list(
    #' @field template The Mustache template string for the system prompt, or
    #'   a path to a file containing a system prompt template.
    template = NULL,

    #' @field data_description Optional description of the data context, or a
    #'   path to a file containing the data description.
    data_description = NULL,

    #' @field extra_instructions Optional custom instructions for the LLM, or a
    #'   path to a file containing the extra instructions.
    extra_instructions = NULL,

    #' @field schema The database schema information.
    schema = NULL,

    #' @field categorical_threshold Threshold for categorical column detection.
    categorical_threshold = NULL,

    #' @field data_source Reference to the data source object.
    data_source = NULL,

    #' @description
    #' Create a new QueryChatSystemPrompt object.
    #'
    #' @param prompt_template Path to template file or template string.
    #' @param data_source A DataSource object for schema access.
    #' @param data_description Optional path to data description file or description string.
    #' @param extra_instructions Optional path to instructions file or instructions string.
    #' @param categorical_threshold Threshold for categorical column detection (default: 10).
    #'
    #' @return A new `QueryChatSystemPrompt` object.
    initialize = function(
      prompt_template,
      data_source,
      data_description = NULL,
      extra_instructions = NULL,
      categorical_threshold = 10
    ) {
      # Load template (file or string) using helper
      self$template <- read_text(prompt_template)

      # Load data_description (file, string, or NULL)
      if (!is.null(data_description)) {
        self$data_description <- read_text(data_description)
      }

      # Load extra_instructions (file, string, or NULL)
      if (!is.null(extra_instructions)) {
        self$extra_instructions <- read_text(extra_instructions)
      }

      # Store schema and other fields
      self$schema <- data_source$get_schema(
        categorical_threshold = categorical_threshold
      )
      self$categorical_threshold <- categorical_threshold
      self$data_source <- data_source
    },

    #' @description
    #' Render the system prompt with tool configuration.
    #'
    #' @param tools Character vector of tool names to enable (e.g.,
    #'   `c("query", "update"))`, or `NULL` for no tools.
    #'
    #' @return A character string containing the rendered system prompt.
    render = function(tools) {
      # Build context for whisker rendering
      db_type <- self$data_source$get_db_type()
      is_duck_db <- tolower(db_type) == "duckdb"
      is_snowflake <- tolower(db_type) == "snowflake"

      # Check for semantic views (only available with SnowflakeSource)
      has_semantic_views <- FALSE
      if (
        inherits(self$data_source, "SnowflakeSource") &&
          self$data_source$has_semantic_views()
      ) {
        has_semantic_views <- TRUE
      }

      context <- list(
        db_type = db_type,
        is_duck_db = is_duck_db,
        is_snowflake = if (is_snowflake) "true",
        has_semantic_views = if (has_semantic_views) "true",
        semantic_view_syntax = if (has_semantic_views) SEMANTIC_VIEW_SYNTAX,
        schema = self$schema,
        data_description = self$data_description,
        extra_instructions = self$extra_instructions,
        has_tool_update = if ("update" %in% tools) "true",
        has_tool_query = if ("query" %in% tools) "true",
        include_query_guidelines = if (length(tools) > 0) "true"
      )

      whisker::whisker.render(self$template, context)
    }
  )
)

# Reference documentation for SEMANTIC_VIEW() query syntax
# nolint start: line_length_linter.
SEMANTIC_VIEW_SYNTAX <- '
## SEMANTIC_VIEW() Query Syntax

When Semantic Views are available, use the `SEMANTIC_VIEW()` table function instead of raw SQL.

### Basic Syntax

```sql
SELECT * FROM SEMANTIC_VIEW(
    {view_name}
    METRICS {logical_table}.{metric_name}
    DIMENSIONS {logical_table}.{dimension_name}
    [WHERE {dimension} = \'value\']  -- Optional: pre-aggregation filter
)
[WHERE {column} = \'value\']  -- Optional: post-aggregation filter
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
-- Pre-aggregation: only include \'EXT\' accounts in the calculation
SELECT * FROM SEMANTIC_VIEW(
    MODEL_NAME
    METRICS T_DATA.NET_REVENUE
    DIMENSIONS REF_ENTITIES.ACC_TYPE_CD
    WHERE REF_ENTITIES.ACC_TYPE_CD = \'EXT\'
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

- **"Invalid identifier"**: Verify metric/dimension names match exactly what is in the DDL
- **Syntax error**: Use SEMANTIC_VIEW() function, GROUP BY is not needed
'
# nolint end

# Utility function for loading file or string content
read_text <- function(x) {
  if (file.exists(x)) {
    read_utf8(x)
  } else {
    paste(x, collapse = "\n")
  }
}
