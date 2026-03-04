Run an exploratory visualization query inline in the chat.

## When to Use

- The user asks an exploratory question that benefits from visualization
- You want to show a one-off chart without affecting the dashboard filter
- You need to visualize data with specific SQL transformations

## Behavior

- Executes the SQL query against the data source
- Renders the visualization inline in the chat
- The chart is also accessible via the Query Plot tab
- Does NOT affect the dashboard filter or filtered data
- Each call replaces the previous query visualization
- The `title` parameter is displayed as the card header above the chart — do NOT also put a title in the ggsql query via `LABEL title => ...` as it will be redundant
- Always provide the `title` parameter with a brief, descriptive title for the visualization

## ggsql Syntax Reference

### Quick Reference

```sql
[WITH cte AS (...), ...]
[SELECT columns FROM table WHERE conditions]
VISUALISE [mappings] [FROM source]
DRAW geom_type
    [MAPPING col AS aesthetic, ... FROM source]
    [REMAPPING stat AS aesthetic, ...]
    [SETTING param => value, ...]
    [FILTER sql_condition]
    [PARTITION BY col, ...]
    [ORDER BY col [ASC|DESC], ...]
[SCALE [TYPE] aesthetic [FROM ...] [TO ...] [VIA ...] [SETTING ...] [RENAMING ...]]
[COORD type SETTING property => value, ...]
[FACET var | row_var BY col_var [SETTING free => 'x'|'y'|['x','y'], ncol => N]]
[LABEL x => '...', y => '...', ...]
[THEME name [SETTING property => value, ...]]
```

### VISUALISE Clause

Entry point for visualization. Marks where SQL ends and visualization begins.

```sql
-- After SELECT (most common)
SELECT date, revenue, region FROM sales
VISUALISE date AS x, revenue AS y, region AS color
DRAW line

-- Shorthand with FROM (auto-generates SELECT * FROM)
VISUALISE FROM sales
DRAW bar MAPPING region AS x, total AS y
```

### Mapping Styles

| Style | Syntax | Use When |
|-------|--------|----------|
| Explicit | `date AS x` | Column name differs from aesthetic |
| Implicit | `x` | Column name equals aesthetic name |
| Wildcard | `*` | Map all matching columns automatically |
| Literal | `'string' AS color` | Use a literal value (for legend labels in multi-layer plots) |

### DRAW Clause (Layers)

Multiple DRAW clauses create layered visualizations.

```sql
DRAW geom_type
    [MAPPING col AS aesthetic, ... FROM source]
    [REMAPPING stat AS aesthetic, ...]
    [SETTING param => value, ...]
    [FILTER sql_condition]
    [PARTITION BY col, ...]
    [ORDER BY col [ASC|DESC], ...]
```

**Geom types:**

| Category | Types |
|----------|-------|
| Basic | `point`, `line`, `path`, `bar`, `area`, `tile`, `polygon`, `ribbon` |
| Statistical | `histogram`, `density`, `smooth`, `boxplot`, `violin` |
| Annotation | `text`, `label`, `segment`, `arrow`, `hline`, `vline`, `abline`, `errorbar` |

**Aesthetics (MAPPING):**

| Category | Aesthetics |
|----------|------------|
| Position | `x`, `y`, `xmin`, `xmax`, `ymin`, `ymax`, `xend`, `yend` |
| Color | `color`/`colour`, `fill`, `stroke`, `opacity` |
| Size/Shape | `size`, `shape`, `linewidth`, `linetype`, `width`, `height` |
| Text | `label`, `family`, `fontface`, `hjust`, `vjust` |
| Aggregation | `weight` (for histogram/bar/density/violin) |

**Layer-specific data source:** Each layer can use a different data source:

```sql
WITH summary AS (SELECT region, SUM(sales) as total FROM sales GROUP BY region)
SELECT * FROM sales
VISUALISE date AS x, amount AS y
DRAW line
DRAW bar MAPPING region AS x, total AS y FROM summary
```

