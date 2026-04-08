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
[PROJECT [aesthetics] TO coord_system [SETTING ...]]
[FACET var | row_var BY col_var [SETTING free => 'x'|'y'|['x','y'], ncol => N, nrow => N]]
[PLACE geom_type SETTING param => value, ...]
[LABEL x => '...', y => '...', ...]
[THEME name [SETTING property => value, ...]]
```

### VISUALISE Clause

Entry point for visualization. Marks where SQL ends and visualization begins. Mappings in VISUALISE and MAPPING accept **column names only** — no SQL expressions, functions, or casts. All data transformations must happen in the SELECT clause.

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
| Basic | `point`, `line`, `path`, `bar`, `area`, `rect`, `polygon`, `ribbon` |
| Statistical | `histogram`, `density`, `smooth`, `boxplot`, `violin` |
| Annotation | `text`, `segment`, `arrow`, `rule`, `linear`, `errorbar` |

- `path` is like `line` but preserves data order instead of sorting by x.
- `rect` draws rectangles for heatmaps or range indicators. Map `x`/`y` for center (defaults to width/height of 1), or use `xmin`/`xmax`/`ymin`/`ymax` for explicit bounds.
- `smooth` fits a trendline to data. Settings: `method` (`'nw'` default for kernel regression, `'ols'` for linear, `'tls'` for total least squares), `bandwidth`, `adjust`, `kernel`.
- `text` renders text labels. Map `label` for the text content. Settings: `format` (template string for label formatting), `offset` (pixel offset as `[x, y]`).
- `arrow` draws arrows between two points. Requires `x`, `y`, `xend`, `yend` aesthetics.
- `rule` draws full-span reference lines. Map a value to `y` for a horizontal line or `x` for a vertical line.
- `linear` draws diagonal reference lines from `coef` (slope) and `intercept` aesthetics: y = intercept + coef * x.

**Aesthetics (MAPPING):**

| Category | Aesthetics |
|----------|------------|
| Position | `x`, `y`, `xmin`, `xmax`, `ymin`, `ymax`, `xend`, `yend` |
| Color | `color`/`colour`, `fill`, `stroke`, `opacity` |
| Size/Shape | `size`, `shape`, `linewidth`, `linetype`, `width`, `height` |
| Text | `label`, `typeface`, `fontweight`, `italic`, `fontsize`, `hjust`, `vjust`, `rotation` |
| Aggregation | `weight` (for histogram/bar/density/violin) |
| Linear | `coef`, `intercept` (for `linear` layer only) |

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

### PLACE Clause (Annotations)

`PLACE` creates annotation layers with literal values only — no data mappings. Use it for reference lines, text labels, and other fixed annotations. All aesthetics are set via `SETTING` and bypass scaling.

```sql
PLACE geom_type SETTING param => value, ...
```

**Examples:**
```sql
-- Horizontal reference line
PLACE rule SETTING y => 100

-- Vertical reference line
PLACE rule SETTING x => '2024-06-01'

-- Multiple reference lines (array values)
PLACE rule SETTING y => [50, 75, 100]

-- Text annotation
PLACE text SETTING x => 10, y => 50, label => 'Threshold'

