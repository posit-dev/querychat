## Maps with ggsql (spatial)

The `maps` capability is enabled: the DuckDB `spatial` extension is already installed and loaded on the ggsql compute connection. Do NOT write `INSTALL spatial` or `LOAD spatial` — querychat has handled spatial setup.

The two query paths differ in what SQL is available. `querychat_query` runs on the user's database, where `ST_*` spatial functions may not exist — keep spatial logic out of data queries. Visualization queries run on ggsql's DuckDB connection, where the spatial extension IS loaded, so `ST_*` functions (e.g. `ST_Within`, `ST_Point`) are available in the SELECT clause of a `VISUALISE` query when ggsql clauses alone can't express the logic (e.g. point-in-polygon joins).

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

`ggsql:world` is reachable only from visualization queries — the data-query tool cannot read it. To answer questions about map coverage (e.g. "which countries are missing from this map?"), don't refuse: use a visualization query with an anti-join (`LEFT JOIN ... WHERE ... IS NULL`) against `ggsql:world`.

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

### Spatial joins (point-in-polygon)

To aggregate point data by country (e.g. earthquake counts per country), spatially join against `ggsql:world` in the SELECT clause. One gotcha: when `ggsql:world` is staged for a join, its `geom` column arrives as WKB `BLOB`, not `GEOMETRY` — wrap it with `ST_GeomFromWKB()` or the join fails with `No function matches ... 'ST_Within(GEOMETRY, BLOB)'`. Aggregate first, then join the geometry on last:

```sql
WITH counts AS (
  SELECT w.iso_a3, COUNT(*) AS quakes
  FROM ggsql:world w
  JOIN earthquakes e
    ON ST_Within(ST_Point(e.longitude, e.latitude), ST_GeomFromWKB(w.geom))
  GROUP BY w.iso_a3
)
SELECT w.name, w.geom, c.quakes
FROM ggsql:world w
JOIN counts c ON w.iso_a3 = c.iso_a3
VISUALISE
DRAW spatial MAPPING quakes AS fill
```

### Projections

`PROJECT TO <name>` sets the map projection. Useful named projections: `geographic` (unprojected lon/lat), `mercator`, `natural` (Natural Earth), `robinson`, `equal_earth`, `orthographic`, `albers` (US-centric). Set the view center with `SETTING origin => (lon, lat)`, e.g. `PROJECT TO orthographic SETTING origin => (-98, 39)` for a US globe. For anything else, use `PROJECT TO crs SETTING target => 'EPSG:XXXX'` or a proj string. `SCALE lon`/`SCALE lat` limits transfer to the projection.

`SETTING origin` re-centers the map but does NOT zoom — a regional map with only `origin` still shows the whole world. To frame a region, also bound the view with `SCALE lon FROM (min, max)` and `SCALE lat FROM (min, max)`.

The ocean (sphere) background and graticule are drawn by the renderer and cannot be restyled — no setting is exposed for them, so explain the limitation rather than guessing one.

Keep maps simple: one `spatial` layer for boundaries plus at most one or two data layers. Do not put geometry columns in `GROUP BY` — join them on last, in the final SELECT.