**PARTITION BY** groups data without visual encoding (useful for separate lines per group without color):

```sql
DRAW line PARTITION BY category
```

**ORDER BY** controls row ordering within a layer:

```sql
DRAW line ORDER BY date ASC
```

### Statistical Layers and REMAPPING

Some layers compute statistics. Use REMAPPING to access computed values:

| Layer | Computed Stats | Default Remapping |
|-------|---------------|-------------------|
| `bar` (y unmapped) | `count`, `proportion` | `count AS y` |
| `histogram` | `count`, `density` | `count AS y` |
| `density` | `density`, `intensity` | `density AS y` |
| `violin` | `density`, `intensity` | `density AS offset` |
| `boxplot` | `value`, `type` | `value AS y` |

`density` computes a KDE from a continuous `x`. Settings: `bandwidth` (numeric), `adjust` (multiplier, default 1), `kernel` (`'gaussian'` default, `'epanechnikov'`, `'triangular'`, `'rectangular'`, `'biweight'`, `'cosine'`), `stacking` (`'off'` default, `'on'`, `'fill'`). Use `REMAPPING intensity AS y` to show unnormalized density that reflects group size differences.

`violin` displays mirrored KDE curves for groups. Requires both `x` (categorical) and `y` (continuous). Accepts the same bandwidth/adjust/kernel settings as density. Use `REMAPPING intensity AS offset` to reflect group size differences.

**Examples:**

```sql
-- Density histogram (instead of count)
VISUALISE FROM products
DRAW histogram MAPPING price AS x REMAPPING density AS y

-- Bar showing proportion
VISUALISE FROM sales
DRAW bar MAPPING region AS x REMAPPING proportion AS y

-- Overlay histogram and density on the same scale
VISUALISE FROM measurements
DRAW histogram MAPPING value AS x SETTING opacity => 0.5
DRAW density MAPPING value AS x REMAPPING intensity AS y SETTING opacity => 0.5

-- Violin plot
SELECT department, salary FROM employees
VISUALISE department AS x, salary AS y
DRAW violin
```

### SCALE Clause

Configures how data maps to visual properties. All sub-clauses are optional; type and transform are auto-detected from data when omitted.

```sql
SCALE [TYPE] aesthetic [FROM range] [TO output] [VIA transform] [SETTING prop => value, ...] [RENAMING ...]
```

**Type identifiers** (optional — auto-detected if omitted):

| Type | Description |
|------|-------------|
| `CONTINUOUS` | Numeric data on a continuous axis |
| `DISCRETE` | Categorical/nominal data |
| `BINNED` | Pre-bucketed data |
| `ORDINAL` | Ordered categories with interpolated output |
| `IDENTITY` | Data values are already visual values (e.g., literal hex colors) |

**FROM** — input domain:
```sql
SCALE x FROM [0, 100]           -- explicit min and max
SCALE x FROM [0, null]          -- explicit min, auto max
SCALE DISCRETE x FROM ['A', 'B', 'C']  -- explicit category order
```

**TO** — output range or palette:
```sql
SCALE color TO navia             -- named palette (default continuous: navia)
SCALE color TO viridis           -- other continuous: viridis, plasma, inferno, magma, cividis, batlow
SCALE color TO vik               -- diverging: vik, rdbu, rdylbu, spectral, brbg
SCALE DISCRETE color TO ggsql10  -- discrete (default: ggsql10): tableau10, category10, set1, set2, dark2
SCALE color TO ['red', 'blue']   -- explicit color array
SCALE size TO [1, 10]            -- numeric output range
```

**VIA** — transformation:
```sql
SCALE x VIA date                 -- date axis (auto-detected from Date columns)
SCALE x VIA datetime             -- datetime axis
SCALE y VIA log10                -- base-10 logarithm
SCALE y VIA sqrt                 -- square root
```

