# DataSourceReader Bridge Design

## Problem

querychat executes ggsql queries in two phases: run the SQL on the real database, then replay the VISUALISE portion locally against the result in an in-memory DuckDB. This has two drawbacks:

1. **Scaling** — the full SQL result must be pulled into Python memory, even when ggsql's stat transforms (histogram, density, boxplot) would reduce it to a small summary. A histogram of 10M rows pulls all 10M rows into memory only to bin them into ~30 buckets.

2. **Multi-source layers** — ggsql supports per-layer data sources (e.g., a CTE fed to a different DRAW clause). The two-phase approach loses intermediate tables at the DataSource boundary, so querychat rejects these queries.

Both problems stem from the same root cause: querychat splits the query at the SQL/VISUALISE boundary and runs each half independently, rather than letting ggsql run the full pipeline against the real database.

## Solution

For `SQLAlchemySource` data sources, implement a `DataSourceReader` — a Python object that satisfies ggsql's reader protocol (`execute_sql()`, `register()`, `unregister()`) by routing SQL to the real database. Pass this reader to `ggsql.execute(query, reader)`, letting ggsql run the entire pipeline (parsing, CTEs, stat transforms, everything) against the real DB.

Use [sqlglot](https://github.com/tobymao/sqlglot) to transpile ggsql's ANSI-generated SQL to the target database dialect. This gives broad database coverage (31 dialects) without waiting for ggsql to add each one.

Fall back to the current two-phase approach when the bridge fails (e.g., temp table permission denied, unsupported dialect, transpilation error) or for non-SQLAlchemy data sources.

## Data flow

### Bridge path (SQLAlchemySource)

```
ggsql.execute(query, DataSourceReader)
  │
  ├─ CTE materialization
  │    execute_sql("SELECT … FROM orders GROUP BY …")
  │    → sqlglot transpiles generic → target dialect
  │    → runs on real DB
  │    → result registered as temp table on real DB
  │
  ├─ Global SQL
  │    execute_sql("SELECT * FROM orders WHERE …")
  │    → runs on real DB
  │    → result registered as temp table on real DB
  │
  ├─ Schema queries
  │    execute_sql("SELECT … LIMIT 0")
  │    → runs on real DB against temp tables
  │
  ├─ Stat transforms (histograms, density, boxplot, etc.)
  │    execute_sql("WITH … SELECT … binning SQL …")
  │    → sqlglot transpiles generated ANSI SQL → target dialect
  │    → runs on real DB against temp tables
  │
  └─ Final layer queries
       execute_sql("SELECT …")
       → runs on real DB, small result set returned
```

### Fallback path (current approach, all DataSource types)

```
validated.sql()
  → DataSource.execute_query() on real DB
  → full result pulled into Python memory
  → registered in local DuckDB
  → ggsql replays VISUALISE portion locally
```

## Components

### `DataSourceReader`

Python class implementing ggsql's reader protocol. Lives in `_viz_ggsql.py`.

- **Constructor**: takes a `sqlalchemy.Engine` and a sqlglot dialect string. Opens a single connection from the engine, held for the pipeline's duration.
- **`execute_sql(sql)`**: transpiles from generic SQL to target dialect via `sqlglot.transpile(sql, read="", write=dialect)`, executes on the real DB via SQLAlchemy, returns a polars DataFrame.
- **`register(name, df, replace)`**: creates a `TEMPORARY TABLE` on the real DB with column types derived from polars dtypes (generic SQL types, transpiled by sqlglot). Inserts rows in batches via SQLAlchemy. Tracks registered names for cleanup.
- **`unregister(name)`**: drops the temp table on the real DB.
- **Context manager**: `__exit__` drops all registered temp tables and closes the connection, ensuring cleanup even on error.

### Dialect mapping

```python
SQLGLOT_DIALECTS = {
    "postgresql": "postgres",
    "snowflake": "snowflake",
    "duckdb": "duckdb",
    "sqlite": "sqlite",
    "mysql": "mysql",
    "mssql": "tsql",
    "bigquery": "bigquery",
    "redshift": "redshift",
}
```

Maps `engine.dialect.name` to sqlglot dialect names. Unknown dialects skip the bridge and use the fallback.

### Entry point

```python
def execute_ggsql(data_source, query, validated):
    if isinstance(data_source, SQLAlchemySource):
        dialect = SQLGLOT_DIALECTS.get(data_source._engine.dialect.name)
        if dialect is not None:
            try:
                with DataSourceReader(data_source._engine, dialect) as reader:
                    return ggsql.execute(query, reader)
            except Exception:
                pass  # fall through

    # Fallback: current two-phase approach
    return _execute_two_phase(data_source, validated)
```

### `_execute_two_phase`

The current `execute_ggsql` body, renamed. Includes the existing regex-based `extract_visualise_table` and `has_layer_level_source` logic. Used for `DataFrameSource`, `PolarsLazySource`, `IbisSource`, and as the fallback for SQLAlchemy sources.

## Dependencies

- `sqlglot` added to the `viz` optional extra in `pyproject.toml`
- No changes to ggsql required for the initial implementation

## Scope boundaries

- **SQLAlchemySource only** — IbisSource could follow later
- **No ggsql changes required** — the `dialect` parameter contribution to `execute()` can come later as an optimization (skipping sqlglot when ggsql natively supports the dialect)
- **No prompt changes** — the LLM already writes SQL for the correct `db_type`

## Testing

- Unit tests for `DataSourceReader`: mock SQLAlchemy connection, verify transpile + execute, register/unregister lifecycle, cleanup on error
- Unit tests for sqlglot transpilation of ggsql's generated SQL patterns (recursive CTEs, NTILE percentiles, CREATE TEMPORARY TABLE) across key dialects
- Integration test for fallback: verify bridge failure triggers two-phase approach
- End-to-end with a test database connection if available
