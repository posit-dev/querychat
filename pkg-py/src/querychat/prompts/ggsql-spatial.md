## Maps with ggsql (spatial)

The `maps` capability is enabled: the DuckDB `spatial` extension is already installed and loaded. Do NOT write `INSTALL spatial`, `LOAD spatial`, or `ST_*` function calls — querychat has handled spatial setup, and spatial SQL functions may not exist on the user's database. Keep spatial logic in ggsql clauses.

### Choropleths from `ggsql:world`

`ggsql:world` is a builtin dataset of country boundaries (Natural Earth 1:110m) with columns: `name`, `iso_a3`, `continent`, `subregion`, `income_group`, `population`, `gdp`, `geom` (geometry). It is resolved by ggsql, not the user's database — but you can join it with the user's tables in the SELECT clause and ggsql will stage the join itself.

To map the user's data, join it to `ggsql:world` on `iso_a3` (preferred) or `name`, then `DRAW spatial` with a fill mapping:

```sql
SELECT w.name, w.geom, s.revenue
FROM ggsql:world w JOIN sales_by_country s ON w.iso_a3 = s.country_code
VISUALISE
DRAW spatial MAPPING revenue AS fill
```

The geometry column is auto-detected; declare `MAPPING geom AS geometry` explicitly only if detection fails. Before joining, inspect the user's identifier values (e.g. with the schema or query tool): country names vary ("United States" vs "USA"), and ISO codes only match if the user's column is also ISO 3166-1 alpha-3. Filter to a region with `FILTER continent = 'Europe'` on the DRAW clause when the data only covers one.

### Point maps

For lon/lat columns, map them to `lon`/`lat` (or `x`/`y` with `PROJECT x, y TO <projection>`) and draw `point` over a `ggsql:world` background:

```sql
SELECT city, lon, lat, passengers FROM airports
VISUALISE
DRAW spatial MAPPING null AS fill FROM ggsql:world
DRAW point MAPPING lon, lat, passengers AS size
PROJECT TO natural
```

**Always put `lon`/`lat`/`size` mappings on the `DRAW point` layer, never in the global `VISUALISE` mappings.** Global mappings are inherited by every layer, and the `spatial` background layer only accepts `geometry`/`fill`/`stroke`/`opacity` — a global `lon`/`lat`/`size` mapping fails with "Layer 'spatial' does not support the `lat`, `size`, `lon` mappings". If you see that error, move the point aesthetics out of `VISUALISE` and onto `DRAW point MAPPING ...`.

### Projections

`PROJECT TO <name>` sets the map projection. Useful named projections: `geographic` (unprojected lon/lat), `mercator`, `natural` (Natural Earth), `robinson`, `equal_earth`, `orthographic`, `albers` (US-centric). Set the view center with `SETTING origin => (lon, lat)`, e.g. `PROJECT TO orthographic SETTING origin => (-98, 39)` for a US globe. For anything else, use `PROJECT TO crs SETTING target => 'EPSG:XXXX'` or a proj string. `SCALE lon`/`SCALE lat` limits transfer to the projection.

Keep maps simple: one `spatial` layer for boundaries plus at most one or two data layers. Do not put geometry columns in `GROUP BY` — join them on last, in the final SELECT.