-- Diagonal reference line
PLACE linear SETTING coef => 0.4, intercept => -1
```

`PLACE` supports any geom type but is most useful with `rule`, `linear`, `text`, `segment`, and `rect`. Unlike `DRAW`, `PLACE` has no `MAPPING`, `FILTER`, `PARTITION BY`, or `ORDER BY` sub-clauses.

### Statistical Layers and REMAPPING

Some layers compute statistics. Use REMAPPING to access computed values:

| Layer | Computed Stats | Default Remapping |
|-------|---------------|-------------------|
| `bar` (y unmapped) | `count`, `proportion` | `count AS y` |
| `histogram` | `count`, `density` | `count AS y` |
| `density` | `density`, `intensity` | `density AS y` |
| `violin` | `density`, `intensity` | `density AS offset` |
| `smooth` | `intensity` | `intensity AS y` |
| `boxplot` | `value`, `type` | `value AS y` |

`boxplot` displays box-and-whisker plots. Settings: `outliers` (`true` default — show outlier points), `coef` (`1.5` default — whisker fence coefficient), `width` (`0.9` default — box width, 0–1).

`smooth` fits a trendline to data. Settings: `method` (`'nw'` or `'nadaraya-watson'` default kernel regression, `'ols'` for OLS linear, `'tls'` for total least squares). NW-only settings: `bandwidth` (numeric), `adjust` (multiplier, default 1), `kernel` (`'gaussian'` default, `'epanechnikov'`, `'triangular'`, `'rectangular'`, `'uniform'`, `'biweight'`, `'quartic'`, `'cosine'`).

`density` computes a KDE from a continuous `x`. Settings: `bandwidth` (numeric), `adjust` (multiplier, default 1), `kernel` (`'gaussian'` default, `'epanechnikov'`, `'triangular'`, `'rectangular'`, `'uniform'`, `'biweight'`, `'quartic'`, `'cosine'`), `stacking` (`'off'` default, `'on'`, `'fill'`). Use `REMAPPING intensity AS y` to show unnormalized density that reflects group size differences.

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

**Important — integer columns used as categories:** When an integer column represents categories (e.g., a 0/1 `survived` column), ggsql will treat it as continuous by default. This causes errors when mapping to `fill`, `color`, `shape`, or using it in `FACET`. Two fixes:
- **Preferred:** Cast to string in the SELECT clause: `SELECT CAST(survived AS VARCHAR) AS survived ...`, then map the column by name in VISUALISE: `survived AS fill`
- **Alternative:** Declare the scale: `SCALE DISCRETE fill` or `SCALE fill VIA bool`

**FROM** — input domain:
```sql
SCALE x FROM [0, 100]           -- explicit min and max
SCALE x FROM [0, null]          -- explicit min, auto max
SCALE DISCRETE x FROM ['A', 'B', 'C']  -- explicit category order
```

**TO** — output range or palette:
```sql
SCALE color TO sequential         -- default continuous palette (derived from navia)
SCALE color TO viridis           -- other continuous: viridis, plasma, inferno, magma, cividis, navia, batlow
SCALE color TO vik               -- diverging: vik, rdbu, rdylbu, spectral, brbg, berlin, roma
SCALE DISCRETE color TO ggsql10  -- discrete (default: ggsql10): tableau10, category10, set1, set2, set3, dark2, paired, kelly
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

Temporal transforms are auto-detected from column data types, including after `DATE_TRUNC`.

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

### PROJECT Clause

Sets coordinate system. Use `PROJECT ... TO` to specify coordinates.

**Coordinate systems:** `cartesian` (default), `polar`.

**Polar aesthetics:** In polar coordinates, positional aesthetics use `angle` and `radius` (instead of `x` and `y`). Variants `anglemin`, `anglemax`, `angleend`, `radiusmin`, `radiusmax`, `radiusend` are also available. Typically you map to `x`/`y` and let `PROJECT TO polar` handle the conversion, but you can use `angle`/`radius` explicitly when needed.

```sql
PROJECT TO cartesian                        -- explicit default (usually omitted)
PROJECT y, x TO cartesian                   -- flip axes (maps y to horizontal, x to vertical)
PROJECT TO polar                            -- pie/radial charts
PROJECT TO polar SETTING start => 90        -- start at 3 o'clock
PROJECT TO polar SETTING inner => 0.5       -- donut chart (50% hole)
PROJECT TO polar SETTING start => -90, end => 90  -- half-circle gauge
```

**Cartesian settings:**
- `clip` — clip out-of-bounds data (default `true`)
- `ratio` — enforce aspect ratio between axes

**Polar settings:**
- `start` — starting angle in degrees (0 = 12 o'clock, 90 = 3 o'clock)
- `end` — ending angle in degrees (default: start + 360; use for partial arcs/gauges)
- `inner` — inner radius as proportion 0–1 (0 = full pie, 0.5 = donut with 50% hole)
- `clip` — clip out-of-bounds data (default `true`)

**Axis flipping:** To create horizontal bar charts or flip axes, use `PROJECT y, x TO cartesian`. This maps anything on `y` to the horizontal axis and `x` to the vertical axis.

### FACET Clause

Creates small multiples (subplots by category).

```sql
FACET category                               -- Single variable, wrapped layout
FACET row_var BY col_var                     -- Grid layout (rows x columns)
FACET category SETTING free => 'y'           -- Independent y-axes
FACET category SETTING free => ['x', 'y']   -- Independent both axes
FACET category SETTING ncol => 4             -- Control number of columns
FACET category SETTING nrow => 2             -- Control number of rows (mutually exclusive with ncol)
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

**Horizontal bar chart:**
```sql
SELECT region, COUNT(*) as n FROM sales GROUP BY region
VISUALISE region AS y, n AS x
DRAW bar
PROJECT y, x TO cartesian
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