| Category | Transforms |
|----------|------------|
| Logarithmic | `log10`, `log2`, `log` (natural) |
| Power | `sqrt`, `square` |
| Exponential | `exp`, `exp2`, `exp10` |
| Other | `asinh`, `pseudo_log` |
| Temporal | `date`, `datetime`, `time` |
| Type coercion | `integer`, `string`, `bool` |

**SETTING** — additional properties:
```sql
SCALE x SETTING breaks => 5                -- number of tick marks
SCALE x SETTING breaks => '2 months'       -- interval-based breaks
SCALE x SETTING expand => 0.05             -- expand scale range by 5%
SCALE x SETTING reverse => true            -- reverse direction
```

**RENAMING** — custom axis/legend labels:
```sql
SCALE DISCRETE x RENAMING 'A' => 'Alpha', 'B' => 'Beta'
SCALE CONTINUOUS x RENAMING * => '{} units'         -- template for all labels
SCALE x VIA date RENAMING * => '{:time %b %Y}'     -- date label formatting
```

### Date/Time Axes

Temporal transforms are auto-detected from column data types. Use `VIA date` explicitly only when the column isn't typed as Date (e.g., after `DATE_TRUNC` which returns timestamps).

**Break intervals:**
```sql
SCALE x SETTING breaks => 'month'        -- one break per month
SCALE x SETTING breaks => '2 weeks'      -- every 2 weeks
SCALE x SETTING breaks => '3 months'     -- quarterly
SCALE x SETTING breaks => 'year'         -- yearly
```

Valid units: `day`, `week`, `month`, `year` (for date); also `hour`, `minute`, `second` (for datetime/time).

**Date label formatting** (strftime syntax):
```sql
SCALE x VIA date RENAMING * => '{:time %b %Y}'       -- "Jan 2024"
SCALE x VIA date RENAMING * => '{:time %B %d, %Y}'   -- "January 15, 2024"
SCALE x VIA date RENAMING * => '{:time %b %d}'        -- "Jan 15"
```

### COORD Clause

Sets coordinate system. Types: `cartesian` (default), `flip`, `polar`, `fixed`, `trans`, `map`, `quickmap`.

```sql
COORD cartesian SETTING xlim => [0, 100], ylim => [0, 50]
COORD polar                   -- Pie/radial charts
COORD polar SETTING theta => y
```

**WARNING:** `COORD flip` is currently broken and produces empty charts. Avoid using it.

### FACET Clause

Creates small multiples (subplots by category).

```sql
FACET category                               -- Single variable, wrapped layout
FACET row_var BY col_var                     -- Grid layout (rows x columns)
FACET category SETTING free => 'y'           -- Independent y-axes
FACET category SETTING free => ['x', 'y']   -- Independent both axes
FACET category SETTING ncol => 4             -- Control number of columns
```

Custom strip labels via SCALE:
```sql
FACET region
SCALE panel RENAMING 'N' => 'North', 'S' => 'South'
```

### LABEL Clause

Use LABEL for axis labels only. Do NOT use `title =>` — the tool's `title` parameter handles chart titles.

```sql
LABEL x => 'X Axis Label', y => 'Y Axis Label'
```

### THEME Clause

Available themes: `minimal`, `classic`, `gray`/`grey`, `bw`, `dark`, `light`, `void`

```sql
THEME minimal
THEME dark
THEME classic SETTING background => '#f5f5f5'
```

## Complete Examples

**Line chart with multiple series:**
```sql
SELECT date, revenue, region FROM sales WHERE year = 2024
VISUALISE date AS x, revenue AS y, region AS color
DRAW line
SCALE x VIA date
LABEL x => 'Date', y => 'Revenue ($)'
THEME minimal
```

**Bar chart (auto-count):**
```sql
VISUALISE FROM products
DRAW bar MAPPING category AS x
```

**Scatter plot with trend line:**
```sql
SELECT mpg, hp, cylinders FROM cars
VISUALISE mpg AS x, hp AS y
DRAW point MAPPING cylinders AS color
DRAW smooth
```

