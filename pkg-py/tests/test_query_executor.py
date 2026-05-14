from __future__ import annotations

import tempfile
from pathlib import Path

import narwhals.stable.v1 as nw
import pandas as pd
import polars as pl
import pytest
from querychat._datasource import (
    DataFrameSource,
    IbisSource,
    MissingColumnsError,
    PolarsLazySource,
    SQLAlchemySource,
)
from querychat._query_executor import (
    DataSourceExecutor,
    DuckDBExecutor,
    PolarsSQLExecutor,
)
from sqlalchemy import create_engine, text


@pytest.fixture
def orders_source():
    df = pd.DataFrame({
        "order_id": [1, 2, 3],
        "customer_id": [10, 20, 10],
        "amount": [100.0, 200.0, 150.0],
    })
    return DataFrameSource(nw.from_native(df), "orders")


@pytest.fixture
def customers_source():
    df = pd.DataFrame({
        "id": [10, 20, 30],
        "name": ["Alice", "Bob", "Charlie"],
    })
    return DataFrameSource(nw.from_native(df), "customers")


@pytest.fixture
def sqlite_sources():
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
    temp_db.close()
    engine = create_engine(f"sqlite:///{temp_db.name}")

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE orders (
                order_id INTEGER,
                customer_id INTEGER,
                amount REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE customers (
                id INTEGER,
                name TEXT
            )
        """))
        conn.execute(
            text("""
                INSERT INTO orders (order_id, customer_id, amount)
                VALUES
                    (1, 10, 100.0),
                    (2, 20, 200.0),
                    (3, 10, 150.0)
            """)
        )
        conn.execute(
            text("""
                INSERT INTO customers (id, name)
                VALUES
                    (10, 'Alice'),
                    (20, 'Bob'),
                    (30, 'Charlie')
            """)
        )

    yield {
        "orders": SQLAlchemySource(engine, "orders"),
        "customers": SQLAlchemySource(engine, "customers"),
    }

    engine.dispose()
    Path(temp_db.name).unlink()


@pytest.fixture
def ibis_sources():
    ibis = pytest.importorskip("ibis")
    conn = ibis.duckdb.connect()
    conn.create_table(
        "orders",
        {
            "order_id": [1, 2, 3],
            "customer_id": [10, 20, 10],
            "amount": [100.0, 200.0, 150.0],
        },
    )
    conn.create_table(
        "customers",
        {
            "id": [10, 20, 30],
            "name": ["Alice", "Bob", "Charlie"],
        },
    )

    yield {
        "orders": IbisSource(conn.table("orders"), "orders"),
        "customers": IbisSource(conn.table("customers"), "customers"),
    }

    conn.disconnect()


@pytest.fixture
def orders_polars_dataframe_source():
    df = pl.DataFrame({
        "order_id": [1, 2, 3],
        "customer_id": [10, 20, 10],
        "amount": [100.0, 200.0, 150.0],
    })
    return DataFrameSource(nw.from_native(df), "orders_polars")


class TestDuckDBExecutor:
    def test_cross_table_join(self, orders_source, customers_source):
        executor = DuckDBExecutor({
            "orders": orders_source,
            "customers": customers_source,
        })
        result = executor.execute_query(
            "SELECT o.order_id, c.name "
            "FROM orders o JOIN customers c ON o.customer_id = c.id"
        )
        nw_df = nw.from_native(result, eager_only=True)
        assert set(nw_df.columns) == {"order_id", "name"}
        assert nw_df.shape[0] == 3
        executor.cleanup()

    def test_single_table_query(self, orders_source, customers_source):
        executor = DuckDBExecutor({
            "orders": orders_source,
            "customers": customers_source,
        })
        result = executor.execute_query("SELECT * FROM orders WHERE amount > 100")
        nw_df = nw.from_native(result, eager_only=True)
        assert nw_df.shape[0] == 2
        executor.cleanup()

    def test_returns_native_type(self, orders_source):
        executor = DuckDBExecutor({"orders": orders_source})
        result = executor.execute_query("SELECT * FROM orders")
        assert isinstance(result, pd.DataFrame)
        executor.cleanup()

    def test_get_db_type(self, orders_source):
        executor = DuckDBExecutor({"orders": orders_source})
        assert executor.get_db_type() == "DuckDB"
        executor.cleanup()

    def test_test_query_passes(self, orders_source):
        executor = DuckDBExecutor({"orders": orders_source})
        executor.test_query(
            "SELECT * FROM orders",
            table_name="orders",
            require_all_columns=True,
        )
        executor.cleanup()

    def test_test_query_missing_columns(self, orders_source):
        executor = DuckDBExecutor({"orders": orders_source})
        with pytest.raises(MissingColumnsError, match="missing required columns"):
            executor.test_query(
                "SELECT order_id FROM orders",
                table_name="orders",
                require_all_columns=True,
            )
        executor.cleanup()

    def test_test_query_cross_table_join(self, orders_source, customers_source):
        executor = DuckDBExecutor({
            "orders": orders_source,
            "customers": customers_source,
        })
        executor.test_query(
            "SELECT o.* FROM orders o "
            "JOIN customers c ON o.customer_id = c.id "
            "WHERE c.name = 'Alice'",
            table_name="orders",
            require_all_columns=True,
        )
        executor.cleanup()

    def test_unsafe_query_rejected(self, orders_source):
        executor = DuckDBExecutor({"orders": orders_source})
        with pytest.raises(Exception, match=r"(?i)disallowed|unsafe|not allowed"):
            executor.execute_query("DROP TABLE orders")
        executor.cleanup()

    def test_cleanup_closes_connection(self, orders_source):
        import duckdb

        executor = DuckDBExecutor({"orders": orders_source})
        executor.cleanup()
        with pytest.raises(duckdb.ConnectionException):
            executor.execute_query("SELECT 1")

    def test_rejects_mixed_dataframe_backends(
        self, orders_source, orders_polars_dataframe_source
    ):
        with pytest.raises(ValueError, match="same DataFrame backend"):
            DuckDBExecutor({
                "orders": orders_source,
                "orders_polars": orders_polars_dataframe_source,
            })

    def test_rejects_mixed_dataframe_backends_before_opening_connection(
        self, monkeypatch, orders_source, orders_polars_dataframe_source
    ):
        def fail_if_connect_called(*args, **kwargs):
            raise AssertionError("duckdb.connect should not be called")

        monkeypatch.setattr("querychat._query_executor.duckdb.connect", fail_if_connect_called)

        with pytest.raises(ValueError, match="same DataFrame backend"):
            DuckDBExecutor({
                "orders": orders_source,
                "orders_polars": orders_polars_dataframe_source,
            })


@pytest.fixture
def orders_polars_source():
    lf = pl.LazyFrame({
        "order_id": [1, 2, 3],
        "customer_id": [10, 20, 10],
        "amount": [100.0, 200.0, 150.0],
    })
    return PolarsLazySource(nw.from_native(lf), "orders")


@pytest.fixture
def customers_polars_source():
    lf = pl.LazyFrame({
        "id": [10, 20, 30],
        "name": ["Alice", "Bob", "Charlie"],
    })
    return PolarsLazySource(nw.from_native(lf), "customers")


class TestPolarsSQLExecutor:
    def test_cross_table_join(self, orders_polars_source, customers_polars_source):
        executor = PolarsSQLExecutor({
            "orders": orders_polars_source,
            "customers": customers_polars_source,
        })
        result = executor.execute_query(
            "SELECT o.order_id, c.name "
            "FROM orders o JOIN customers c ON o.customer_id = c.id"
        )
        assert isinstance(result, pl.LazyFrame)
        collected = result.collect()
        assert set(collected.columns) == {"order_id", "name"}
        assert collected.shape[0] == 3

    def test_get_db_type(self, orders_polars_source):
        executor = PolarsSQLExecutor({"orders": orders_polars_source})
        assert executor.get_db_type() == "Polars"

    def test_test_query_missing_columns(self, orders_polars_source):
        executor = PolarsSQLExecutor({"orders": orders_polars_source})
        with pytest.raises(MissingColumnsError, match="missing required columns"):
            executor.test_query(
                "SELECT order_id FROM orders",
                table_name="orders",
                require_all_columns=True,
            )

    def test_cleanup_noop(self, orders_polars_source):
        executor = PolarsSQLExecutor({"orders": orders_polars_source})
        executor.cleanup()


class TestDataSourceExecutor:
    def test_single_table_execute(self, orders_source):
        executor = DataSourceExecutor({"orders": orders_source})
        result = executor.execute_query("SELECT * FROM orders")
        nw_df = nw.from_native(result, eager_only=True)
        assert nw_df.shape[0] == 3

    def test_get_db_type(self, orders_source):
        executor = DataSourceExecutor({"orders": orders_source})
        assert executor.get_db_type() == "DuckDB"

    def test_test_query_routes_by_table(self, orders_source, customers_source):
        executor = DataSourceExecutor({
            "orders": orders_source,
            "customers": customers_source,
        })
        # test_query against orders — should check orders columns
        with pytest.raises(MissingColumnsError, match="missing required columns"):
            executor.test_query(
                "SELECT order_id FROM orders",
                table_name="orders",
                require_all_columns=True,
            )

    def test_shared_sqlalchemy_sources_support_cross_table_query(self, sqlite_sources):
        executor = DataSourceExecutor(sqlite_sources)
        result = executor.execute_query(
            "SELECT o.order_id, c.name "
            "FROM orders o JOIN customers c ON o.customer_id = c.id"
        )
        nw_df = nw.from_native(result, eager_only=True)
        assert set(nw_df.columns) == {"order_id", "name"}
        assert nw_df.shape[0] == 3

    def test_rejects_sqlalchemy_sources_with_different_engines(self):
        orders_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
        customers_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
        orders_db.close()
        customers_db.close()

        orders_engine = create_engine(f"sqlite:///{orders_db.name}")
        customers_engine = create_engine(f"sqlite:///{customers_db.name}")

        try:
            with orders_engine.begin() as conn:
                conn.execute(
                    text("""
                        CREATE TABLE orders (
                            order_id INTEGER,
                            customer_id INTEGER
                        )
                    """)
                )
            with customers_engine.begin() as conn:
                conn.execute(
                    text("""
                        CREATE TABLE customers (
                            id INTEGER,
                            name TEXT
                        )
                    """)
                )

            with pytest.raises(ValueError, match="share the same Engine instance"):
                DataSourceExecutor({
                    "orders": SQLAlchemySource(orders_engine, "orders"),
                    "customers": SQLAlchemySource(customers_engine, "customers"),
                })
        finally:
            orders_engine.dispose()
            customers_engine.dispose()
            Path(orders_db.name).unlink()
            Path(customers_db.name).unlink()

    def test_shared_ibis_sources_support_cross_table_query(self, ibis_sources):
        executor = DataSourceExecutor(ibis_sources)
        result = executor.execute_query(
            "SELECT o.order_id, c.name "
            "FROM orders o JOIN customers c ON o.customer_id = c.id"
        )
        collected = result.execute()
        assert set(collected.columns) == {"order_id", "name"}
        assert collected.shape[0] == 3

    def test_rejects_ibis_sources_with_different_backends(self):
        ibis = pytest.importorskip("ibis")
        orders_conn = ibis.duckdb.connect()
        customers_conn = ibis.duckdb.connect()

        try:
            orders_conn.create_table("orders", {"order_id": [1], "customer_id": [10]})
            customers_conn.create_table("customers", {"id": [10], "name": ["Alice"]})

            with pytest.raises(ValueError, match="share the same backend instance"):
                DataSourceExecutor({
                    "orders": IbisSource(orders_conn.table("orders"), "orders"),
                    "customers": IbisSource(customers_conn.table("customers"), "customers"),
                })
        finally:
            orders_conn.disconnect()
            customers_conn.disconnect()

    def test_cleanup_noop(self, orders_source):
        executor = DataSourceExecutor({"orders": orders_source})
        executor.cleanup()
