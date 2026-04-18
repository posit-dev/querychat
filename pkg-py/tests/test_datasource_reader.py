"""Tests for DataSourceReader bridge."""

import polars as pl
import pytest
from sqlalchemy import create_engine, text


class TestDialectMapping:
    """Tests for SQLGLOT_DIALECTS mapping."""

    def test_known_dialects_present(self):
        from querychat._datasource_reader import SQLGLOT_DIALECTS

        expected = {
            "postgresql": "postgres",
            "mysql": "mysql",
            "sqlite": "sqlite",
            "mssql": "tsql",
            "oracle": "oracle",
            "duckdb": "duckdb",
            "snowflake": "snowflake",
            "bigquery": "bigquery",
            "redshift": "redshift",
            "trino": "trino",
            "databricks": "databricks",
            "clickhousedb": "clickhouse",
            "clickhouse": "clickhouse",
            "awsathena": "athena",
            "teradatasql": "teradata",
            "exasol": "exasol",
            "doris": "doris",
            "singlestoredb": "singlestore",
            "risingwave": "risingwave",
            "druid": "druid",
            "hive": "hive",
            "presto": "presto",
        }
        for sa_name, sqlglot_name in expected.items():
            assert SQLGLOT_DIALECTS[sa_name] == sqlglot_name, f"mismatch for {sa_name}"

    def test_unknown_dialect_not_present(self):
        from querychat._datasource_reader import SQLGLOT_DIALECTS

        assert "nonexistent_db" not in SQLGLOT_DIALECTS

    def test_register_custom_dialect(self):
        from querychat._datasource_reader import (
            SQLGLOT_DIALECTS,
            register_sqlglot_dialect,
        )

        register_sqlglot_dialect("my_custom_db", "mysql")
        assert SQLGLOT_DIALECTS["my_custom_db"] == "mysql"
        # Clean up to avoid polluting other tests
        del SQLGLOT_DIALECTS["my_custom_db"]


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
            reader.register("my_temp", df, replace=True)
            result = reader.execute_sql("SELECT * FROM my_temp")
            assert len(result) == 2
            assert set(result.columns) == {"a", "b"}

    def test_unregister_drops_temp_table(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        df = pl.DataFrame({"a": [1]})
        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            reader.register("drop_me", df, replace=True)
            reader.unregister("drop_me")
            with pytest.raises(Exception, match="drop_me"):
                reader.execute_sql("SELECT * FROM drop_me")

    def test_context_manager_cleans_up_temp_tables(self, sqlite_engine):
        from querychat._datasource_reader import DataSourceReader

        df = pl.DataFrame({"a": [1]})
        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            reader.register("cleanup_test", df, replace=True)

        # After exiting context, temp table should be gone.
        # SQLite temp tables are connection-scoped, so they vanish
        # when the connection closes.
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
            reader.register("replace_me", df1, replace=True)
            reader.register("replace_me", df2, replace=True)
            result = reader.execute_sql("SELECT * FROM replace_me")
            assert len(result) == 3

    def test_execute_sql_transpiles(self, sqlite_engine):
        """Verify that generated SQL gets transpiled to the target dialect."""
        from querychat._datasource_reader import DataSourceReader

        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            df = reader.execute_sql("SELECT x, y FROM test_data ORDER BY x LIMIT 2")
            assert len(df) == 2


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

        # ggsql bar layer requires columns named x/y; "label" is a reserved keyword
        # so we alias: label -> x, SUM(y) -> y.  Two distinct label values -> 2 rows.
        with DataSourceReader(sqlite_engine, "sqlite") as reader:
            spec = ggsql.execute(
                "SELECT label AS x, SUM(y) AS y FROM test_data GROUP BY label "
                "VISUALISE x, y DRAW bar",
                reader,
            )
            assert spec.metadata()["rows"] == 2