**Histogram with density overlay:**
```sql
VISUALISE FROM measurements
DRAW histogram MAPPING value AS x SETTING bins => 20, opacity => 0.5
DRAW density MAPPING value AS x REMAPPING intensity AS y SETTING opacity => 0.5
```

**Density plot with groups:**
```sql
VISUALISE FROM measurements
DRAW density MAPPING value AS x, category AS color SETTING opacity => 0.7
```

**Faceted chart:**
```sql
SELECT month, sales, region FROM data
VISUALISE month AS x, sales AS y
DRAW line
DRAW point
FACET region
SCALE x VIA date
```

**CTE with aggregation and date formatting:**
```sql
WITH monthly AS (
    SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as total
    FROM orders GROUP BY 1
)
VISUALISE month AS x, total AS y FROM monthly
DRAW line
DRAW point
SCALE x VIA date SETTING breaks => 'month' RENAMING * => '{:time %b %Y}'
LABEL y => 'Revenue ($)'
```

**Ribbon / confidence band:**
```sql
WITH daily AS (
    SELECT DATE_TRUNC('day', timestamp) as day,
           AVG(temperature) as avg_temp,
           MIN(temperature) as min_temp,
           MAX(temperature) as max_temp
    FROM sensor_data
    GROUP BY DATE_TRUNC('day', timestamp)
)
VISUALISE day AS x FROM daily
DRAW ribbon MAPPING min_temp AS ymin, max_temp AS ymax SETTING opacity => 0.3
DRAW line MAPPING avg_temp AS y
SCALE x VIA date
LABEL y => 'Temperature'
```

## Important Notes

1. **Date columns**: Use `SCALE x VIA date` for date/time columns. It's auto-detected from `DATE` columns but needed after `DATE_TRUNC` (which returns `TIMESTAMP`). Customize labels with `RENAMING * => '{:time ...}'` for readable axes.
2. **Multiple layers**: Use multiple DRAW clauses for overlaid visualizations.
3. **Charts vs Tables**: For visualizations use VISUALISE with DRAW. For tabular data use plain SQL without VISUALISE.
4. **CTEs work**: Use `WITH ... SELECT ... VISUALISE` or shorthand `WITH ... VISUALISE FROM cte_name`.
5. **Statistical layers**: When using `histogram`, `bar` (without y), `density`, `violin`, or `boxplot`, the layer computes statistics. Use REMAPPING to access `density`, `intensity`, `proportion`, etc.
6. **Stacked bars via fill**: Map a categorical column to `fill` — there is no `position => 'stack'` setting:
   ```sql
   DRAW bar MAPPING category AS x, subcategory AS fill
   ```
7. **String values use single quotes**: In SETTING, LABEL, and RENAMING clauses, always use single quotes for string values. Double quotes cause parse errors.
8. **Column casing**: DuckDB lowercases unquoted column names. VISUALISE validates column references case-sensitively. Always alias to lowercase in SELECT:
   ```sql
   -- WRONG: uppercase column name
   SELECT ROOM_TYPE, COUNT(*) AS listings FROM airbnb
   VISUALISE ROOM_TYPE AS x, listings AS y
   DRAW bar

   -- CORRECT: alias to lowercase
   SELECT ROOM_TYPE AS room_type, COUNT(*) AS listings FROM airbnb
   VISUALISE room_type AS x, listings AS y
   DRAW bar
   ```
9. **COORD flip is broken**: It currently produces empty charts. Avoid using it.

Parameters
----------
ggsql :
    A full ggsql query with SELECT and VISUALISE clauses. The SELECT portion follows standard {{db_type}} SQL syntax. The VISUALISE portion specifies the chart configuration. Do NOT include `LABEL title => ...` in the query — use the `title` parameter instead.
title :
    Always provide this. A brief, user-friendly title for this visualization. This is displayed as the card header above the chart.

Returns
-------
:
    The visualization rendered inline in the chat, or the error that occurred. The chart will also be accessible in the Query Plot tab. Does not affect the dashboard filter state.
