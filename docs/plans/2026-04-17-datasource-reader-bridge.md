# DataSourceReader Bridge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a `DataSourceReader` that lets ggsql run its full pipeline against the real database (via SQLAlchemy), using sqlglot for dialect transpilation, with fallback to the current two-phase approach on failure.

**Architecture:** `DataSourceReader` implements ggsql's reader protocol (`execute_sql`, `register`, `unregister`) by routing SQL through a held SQLAlchemy connection. sqlglot transpiles ggsql's ANSI-generated SQL to the target dialect. Temp tables are created on the real DB for ggsql's intermediate results. Falls back to the existing two-phase approach (renamed `execute_two_phase`) for non-SQLAlchemy sources or on bridge failure.

**Tech Stack:** Python, sqlglot, SQLAlchemy, ggsql (PyReaderBridge), polars, pytest

**Design doc:** `docs/plans/2026-04-17-datasource-reader-bridge-design.md`

---

### Task 1: Add sqlglot dependency

**Files:**
- Modify: `pyproject.toml:52`

**Step 1: Add sqlglot to the viz extra**

In `pyproject.toml`, change line 52 from:

```toml
viz = ["ggsql>=0.2.4", "altair>=6.0", "shinywidgets>=0.8.0", "vl-convert-python>=1.9.0"]
```

to:

```toml
viz = ["ggsql>=0.2.4", "altair>=6.0", "shinywidgets>=0.8.0", "vl-convert-python>=1.9.0", "sqlglot>=26.0"]
```

**Step 2: Install the updated dependencies**

Run: `cd /Users/cpsievert/github/querychat && uv sync --extra viz`
Expected: sqlglot installs successfully

**Step 3: Verify import**

Run: `cd /Users/cpsievert/github/querychat && uv run python -c "import sqlglot; print(sqlglot.__version__)"`
Expected: Version prints without error

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add sqlglot dependency for DataSourceReader bridge"
```

---

### Task 2: Write dialect mapping and transpile helper (tests first)

**Files:**
- Create: `pkg-py/tests/test_datasource_reader.py`
- Create (later): `pkg-py/src/querychat/_datasource_reader.py`

**Step 1: Write tests for dialect mapping and transpilation**

Create `pkg-py/tests/test_datasource_reader.py`:

```python
"""Tests for DataSourceReader bridge."""

import pytest


class TestDialectMapping:
    """Tests for SQLGLOT_DIALECTS mapping."""

    def test_known_dialects_present(self):
        from querychat._datasource_reader import SQLGLOT_DIALECTS

        assert SQLGLOT_DIALECTS["postgresql"] == "postgres"
        assert SQLGLOT_DIALECTS["snowflake"] == "snowflake"
        assert SQLGLOT_DIALECTS["duckdb"] == "duckdb"
        assert SQLGLOT_DIALECTS["sqlite"] == "sqlite"
        assert SQLGLOT_DIALECTS["mysql"] == "mysql"
        assert SQLGLOT_DIALECTS["mssql"] == "tsql"

    def test_unknown_dialect_not_present(self):
        from querychat._datasource_reader import SQLGLOT_DIALECTS

        assert "oracle" not in SQLGLOT_DIALECTS


class TestTranspileSql:
    """Tests for transpile_sql() helper."""

    def test_identity_for_duckdb(self):
        from querychat._datasource_reader import transpile_sql

        sql = "SELECT x, y FROM t WHERE x > 1"
        result = transpile_sql(sql, "duckdb")
        assert "SELECT" in result
        assert "FROM" in result

    def test_transpiles_create_temp_table_to_snowflake(self):
        from querychat._datasource_reader import transpile_sql

        sql = "CREATE TEMPORARY TABLE __ggsql_cte_0 AS SELECT x FROM t"
        result = transpile_sql(sql, "snowflake")
        assert "TEMPORARY" in result.upper() or "TEMP" in result.upper()
        assert "__ggsql_cte_0" in result

    def test_transpiles_recursive_cte_to_postgres(self):
        from querychat._datasource_reader import transpile_sql

        sql = (
            "WITH RECURSIVE series AS ("
            "SELECT 0 AS n UNION ALL SELECT n + 1 FROM series WHERE n < 10"
            ") SELECT n FROM series"
        )
        result = transpile_sql(sql, "postgres")
        assert "RECURSIVE" in result.upper()

    def test_transpiles_ntile_to_snowflake(self):
        from querychat._datasource_reader import transpile_sql

        sql = "SELECT NTILE(4) OVER (ORDER BY x) AS quartile FROM t"
        result = transpile_sql(sql, "snowflake")
        assert "NTILE" in result.upper()

    def test_passthrough_on_empty_dialect(self):
        """Empty string dialect means generic/ANSI — should pass through."""
        from querychat._datasource_reader import transpile_sql

        sql = "SELECT 1"
        result = transpile_sql(sql, "")
        assert result == "SELECT 1"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/cpsievert/github/querychat && uv run pytest pkg-py/tests/test_datasource_reader.py -v`
Expected: ImportError — `querychat._datasource_reader` does not exist

**Step 3: Implement dialect mapping and transpile helper**

Create `pkg-py/src/querychat/_datasource_reader.py`:

```python
"""DataSourceReader bridge: routes ggsql's reader protocol through a real database."""

