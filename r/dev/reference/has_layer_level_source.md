# Detect whether a VISUALISE string has a layer-level FROM source

Returns `TRUE` when a DRAW clause defines its own `FROM <source>` via a
MAPPING sub-clause. Querychat replays VISUALISE against a single local
relation, so layer-specific sources cannot be preserved reliably.

## Usage

``` r
has_layer_level_source(visual)
```

## Arguments

- visual:

  A ggsql VISUALISE string.

## Value

`TRUE` if any DRAW clause contains a MAPPING ... FROM source.
