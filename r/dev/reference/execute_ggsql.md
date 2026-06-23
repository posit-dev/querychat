# Execute a pre-validated ggsql query against an executor

Executes the SQL portion through an executor (preserving database
pushdown), then feeds the result into a ggsql DuckDB reader to produce a
Spec.

## Usage

``` r
execute_ggsql(executor, validated)
```

## Arguments

- executor:

  A querychat QueryExecutor R6 object.

- validated:

  A pre-validated ggsql query (from
  [`ggsql::ggsql_validate()`](https://r.ggsql.org/reference/ggsql_validate.html)).
  Must be a list with `$sql` and `$visual` fields.

## Value

A `ggsql::Spec` R6 object (the writer-independent plot specification).