from __future__ import annotations

import sqlglot

SQLGLOT_DIALECTS: dict[str, str] = {
    "postgresql": "postgres",
    "snowflake": "snowflake",
    "duckdb": "duckdb",
    "sqlite": "sqlite",
    "mysql": "mysql",
    "mssql": "tsql",
    "bigquery": "bigquery",
    "redshift": "redshift",
}


def transpile_sql(sql: str, dialect: str) -> str:
    """Transpile generic SQL to a target dialect using sqlglot."""
    results = sqlglot.transpile(sql, read="", write=dialect)
    return results[0]
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/cpsievert/github/querychat && uv run pytest pkg-py/tests/test_datasource_reader.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add pkg-py/tests/test_datasource_reader.py pkg-py/src/querychat/_datasource_reader.py
git commit -m "feat: add dialect mapping and transpile_sql helper"
```

---

### Task 3: Implement DataSourceReader class (tests first)

This is the core class. It implements ggsql's reader protocol by executing SQL on the real database via SQLAlchemy. Tests use a real SQLite database (in-memory) to verify end-to-end behavior.

**Files:**
- Modify: `pkg-py/tests/test_datasource_reader.py`
- Modify: `pkg-py/src/querychat/_datasource_reader.py`

**Step 1: Write tests for DataSourceReader lifecycle**

Append to `pkg-py/tests/test_datasource_reader.py`:

```python
import polars as pl
from sqlalchemy import create_engine, text


@pytest.fixture
def sqlite_engine():
    """Create an in-memory SQLite database with test data."""
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE test_data (x INTEGER, y INTEGER, label TEXT)"))
        conn.execute(
            text("INSERT INTO test_data VALUES (1, 10, 'a'), (2, 20, 'b'), (3, 30, 'a')")
        )
        conn.commit()
    return engine