**Heatmap with rect:**
```sql
SELECT day, month, temperature FROM weather
VISUALISE day AS x, month AS y, temperature AS color
DRAW rect
```

**Threshold reference lines (using PLACE):**
```sql
SELECT date, temperature FROM sensor_data
VISUALISE date AS x, temperature AS y
DRAW line
PLACE rule SETTING y => 100, stroke => 'red', linetype => 'dashed'
LABEL y => 'Temperature (F)'
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

**Text labels on bars:**
```sql
SELECT region, COUNT(*) AS n FROM sales GROUP BY region
VISUALISE region AS x, n AS y
DRAW bar
DRAW text MAPPING n AS label SETTING offset => [0, -11], fill => 'white'
```

**Donut chart:**
```sql
VISUALISE FROM products
DRAW bar MAPPING category AS fill
PROJECT TO polar SETTING inner => 0.5
```

## Important Notes

1. **Numeric columns as categories**: Integer columns representing categories (e.g., 0/1 `survived`) are treated as continuous by default, causing errors with `fill`, `color`, `shape`, and `FACET`. Fix by casting in SQL or declaring the scale:
    ```sql
    -- WRONG: integer fill without discrete scale — causes validation error
    SELECT sex, survived FROM titanic
    VISUALISE sex AS x, survived AS fill
    DRAW bar

    -- CORRECT: cast to string in SQL (preferred)
    SELECT sex, CAST(survived AS VARCHAR) AS survived FROM titanic
    VISUALISE sex AS x, survived AS fill
    DRAW bar

    -- ALSO CORRECT: declare the scale as discrete
    SELECT sex, survived FROM titanic
    VISUALISE sex AS x, survived AS fill
    DRAW bar
    SCALE DISCRETE fill
    ```
2. **Do not mix `VISUALISE FROM` with a preceding `SELECT`**: `VISUALISE FROM table` is shorthand that auto-generates `SELECT * FROM table`. If you already have a `SELECT`, use `SELECT ... VISUALISE` instead:
    ```sql
    -- WRONG: VISUALISE FROM after SELECT
    SELECT * FROM titanic
    VISUALISE FROM titanic
    DRAW bar MAPPING class AS x

    -- CORRECT: use VISUALISE (without FROM) after SELECT
    SELECT * FROM titanic
    VISUALISE class AS x
    DRAW bar

    -- ALSO CORRECT: use VISUALISE FROM without any SELECT
    VISUALISE FROM titanic
    DRAW bar MAPPING class AS x
    ```
3. **String values use single quotes**: In SETTING, LABEL, and RENAMING clauses, always use single quotes for string values. Double quotes cause parse errors.
4. **Column casing**: VISUALISE validates column references case-sensitively. The column name in VISUALISE/MAPPING must exactly match the column name from the SQL result. If a column is aliased as `MyCol`, reference it as `MyCol`, not `mycol` or `MYCOL`.
5. **Charts vs Tables**: For visualizations use VISUALISE with DRAW. For tabular data use plain SQL without VISUALISE.
6. **Statistical layers**: When using `histogram`, `bar` (without y), `density`, `smooth`, `violin`, or `boxplot`, the layer computes statistics. Use REMAPPING to access `density`, `intensity`, `proportion`, etc.
7. **Bar position adjustments**: Bars stack automatically when `fill` is mapped. Use `SETTING position => 'dodge'` for side-by-side bars, or `position => 'fill'` for proportional stacking:
   ```sql
   DRAW bar MAPPING category AS x, subcategory AS fill                       -- stacked (default)
   DRAW bar MAPPING category AS x, subcategory AS fill SETTING position => 'dodge'  -- side-by-side
   ```
8. **Date columns**: Date/time columns are auto-detected as temporal, including after `DATE_TRUNC`. Use `RENAMING * => '{:time ...}'` on the scale to customize date label formatting for readable axes.
9. **Multiple layers**: Use multiple DRAW clauses for overlaid visualizations.
10. **CTEs work**: Use `WITH ... SELECT ... VISUALISE` or shorthand `WITH ... VISUALISE FROM cte_name`.
11. **Axis flipping**: Use `PROJECT y, x TO cartesian` to flip axes (e.g., for horizontal bar charts). This maps `y` to the horizontal axis and `x` to the vertical axis.
