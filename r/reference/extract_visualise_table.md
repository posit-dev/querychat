# Extract the table name from a VISUALISE clause's FROM, if present

Looks only in the portion of the visual string before the first DRAW
keyword, so FROM clauses inside DRAW (e.g., MAPPING x FROM other) are
ignored.

## Usage

``` r
extract_visualise_table(visual)
```

## Arguments

- visual:

  A ggsql VISUALISE string.

## Value

The table name string (possibly quoted), or `NULL` if not present.