class TestDataSourceReader:
    """Tests for DataSourceReader against a real SQLite database."""

    def test_execute_sql_returns_polars(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            df = reader.execute_sql("SELECT * FROM test_data")
            assert isinstance(df, pl.DataFrame)
            assert len(df) == 3
            assert set(df.columns) == {"x", "y", "label"}

    def test_execute_sql_with_filter(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            df = reader.execute_sql("SELECT * FROM test_data WHERE x > 1")
            assert len(df) == 2

    def test_register_creates_temp_table(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            reader.register("my_temp", df, True)
            result = reader.execute_sql("SELECT * FROM my_temp")
            assert len(result) == 2
            assert set(result.columns) == {"a", "b"}

    def test_unregister_drops_temp_table(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        df = pl.DataFrame({"a": [1]})
        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            reader.register("drop_me", df, True)
            reader.unregister("drop_me")
            with pytest.raises(Exception, match="drop_me"):
                reader.execute_sql("SELECT * FROM drop_me")

    def test_context_manager_cleans_up_temp_tables(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        df = pl.DataFrame({"a": [1]})
        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            reader.register("cleanup_test", df, True)

        # After exiting context, temp table should be gone.
        # SQLite temp tables are connection-scoped, so they vanish
        # when the connection closes. Verify by opening a new connection.
        with sqlite_engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_temp_master WHERE name = 'cleanup_test'")
            )
            assert result.fetchone() is None

    def test_register_replace_overwrites(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        df1 = pl.DataFrame({"a": [1, 2]})
        df2 = pl.DataFrame({"a": [10, 20, 30]})
        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            reader.register("replace_me", df1, True)
            reader.register("replace_me", df2, True)
            result = reader.execute_sql("SELECT * FROM replace_me")
            assert len(result) == 3

    def test_execute_sql_transpiles(self, sqlite_engine):
        """Verify that generated SQL gets transpiled to the target dialect."""
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            # This is valid generic SQL; sqlglot should pass it through for SQLite
            df = reader.execute_sql("SELECT x, y FROM test_data ORDER BY x LIMIT 2")
            assert len(df) == 2
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/cpsievert/github/querychat && uv run pytest pkg-py/tests/test_datasource_reader.py::TestDataSourceReader -v`
Expected: ImportError — `DataSourceReader` not found

**Step 3: Implement DataSourceReader**

Add to `pkg-py/src/querychat/_datasource_reader.py` (below the existing code):

```python
from typing import TYPE_CHECKING

import polars as pl
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


class DataSourceReader:
    """
    ggsql reader protocol implementation that routes SQL through a real database.

    Implements execute_sql(), register(), and unregister() as expected by
    ggsql's PyReaderBridge. Uses sqlglot to transpile ggsql's ANSI-generated
    SQL to the target database dialect.
    """

    def __init__(self, engine: Engine, dialect: str):
        self._engine = engine
        self._dialect = dialect
        self._conn: Connection | None = None
        self._registered: list[str] = []

    def __enter__(self):
        self._conn = self._engine.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn is not None:
            try:
                for name in self._registered:
                    try:
                        self._conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
                    except Exception:
                        pass
                self._conn.commit()
            finally:
                self._conn.close()
                self._conn = None
        self._registered.clear()
        return False

    def execute_sql(self, sql: str) -> pl.DataFrame:
        assert self._conn is not None, "DataSourceReader must be used as a context manager"
        transpiled = transpile_sql(sql, self._dialect)
        result = self._conn.execute(text(transpiled))
        rows = result.fetchall()
        columns = list(result.keys())
        if not rows:
            return pl.DataFrame(schema={col: pl.Utf8 for col in columns})
        data = {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        return pl.DataFrame(data)

    def register(self, name: str, df: pl.DataFrame, replace: bool = True) -> None:
        assert self._conn is not None, "DataSourceReader must be used as a context manager"
        if replace:
            self._conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
            if name in self._registered:
                self._registered.remove(name)

        col_defs = ", ".join(
            f"{col} {_polars_to_sql_type(dtype)}" for col, dtype in zip(df.columns, df.dtypes)
        )
        create_sql = f"CREATE TEMPORARY TABLE {name} ({col_defs})"
        transpiled_create = transpile_sql(create_sql, self._dialect)
        self._conn.execute(text(transpiled_create))
        self._registered.append(name)

        if len(df) > 0:
            placeholders = ", ".join(f":{col}" for col in df.columns)
            insert_sql = f"INSERT INTO {name} VALUES ({placeholders})"
            rows = df.to_dicts()
            self._conn.execute(text(insert_sql), rows)

        self._conn.commit()

    def unregister(self, name: str) -> None:
        assert self._conn is not None, "DataSourceReader must be used as a context manager"
        self._conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
        self._conn.commit()
        if name in self._registered:
            self._registered.remove(name)


def _polars_to_sql_type(dtype: pl.DataType) -> str:
    """Map polars dtypes to generic SQL types for CREATE TABLE."""
    if dtype.is_integer():
        return "INTEGER"
    if dtype.is_float():
        return "REAL"
    if dtype == pl.Boolean:
        return "BOOLEAN"
    if dtype == pl.Date:
        return "DATE"
    if dtype == pl.Datetime or dtype == pl.Duration:
        return "TIMESTAMP"
    return "TEXT"
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/cpsievert/github/querychat && uv run pytest pkg-py/tests/test_datasource_reader.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add pkg-py/tests/test_datasource_reader.py pkg-py/src/querychat/_datasource_reader.py
git commit -m "feat: implement DataSourceReader with temp table lifecycle"
```

---

### Task 4: Integrate with ggsql — end-to-end test with SQLite

Verify that `DataSourceReader` works with `ggsql.execute(query, reader)` against a real SQLite database.

**Files:**
- Modify: `pkg-py/tests/test_datasource_reader.py`

**Step 1: Write end-to-end test**

Append to `pkg-py/tests/test_datasource_reader.py`:

```python
@pytest.mark.ggsql
class TestDataSourceReaderWithGgsql:
    """End-to-end tests: DataSourceReader + ggsql.execute()."""

    def test_simple_scatter(self, sqlite_engine):
        import ggsql
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            spec = ggsql.execute(
                "SELECT x, y FROM test_data VISUALISE x, y DRAW point",
                reader,
            )
            assert spec.metadata()["rows"] == 3
            assert "VISUALISE" in spec.visual()

    def test_with_filter(self, sqlite_engine):
        import ggsql
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            spec = ggsql.execute(
                "SELECT x, y FROM test_data WHERE x > 1 VISUALISE x, y DRAW point",
                reader,
            )
            assert spec.metadata()["rows"] == 2

    def test_form_b_visualise_from(self, sqlite_engine):
        import ggsql
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            spec = ggsql.execute(
                "VISUALISE x, y FROM test_data DRAW point",
                reader,
            )
            assert spec.metadata()["rows"] == 3

    def test_with_aggregation(self, sqlite_engine):
        import ggsql
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            spec = ggsql.execute(
                "SELECT label, SUM(y) AS total FROM test_data GROUP BY label "
                "VISUALISE label AS x, total AS y DRAW bar",
                reader,
            )
            assert spec.metadata()["rows"] == 2
```

**Step 2: Run tests**

Run: `cd /Users/cpsievert/github/querychat && uv run pytest pkg-py/tests/test_datasource_reader.py::TestDataSourceReaderWithGgsql -v`
Expected: All pass (if the reader protocol is correctly implemented). If any fail, debug and fix.

**Step 3: Commit**

```bash
git add pkg-py/tests/test_datasource_reader.py
git commit -m "test: end-to-end DataSourceReader with ggsql.execute()"
```

---

### Task 5: Refactor execute_ggsql — rename current body, add bridge path

**Files:**
- Modify: `pkg-py/src/querychat/_viz_ggsql.py`
- Modify: `pkg-py/src/querychat/_viz_tools.py:182`
- Modify: `pkg-py/tests/test_ggsql.py`

**Step 1: Write test for bridge+fallback behavior**

Add to `pkg-py/tests/test_datasource_reader.py`:

```python
import narwhals.stable.v1 as nw


class TestExecuteGgsqlBridge:
    """Tests for the updated execute_ggsql entry point with bridge+fallback."""

    @pytest.mark.ggsql
    def test_sqlalchemy_source_uses_bridge(self, sqlite_engine):
        """SQLAlchemySource with known dialect should use the bridge path."""
        import ggsql
        from querychat._datasource import SQLAlchemySource
        from querychat._viz_ggsql import execute_ggsql

        # Create a table that SQLAlchemySource can find
        with sqlite_engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS bridge_data (x INTEGER, y INTEGER)"))
            conn.execute(text("INSERT INTO bridge_data VALUES (1, 10), (2, 20), (3, 30)"))
            conn.commit()

        ds = SQLAlchemySource(sqlite_engine, "bridge_data")
        query = "SELECT x, y FROM bridge_data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        spec = execute_ggsql(ds, query, validated)
        assert spec.metadata()["rows"] == 3

    @pytest.mark.ggsql
    def test_dataframe_source_uses_fallback(self):
        """DataFrameSource should always use the fallback path."""
        import ggsql
        from querychat._datasource import DataFrameSource
        from querychat._viz_ggsql import execute_ggsql

        nw_df = nw.from_native(pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
        ds = DataFrameSource(nw_df, "test_data")
        query = "SELECT * FROM test_data VISUALISE x, y DRAW point"
        validated = ggsql.validate(query)
        spec = execute_ggsql(ds, query, validated)
        assert spec.metadata()["rows"] == 3
```

**Step 2: Run new tests to verify they fail**

Run: `cd /Users/cpsievert/github/querychat && uv run pytest pkg-py/tests/test_datasource_reader.py::TestExecuteGgsqlBridge -v`
Expected: TypeError — `execute_ggsql()` doesn't accept 3 arguments yet

**Step 3: Update execute_ggsql signature and add bridge logic**

Modify `pkg-py/src/querychat/_viz_ggsql.py`. The full updated file:

```python
"""
Helpers for executing ggsql queries in querychat.

Architecture overview
---------------------
Querychat executes ggsql queries through two possible paths:

1. **Bridge path** (SQLAlchemySource with known dialect) — A
   ``DataSourceReader`` implements ggsql's reader protocol, routing all SQL
   through the real database. ggsql runs its full pipeline (CTEs, stat
   transforms, layer queries) against the real DB. sqlglot transpiles
   ggsql's ANSI-generated SQL to the target dialect. This path supports
   multi-source layers and avoids pulling large result sets into memory.

2. **Fallback path** (all other DataSource types, or bridge failure) — The
   SQL portion (before VISUALISE) runs on the real database via
   ``DataSource.execute_query()``, then the VISUALISE portion replays
   locally against the SQL result using ``ggsql.DuckDBReader``.

The fallback path requires reconstructing a valid ggsql query from the
split ``sql()`` and ``visual()`` parts. See ``execute_two_phase()`` for
details on the two VISUALISE forms (Form A and Form B).

Limitation of fallback path: layer-specific sources
----------------------------------------------------
ggsql supports per-layer data sources (``DRAW line MAPPING … FROM cte``),
but the fallback path can't support them because the SQL result is a single
DataFrame — CTEs don't survive the DataSource boundary. The bridge path
handles this correctly.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ._utils import to_polars

if TYPE_CHECKING:
    import ggsql

    from ._datasource import DataSource

logger = logging.getLogger(__name__)


def execute_ggsql(
    data_source: DataSource,
    query: str,
    validated: ggsql.Validated,
) -> ggsql.Spec:
    """
    Execute a ggsql query, choosing the bridge or fallback path.

    Parameters
    ----------
    data_source
        The querychat DataSource to execute against.
    query
        The original ggsql query string (needed for the bridge path).
    validated
        A pre-validated ggsql query (from ``ggsql.validate()``).

    Returns
    -------
    ggsql.Spec
        The writer-independent plot specification.

    """
    from ._datasource import SQLAlchemySource
    from ._datasource_reader import SQLGLOT_DIALECTS, DataSourceReader

    if isinstance(data_source, SQLAlchemySource):
        dialect = SQLGLOT_DIALECTS.get(data_source._engine.dialect.name)
        if dialect is not None:
            try:
                with DataSourceReader(data_source._engine, dialect) as reader:
                    import ggsql as _ggsql

                    return _ggsql.execute(query, reader)
            except Exception:
                logger.debug(
                    "DataSourceReader bridge failed, falling back to two-phase",
                    exc_info=True,
                )

    return execute_two_phase(data_source, validated)


def execute_two_phase(
    data_source: DataSource,
    validated: ggsql.Validated,
) -> ggsql.Spec:
    """
    Execute a ggsql query using the two-phase approach.

    Phase 1: execute SQL on the real database.
    Phase 2: replay the VISUALISE portion locally in DuckDB.

    This is the fallback for non-SQLAlchemy sources or when the bridge fails.
    """
    from ggsql import DuckDBReader

    visual = validated.visual()
    if has_layer_level_source(visual):
        raise ValueError(
            "Layer-specific sources are not currently supported in querychat visual "
            "queries. Rewrite the query so that all layers come from the final SQL "
            "result."
        )

    pl_df = to_polars(data_source.execute_query(validated.sql()))
    pl_df.columns = [c.lower() for c in pl_df.columns]

    reader = DuckDBReader("duckdb://memory")
    table = extract_visualise_table(visual)

    if table is not None:
        name = table[1:-1] if table.startswith('"') and table.endswith('"') else table
        reader.register(name, pl_df)
        return reader.execute(visual)
    else:
        reader.register("_data", pl_df)
        return reader.execute(f"SELECT * FROM _data {visual}")


def extract_visualise_table(visual: str) -> str | None:
    """
    Extract the table name from ``VISUALISE … FROM <table>`` if present.

    Only looks at the portion before the first DRAW clause, since FROM after
    DRAW belongs to layer-level MAPPING (a different concern).
    """
    draw_pos = re.search(r"\bDRAW\b", visual, re.IGNORECASE)
    vis_clause = visual[: draw_pos.start()] if draw_pos else visual
    m = re.search(r'\bFROM\s+("[^"]+?"|\S+)', vis_clause, re.IGNORECASE)
    return m.group(1) if m else None


def has_layer_level_source(visual: str) -> bool:
    """
    Return ``True`` when a DRAW clause defines its own ``FROM <source>``.
    """
    clauses = re.split(
        r"(?=\b(?:DRAW|SCALE|PROJECT|FACET|PLACE|LABEL|THEME)\b)",
        visual,
        flags=re.IGNORECASE,
    )
    for clause in clauses:
        if not re.match(r"^\s*DRAW\b", clause, re.IGNORECASE):
            continue
        if re.search(
            r'\bMAPPING\b[\s\S]*?\bFROM\s+("[^"]+?"|\S+)',
            clause,
            re.IGNORECASE,
        ):
            return True
    return False
```

**Step 4: Update the caller in `_viz_tools.py`**

In `pkg-py/src/querychat/_viz_tools.py`, change line 182 from:

```python
            spec = execute_ggsql(data_source, validated)
```

to:

```python
            spec = execute_ggsql(data_source, ggsql, validated)
```

Note: `ggsql` here is the local parameter name (the query string) from line 151, not the module. The module import at the top of the function (`from ggsql import VegaLiteWriter, validate`) is a different scope.

**Wait** — there's a name collision. The parameter is `ggsql: str` (line 151) and the module import is `from ggsql import ...` (line 148). The parameter shadows the module name within `visualize_query`. But `execute_ggsql` is imported at the module level, not from the `ggsql` package, so the call `execute_ggsql(data_source, ggsql, validated)` correctly passes the string parameter. This works.

**Step 5: Update existing tests in `test_ggsql.py`**

The existing `TestExecuteGgsql` tests call `execute_ggsql(ds, ggsql.validate(query))` with 2 args. Update them to pass 3 args. In `pkg-py/tests/test_ggsql.py`, update each call in `TestExecuteGgsql`:

Change every occurrence of:
```python
        spec = execute_ggsql(ds, ggsql.validate(query))
```
to:
```python
        spec = execute_ggsql(ds, query, ggsql.validate(query))
```

Also update the layer-level source test (line 188):
```python
            execute_ggsql(ds, ggsql.validate(query))
```
to:
```python
            execute_ggsql(ds, query, ggsql.validate(query))
```

**Step 6: Run all tests**

Run: `cd /Users/cpsievert/github/querychat && uv run pytest pkg-py/tests/test_datasource_reader.py pkg-py/tests/test_ggsql.py -v`
Expected: All pass

**Step 7: Run type checker and linter**

Run: `cd /Users/cpsievert/github/querychat && uv run ruff check --fix pkg-py --config pyproject.toml && make py-check-types`
Expected: No errors (fix any that arise)

**Step 8: Commit**

```bash
git add pkg-py/src/querychat/_viz_ggsql.py pkg-py/src/querychat/_viz_tools.py pkg-py/tests/test_ggsql.py pkg-py/tests/test_datasource_reader.py
git commit -m "feat: integrate DataSourceReader bridge into execute_ggsql"
```

---

### Task 6: Run full test suite and fix any issues

**Files:**
- Potentially any file touched above

**Step 1: Run full Python checks**

Run: `cd /Users/cpsievert/github/querychat && uv run ruff check --fix pkg-py --config pyproject.toml`
Expected: Clean

**Step 2: Run type checker**

Run: `cd /Users/cpsievert/github/querychat && make py-check-types`
Expected: Clean

**Step 3: Run full test suite**

Run: `cd /Users/cpsievert/github/querychat && make py-check-tests`
Expected: All pass

**Step 4: Fix any failures**

If any tests fail, debug and fix. Common issues:
- sqlglot transpilation producing unexpected SQL for a specific dialect
- Empty DataFrame handling in `execute_sql` (no rows returned)
- Polars dtype mapping edge cases in `_polars_to_sql_type`

**Step 5: Commit any fixes**

```bash
git add -u
git commit -m "fix: address issues from full test suite run"
```

---

### Task 7: Update module docstring and clean up

**Files:**
- Modify: `pkg-py/src/querychat/_datasource_reader.py`

**Step 1: Ensure the module docstring is accurate**

The docstring added in Task 3 should already be correct. Verify `_datasource_reader.py` has a clear module-level docstring explaining the bridge's purpose.

**Step 2: Verify no dead code remains**

Check that the old `execute_ggsql` docstring in `_viz_ggsql.py` has been updated to reflect the new 3-arg signature and bridge behavior (done in Task 5).

**Step 3: Final commit if any cleanup was needed**

```bash
git add -u
git commit -m "docs: clean up DataSourceReader module docstrings"
```
