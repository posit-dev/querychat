Create or update a persistent visualization for the dashboard's Filter Plot tab.

## Input Format

Provide a VISUALISE-only specification (no SELECT statement). The visualization will be applied to the current filtered/sorted data.

## ggsql VISUALISE Syntax

```
VISUALISE <mappings>
[DRAW <geom>]
[SCALE <scale_config>]
[FACET <facet_config>]
[COORD <coord_config>]
[LABEL <label_config>]
[THEME <theme_config>]
```

### Mappings
- Basic: `VISUALISE x, y` (column names map to x/y aesthetics)
- Named: `VISUALISE date AS x, revenue AS y, region AS color`
- With aggregation: `VISUALISE category AS x, SUM(amount) AS y`

### DRAW Geoms
- `point` - scatter plot
- `line` - line chart
- `bar` - bar chart
- `area` - area chart
- `histogram` - histogram (use `DRAW histogram` with single variable)
- `boxplot` - box plot
- `text` - text labels

### SCALE Configuration
- Type: `SCALE x TYPE log`, `SCALE y TYPE sqrt`
- Palette: `SCALE color PALETTE 'viridis'`, `SCALE color PALETTE 'category10'`
- Domain: `SCALE x DOMAIN [0, 100]`

### FACET Configuration
- Wrap: `FACET WRAP region`
- Grid: `FACET GRID row => year, col => quarter`

### COORD Configuration
- Flip: `COORD flip`
- Polar: `COORD polar`

### LABEL Configuration
- Title: `LABEL title => 'Sales by Region'`
- Axes: `LABEL x => 'Date', y => 'Revenue ($)'`
- Caption: `LABEL caption => 'Data source: internal sales'`

### THEME Configuration
- Built-in: `THEME dark`, `THEME minimal`

## Examples

**Simple scatter plot:**
```
VISUALISE mpg AS x, hp AS y
DRAW point
LABEL title => 'MPG vs Horsepower'
```

**Bar chart with color:**
```
VISUALISE category AS x, COUNT(*) AS y, category AS color
DRAW bar
LABEL title => 'Count by Category'
```

**Time series:**
```
VISUALISE date AS x, revenue AS y
DRAW line
LABEL title => 'Revenue Over Time', x => 'Date', y => 'Revenue'
```

**Faceted histogram:**
```
VISUALISE age
DRAW histogram
FACET WRAP gender
LABEL title => 'Age Distribution by Gender'
```

## Behavior

- The visualization is applied to the **current filtered data** (after any `update_dashboard` filters)
- When filters change, the visualization automatically re-renders with the new data
- The chart appears in the Filter Plot tab
- Calling this tool again replaces the previous filter visualization

Parameters
----------
viz_spec :
    A ggsql VISUALISE specification (without SELECT). Must include at least a VISUALISE clause with column mappings. Optional clauses: DRAW, SCALE, FACET, COORD, LABEL, THEME.
title :
    A brief, user-friendly title for this visualization.

Returns
-------
:
    A confirmation that the dashboard visualization was updated successfully, or the error that occurred. The visualization will appear in the Filter Plot tab and will automatically update when filters change.
