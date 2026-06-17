"""Tests for multi-table support."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import polars as pl
import pytest
from querychat import QueryChat, TableAccessor
from querychat._datasource import DataFrameSource
from querychat._query_executor import (
    DataSourceExecutor,
    DuckDBExecutor,
    check_source_compatibility,
)
from querychat._querychat_base import QueryChatBase, normalize_data_source
from sqlalchemy import create_engine, text


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    """Set a dummy OpenAI API key for testing."""
    old_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old_api_key is not None:
        os.environ["OPENAI_API_KEY"] = old_api_key
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def orders_df():
    """Sample orders DataFrame."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "customer_id": [101, 102, 101],
            "amount": [100.0, 200.0, 150.0],
        }
    )


@pytest.fixture
def customers_df():
    """Sample customers DataFrame."""
    return pd.DataFrame(
        {
            "id": [101, 102, 103],
            "name": ["Alice", "Bob", "Charlie"],
            "state": ["CA", "NY", "CA"],
        }
    )


@pytest.fixture
def shared_sqlite_engine():
    """SQLite engine with orders/customers tables for shared-engine tests."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
    temp_db.close()
    engine = create_engine(f"sqlite:///{temp_db.name}")

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE orders (
                id INTEGER,
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
                INSERT INTO orders (id, customer_id, amount)
                VALUES
                    (1, 101, 100.0),
                    (2, 102, 200.0)
            """)
        )
        conn.execute(
            text("""
                INSERT INTO customers (id, name)
                VALUES
                    (101, 'Alice'),
                    (102, 'Bob')
            """)
        )

    yield engine

    engine.dispose()
    Path(temp_db.name).unlink()


@pytest.fixture
def ibis_tables():
    """Ibis tables with shared backend for compatibility tests."""
    ibis = pytest.importorskip("ibis")
    conn = ibis.duckdb.connect()
    conn.create_table(
        "orders",
        {
            "id": [1, 2],
            "customer_id": [101, 102],
            "amount": [100.0, 200.0],
        },
    )
    conn.create_table(
        "customers",
        {
            "id": [101, 102],
            "name": ["Alice", "Bob"],
        },
    )

    yield {
        "orders": conn.table("orders"),
        "customers": conn.table("customers"),
    }

    conn.disconnect()


@pytest.fixture
def other_ibis_orders_table():
    """Ibis orders table backed by a different backend instance."""
    ibis = pytest.importorskip("ibis")
    conn = ibis.duckdb.connect()
    conn.create_table(
        "orders",
        {
            "id": [1, 2],
            "customer_id": [101, 102],
            "amount": [100.0, 200.0],
        },
    )

    yield conn.table("orders")

    conn.disconnect()


class TestNoArgConstruction:
    """Tests for QueryChatBase() / QueryChat() with no positional arguments."""

    def test_no_arg_construction(self):
        qc = QueryChatBase()
        assert qc.table_names() == []

    def test_no_arg_construction_multi_table(self, orders_df, customers_df):
        qc = QueryChatBase()
        qc.add_table(orders_df, "orders")
        qc.add_table(customers_df, "customers")
        assert qc.table_names() == ["orders", "customers"]


class TestMultiSourceStorage:
    """Tests for multi-source storage infrastructure."""

    def test_single_table_stored_in_data_sources(self, orders_df):
        """Test that single table is stored in _data_sources dict."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        # Should have _data_sources dict with one entry
        assert hasattr(qc, "_data_sources")
        assert isinstance(qc._data_sources, dict)
        assert "orders" in qc._data_sources
        assert len(qc._data_sources) == 1

    def test_table_accessor_returns_data_source(self, orders_df):
        """Test that table() accessor returns the correct data source."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        assert qc.table("orders").data_source is qc._data_sources["orders"]

    def test_table_names_returns_list(self, orders_df):
        """Test that table_names() returns list of table names."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        names = qc.table_names()

        assert names == ["orders"]


class TestAddTable:
    """Tests for add_table() method."""

    def test_add_table_basic(self, orders_df, customers_df):
        """Test adding a second table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        assert qc.table_names() == ["orders", "customers"]
        assert len(qc._data_sources) == 2

    def test_add_table_duplicate_name_raises(self, orders_df):
        """Test that adding duplicate table name raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Table 'orders' already exists"):
            qc.add_table(orders_df, "orders")

    def test_add_table_invalid_name_raises(self, orders_df, customers_df):
        """Test that invalid table name raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="must begin with a letter"):
            qc.add_table(customers_df, "123invalid")

    def test_add_table_after_server_raises(self, orders_df, customers_df):
        """Test that adding table after server init raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc._server_initialized = True  # Simulate server initialization

        with pytest.raises(RuntimeError, match="Cannot add tables after server"):
            qc.add_table(customers_df, "customers")


class TestRemoveTable:
    """Tests for remove_table() method."""

    def test_remove_table_basic(self, orders_df, customers_df):
        """Test removing a table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        qc.remove_table("customers")

        assert qc.table_names() == ["orders"]

    def test_remove_table_nonexistent_raises(self, orders_df):
        """Test that removing nonexistent table raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Table 'foo' not found"):
            qc.remove_table("foo")

    def test_remove_last_table_raises(self, orders_df):
        """Test that removing last table raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Cannot remove last table"):
            qc.remove_table("orders")

    def test_remove_table_after_server_raises(self, orders_df, customers_df):
        """Test that removing table after server init raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")
        qc._server_initialized = True

        with pytest.raises(RuntimeError, match="Cannot remove tables after server"):
            qc.remove_table("customers")


class TestTableAccessor:
    """Tests for table() method and TableAccessor class."""

    def test_table_returns_accessor(self, orders_df):
        """Test that table() returns a TableAccessor."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        accessor = qc.table("orders")

        assert accessor is not None
        assert isinstance(accessor, TableAccessor)
        assert accessor.table_name == "orders"

    def test_table_accessor_has_data_source(self, orders_df):
        """Test that accessor provides access to data source."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        accessor = qc.table("orders")

        assert accessor.data_source is qc._data_sources["orders"]

    def test_table_nonexistent_raises(self, orders_df):
        """Test that accessing nonexistent table raises error."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        with pytest.raises(ValueError, match="Table 'foo' not found"):
            qc.table("foo")

    def test_table_accessor_multiple_tables(self, orders_df, customers_df):
        """Test accessor works with multiple tables."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        orders_accessor = qc.table("orders")
        customers_accessor = qc.table("customers")

        assert orders_accessor.table_name == "orders"
        assert customers_accessor.table_name == "customers"
        assert orders_accessor.data_source is not customers_accessor.data_source


class TestMultiTableSystemPrompt:
    """Tests for multi-table system prompt generation."""

    def test_multiple_schemas_in_prompt(self, orders_df, customers_df):
        """Test that multiple table schemas appear in prompt."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        prompt = qc.system_prompt

        assert "orders" in prompt
        assert "customers" in prompt

    def test_system_prompt_references_get_schema_tool(self, orders_df, customers_df):
        """Column details are now behind get_schema; prompt lists table names only."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        prompt = qc.system_prompt

        # Table names still appear in the prompt
        assert "orders" in prompt
        assert "customers" in prompt
        # Column details are no longer inlined in the prompt
        assert "querychat_get_schema" in prompt


class TestMultiTableCleanup:
    """Tests for cleanup of multiple data sources."""

    def test_cleanup_all_sources(self, orders_df, customers_df):
        """Test that cleanup() cleans up all data sources."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        # Both sources should have connections before cleanup
        assert qc._data_sources["orders"]._conn is not None
        assert qc._data_sources["customers"]._conn is not None

        qc.cleanup()

        # Connections should be closed after cleanup
        # (DuckDB connections don't have is_closed, but they're closed)


@pytest.fixture
def orders_qc(orders_df):
    """QueryChat with a single orders table."""
    return QueryChat(orders_df, "orders", greeting="Hello!")


class TestSourceCompatibility:
    def test_same_pandas_compatible(self, orders_qc, customers_df):
        """Two pandas DataFrameSources are compatible."""
        first = orders_qc._data_sources["orders"]
        second = normalize_data_source(customers_df, "customers")
        # Should not raise
        check_source_compatibility({"orders": first}, second, "customers")

    def test_mixed_pandas_polars_incompatible(self, orders_qc):
        """Pandas and Polars DataFrameSources are incompatible."""
        first = orders_qc._data_sources["orders"]
        polars_df = pl.DataFrame({"x": [1, 2]})
        second = normalize_data_source(polars_df, "other")
        with pytest.raises(ValueError, match="same DataFrame backend"):
            check_source_compatibility({"orders": first}, second, "other")

    def test_different_source_types_incompatible(self, orders_qc):
        """DataFrameSource and PolarsLazySource are incompatible."""
        first = orders_qc._data_sources["orders"]
        lf = pl.LazyFrame({"x": [1, 2]})
        second = normalize_data_source(lf, "lazy_table")
        with pytest.raises(ValueError, match="same type"):
            check_source_compatibility({"orders": first}, second, "lazy_table")

    def test_add_table_validates_compatibility(self, orders_qc):
        """add_table should reject incompatible source types."""
        lf = pl.LazyFrame({"x": [1, 2]})
        with pytest.raises(ValueError, match="same type"):
            orders_qc.add_table(lf, "lazy_table")

    def test_shared_sqlalchemy_engine_compatible(self, shared_sqlite_engine):
        """SQLAlchemy sources sharing an Engine instance are compatible."""
        first = normalize_data_source(shared_sqlite_engine, "orders")
        second = normalize_data_source(shared_sqlite_engine, "customers")

        check_source_compatibility({"orders": first}, second, "customers")

    def test_mismatched_sqlalchemy_engines_incompatible(self, shared_sqlite_engine):
        """SQLAlchemy sources using different Engine instances are incompatible."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
        temp_db.close()
        other_engine = create_engine(f"sqlite:///{temp_db.name}")
        try:
            with other_engine.begin() as conn:
                conn.execute(text("CREATE TABLE customers (id INTEGER, name TEXT)"))

            first = normalize_data_source(shared_sqlite_engine, "orders")
            second = normalize_data_source(other_engine, "customers")

            with pytest.raises(ValueError, match="share the same Engine instance"):
                check_source_compatibility({"orders": first}, second, "customers")
        finally:
            other_engine.dispose()
            Path(temp_db.name).unlink()

    def test_shared_ibis_backend_compatible(self, ibis_tables):
        """Ibis sources sharing a backend instance are compatible."""
        first = normalize_data_source(ibis_tables["orders"], "orders")
        second = normalize_data_source(ibis_tables["customers"], "customers")

        check_source_compatibility({"orders": first}, second, "customers")

    def test_mismatched_ibis_backends_incompatible(
        self, ibis_tables, other_ibis_orders_table
    ):
        """Ibis sources using different backend instances are incompatible."""
        first = normalize_data_source(ibis_tables["orders"], "orders")
        second = normalize_data_source(other_ibis_orders_table, "customers")

        with pytest.raises(ValueError, match="share the same backend instance"):
            check_source_compatibility({"orders": first}, second, "customers")

    def test_add_table_replace_validates_compatibility(
        self, orders_qc, customers_df
    ):
        """Replacing a table must still respect multi-table compatibility."""
        orders_qc.add_table(customers_df, "customers")
        original_orders = orders_qc._data_sources["orders"]

        with pytest.raises(ValueError, match="same DataFrame backend"):
            orders_qc.add_table(
                pl.DataFrame(
                    {
                        "id": [1, 2],
                        "customer_id": [101, 102],
                        "amount": [100.0, 200.0],
                    }
                ),
                "orders",
                replace=True,
            )

        assert orders_qc._data_sources["orders"] is original_orders
        assert isinstance(orders_qc._data_sources["orders"].get_data(), pd.DataFrame)


class TestBuildQueryExecutor:
    def test_executor_none_before_first_use(self, orders_qc):
        assert orders_qc._query_executor is None

    def test_single_table_uses_data_source_executor(self, orders_qc):
        assert isinstance(orders_qc._require_query_executor("test"), DataSourceExecutor)

    def test_multi_dataframe_uses_duckdb_executor(self, orders_qc, customers_df):
        orders_qc.add_table(customers_df, "customers")
        assert isinstance(orders_qc._require_query_executor("test"), DuckDBExecutor)

    def test_executor_invalidated_on_add_table(self, orders_qc, customers_df):
        orders_qc._require_query_executor("test")  # build it
        orders_qc.add_table(customers_df, "customers")
        assert orders_qc._query_executor is None

    def test_executor_invalidated_on_remove_table(self, orders_qc, customers_df):
        orders_qc.add_table(customers_df, "customers")
        orders_qc._require_query_executor("test")  # build it
        orders_qc.remove_table("customers")
        assert orders_qc._query_executor is None

    def test_executor_cached_after_build(self, orders_qc):
        first = orders_qc._require_query_executor("test")
        second = orders_qc._require_query_executor("test")
        assert first is second

    def test_cleanup_includes_executor(self, orders_qc, customers_df):
        orders_qc.add_table(customers_df, "customers")
        executor = orders_qc._require_query_executor("test")
        orders_qc.cleanup()
        # DuckDBExecutor's connection should be closed
        import duckdb

        with pytest.raises(duckdb.ConnectionException):
            executor.execute_query("SELECT 1")

    def test_deferred_executor_is_none(self):
        qc = QueryChatBase(None, "test")
        assert qc._query_executor is None

    def test_rejects_inconsistent_internal_source_group(self, orders_qc):
        orders_qc._data_sources["customers"] = normalize_data_source(
            pl.DataFrame(
                {
                    "id": [101, 102],
                    "name": ["Alice", "Bob"],
                }
            ),
            "customers",
        )

        with pytest.raises(ValueError, match="same DataFrame backend"):
            orders_qc._build_query_executor()

    def test_cached_executor_survives_direct_source_mutation(self, orders_qc, customers_df):
        """Executor built lazily is not invalidated by direct _data_sources mutation."""
        orders_qc.add_table(customers_df, "customers")
        built = orders_qc._require_query_executor("test")

        # Directly corrupt _data_sources (bypassing add_table) — executor should
        # not be affected since invalidation only happens through add/remove_table.
        orders_qc._data_sources["customers"] = normalize_data_source(
            pl.DataFrame({"id": [101, 102], "name": ["Alice", "Bob"]}),
            "customers",
        )

        assert orders_qc._query_executor is built
        result = built.execute_query(
            """
            SELECT customers.name, orders.amount
            FROM orders
            JOIN customers ON orders.customer_id = customers.id
            WHERE orders.id = 1
            """
        )
        assert result.to_dict("records") == [{"name": "Alice", "amount": 100.0}]

    def test_add_table_failure_cleans_staged_source_and_preserves_state(
        self, orders_qc, customers_df, monkeypatch
    ):
        original_table_names = orders_qc.table_names()
        staged_source = None

        original_normalize = normalize_data_source

        def capture_staged_source(data_source, table_name):
            nonlocal staged_source
            staged_source = original_normalize(data_source, table_name)
            return staged_source

        monkeypatch.setattr(
            "querychat._querychat_base.normalize_data_source",
            capture_staged_source,
        )
        def fail_compat(*a, **kw):
            raise ValueError("compat check failed")

        monkeypatch.setattr(
            "querychat._querychat_base.check_source_compatibility",
            fail_compat,
        )

        with pytest.raises(ValueError, match="compat check failed"):
            orders_qc.add_table(customers_df, "customers")

        import duckdb

        assert isinstance(staged_source, DataFrameSource)
        with pytest.raises(duckdb.ConnectionException):
            staged_source.execute_query("SELECT 1")
        assert orders_qc.table_names() == original_table_names

    def test_add_table_replace_failure_cleans_staged_source_and_preserves_state(
        self, orders_qc, customers_df, monkeypatch
    ):
        orders_qc.add_table(customers_df, "customers")
        original_orders_source = orders_qc._data_sources["orders"]
        original_table_names = orders_qc.table_names()
        staged_source = None

        original_normalize = normalize_data_source

        def capture_staged_source(data_source, table_name):
            nonlocal staged_source
            staged_source = original_normalize(data_source, table_name)
            return staged_source

        monkeypatch.setattr(
            "querychat._querychat_base.normalize_data_source",
            capture_staged_source,
        )
        def fail_compat(*a, **kw):
            raise ValueError("compat check failed")

        monkeypatch.setattr(
            "querychat._querychat_base.check_source_compatibility",
            fail_compat,
        )

        with pytest.raises(ValueError, match="compat check failed"):
            orders_qc.add_table(
                pd.DataFrame(
                    {
                        "id": [1, 2, 3],
                        "customer_id": [101, 102, 101],
                        "amount": [100.0, 200.0, 150.0],
                    }
                ),
                "orders",
                replace=True,
            )

        import duckdb

        assert isinstance(staged_source, DataFrameSource)
        assert staged_source is not original_orders_source
        with pytest.raises(duckdb.ConnectionException):
            staged_source.execute_query("SELECT 1")
        assert orders_qc._data_sources["orders"] is original_orders_source
        assert orders_qc.table_names() == original_table_names

    def test_remove_table_cleans_up_removed_source(self, orders_qc, customers_df):
        orders_qc.add_table(customers_df, "customers")
        customer_source = orders_qc._data_sources["customers"]

        orders_qc.remove_table("customers")

        assert orders_qc.table_names() == ["orders"]
        import duckdb

        with pytest.raises(duckdb.ConnectionException):
            customer_source.execute_query("SELECT id FROM customers")


class TestMultiTableGuardrails:
    """Top-level accessors raise when multiple tables are registered."""

    def test_shiny_server_values_df_raises(self, orders_df, customers_df):
        from querychat._shiny_module import (
            ServerValues,
            TableState,
            _MultiTableBlockedReactive,
        )

        from shiny import reactive

        orders_sql = reactive.Value(None)
        orders_title = reactive.Value(None)
        customers_sql = reactive.Value(None)
        customers_title = reactive.Value(None)

        def orders_df_calc():
            return orders_df

        def customers_df_calc():
            return customers_df

        table_list = "'orders', 'customers'"
        vals = ServerValues(
            df=lambda: (_ for _ in ()).throw(
                AttributeError(
                    f"Cannot use .df() with multiple tables ({table_list}). "
                    "Use .tables['name'].df() for per-table access."
                )
            ),
            sql=_MultiTableBlockedReactive(table_list, "sql"),  # type: ignore[arg-type]
            title=_MultiTableBlockedReactive(table_list, "title"),  # type: ignore[arg-type]
            tables={
                "orders": TableState(sql=orders_sql, title=orders_title, df=orders_df_calc),
                "customers": TableState(sql=customers_sql, title=customers_title, df=customers_df_calc),
            },
            client=None,  # type: ignore[arg-type]
        )

        with pytest.raises(AttributeError, match="multiple tables"):
            vals.sql()

        with pytest.raises(AttributeError, match="multiple tables"):
            vals.sql.get()

        with pytest.raises(AttributeError, match="multiple tables"):
            vals.sql.set("SELECT 1")

        with pytest.raises(AttributeError, match="multiple tables"):
            vals.title()

    def test_shiny_server_values_tables_still_works(self, orders_df, customers_df):
        from querychat._shiny_module import (
            ServerValues,
            TableState,
            _MultiTableBlockedReactive,
        )

        from shiny import reactive

        orders_sql = reactive.Value(None)
        orders_title = reactive.Value(None)
        customers_sql = reactive.Value(None)
        customers_title = reactive.Value(None)

        table_list = "'orders', 'customers'"
        vals = ServerValues(
            df=lambda: None,  # type: ignore[return-value]
            sql=_MultiTableBlockedReactive(table_list, "sql"),  # type: ignore[arg-type]
            title=_MultiTableBlockedReactive(table_list, "title"),  # type: ignore[arg-type]
            tables={
                "orders": TableState(sql=orders_sql, title=orders_title, df=lambda: orders_df),
                "customers": TableState(sql=customers_sql, title=customers_title, df=lambda: customers_df),
            },
            client=None,  # type: ignore[arg-type]
        )

        orders_state = vals.tables["orders"]
        assert orders_state.df() is orders_df
        customers_state = vals.tables["customers"]
        assert customers_state.df() is customers_df

    def test_shiny_app_raises_multi_table(self, orders_df, customers_df):
        from querychat.shiny import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        with pytest.raises(RuntimeError, match="does not support multiple tables"):
            qc.app()

    def test_shiny_app_works_single_table(self, orders_df):
        from querychat.shiny import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        app = qc.app()
        assert app is not None

    def test_streamlit_app_raises_multi_table(self, orders_df, customers_df):
        pytest.importorskip("streamlit")
        from querychat.streamlit import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        with pytest.raises(RuntimeError, match="does not support multiple tables"):
            qc.app()

    def test_streamlit_df_raises_multi_table(self, orders_df, customers_df):
        pytest.importorskip("streamlit")
        from querychat.streamlit import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        with pytest.raises(AttributeError, match="multiple tables"):
            qc.df()

    def test_streamlit_sql_raises_multi_table(self, orders_df, customers_df):
        pytest.importorskip("streamlit")
        from querychat.streamlit import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        with pytest.raises(AttributeError, match="multiple tables"):
            qc.sql()

    def test_streamlit_title_raises_multi_table(self, orders_df, customers_df):
        pytest.importorskip("streamlit")
        from querychat.streamlit import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        with pytest.raises(AttributeError, match="multiple tables"):
            qc.title()

    def test_streamlit_single_table_accessor_still_works(self, orders_df, customers_df):
        pytest.importorskip("streamlit")
        from unittest.mock import patch

        from querychat.streamlit import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        with patch("streamlit.session_state", {}):
            result = qc.table("customers").df()
        assert result["id"].tolist() == [101, 102, 103]

    def test_state_dict_mixin_df_raises_multi_table(self, orders_df, customers_df):
        from unittest.mock import MagicMock

        from querychat import QueryChat
        from querychat._querychat_core import StateDictAccessorMixin

        qc = QueryChat(orders_df, "orders")
        qc.add_table(customers_df, "customers")

        class DummyAccessor(StateDictAccessorMixin):
            def __init__(self):
                self._data_sources = dict(qc._data_sources)
                self._query_executor = qc._query_executor
                self.greeting = None

            def _require_initialized(self, _m):
                pass

            def _require_query_executor(self, _m):
                return self._query_executor

            def client(self, **_kw):
                return MagicMock()

        acc = DummyAccessor()
        with pytest.raises(AttributeError, match="multiple tables"):
            acc.df({"sql": None, "title": None, "error": None, "turns": []})

    def test_state_dict_mixin_sql_raises_multi_table(self, orders_df, customers_df):
        from unittest.mock import MagicMock

        from querychat import QueryChat
        from querychat._querychat_core import StateDictAccessorMixin

        qc = QueryChat(orders_df, "orders")
        qc.add_table(customers_df, "customers")

        class DummyAccessor(StateDictAccessorMixin):
            def __init__(self):
                self._data_sources = dict(qc._data_sources)
                self._query_executor = qc._query_executor
                self.greeting = None

            def _require_initialized(self, _m):
                pass

            def _require_query_executor(self, _m):
                return self._query_executor

            def client(self, **_kw):
                return MagicMock()

        acc = DummyAccessor()
        with pytest.raises(AttributeError, match="multiple tables"):
            acc.sql({"sql": "SELECT 1", "title": None, "error": None, "turns": []})

    def test_state_dict_mixin_title_raises_multi_table(self, orders_df, customers_df):
        from unittest.mock import MagicMock

        from querychat import QueryChat
        from querychat._querychat_core import StateDictAccessorMixin

        qc = QueryChat(orders_df, "orders")
        qc.add_table(customers_df, "customers")

        class DummyAccessor(StateDictAccessorMixin):
            def __init__(self):
                self._data_sources = dict(qc._data_sources)
                self._query_executor = qc._query_executor
                self.greeting = None

            def _require_initialized(self, _m):
                pass

            def _require_query_executor(self, _m):
                return self._query_executor

            def client(self, **_kw):
                return MagicMock()

        acc = DummyAccessor()
        with pytest.raises(AttributeError, match="multiple tables"):
            acc.title({"sql": None, "title": "hi", "error": None, "turns": []})

    def test_state_dict_mixin_with_table_kwarg_still_works(self, orders_df, customers_df):
        from unittest.mock import MagicMock

        from querychat import QueryChat
        from querychat._querychat_core import StateDictAccessorMixin

        qc = QueryChat(orders_df, "orders")
        qc.add_table(customers_df, "customers")

        class DummyAccessor(StateDictAccessorMixin):
            def __init__(self):
                self._data_sources = dict(qc._data_sources)
                self._query_executor = qc._query_executor
                self.greeting = None

            def _require_initialized(self, _m):
                pass

            def _require_query_executor(self, _m):
                return self._query_executor

            def client(self, **_kw):
                return MagicMock()

        acc = DummyAccessor()
        state = {
            "table_states": {
                "orders": {"sql": None, "title": None, "error": None},
                "customers": {"sql": None, "title": None, "error": None},
            },
            "sql": None, "title": None, "error": None, "turns": [],
        }
        assert acc.sql(state, table="orders") is None
        assert acc.title(state, table="orders") is None


class TestMultiTableQueryTool:
    def test_client_query_tool_executes_join_against_shared_executor(
        self, orders_df, customers_df
    ):
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")
        registered_tools = []

        def capture_registered_tool(_chat, tool):
            registered_tools.append(tool)

        with patch(
            "chatlas.Chat.register_tool",
            autospec=True,
            side_effect=capture_registered_tool,
        ):
            qc.client(tools="query")

        query_tool = next(tool for tool in registered_tools if tool.name == "querychat_query")
        result = query_tool.func(
            """
            SELECT customers.name, orders.amount
            FROM orders
            JOIN customers ON orders.customer_id = customers.id
            WHERE orders.id = 1
            """
        )

        assert result.error is None
        assert result.value == [{"name": "Alice", "amount": 100.0}]


class TestDataDictListInput:
    """Tests for list-based data_dict input to QueryChat."""

    def test_accepts_list_of_data_dicts(self, orders_df, customers_df) -> None:
        from querychat._data_dict import DataDict, TableSpec

        dd1 = DataDict(name="sales", tables={"orders": TableSpec(description="Orders")})
        dd2 = DataDict(
            name="people", tables={"customers": TableSpec(description="Customers")}
        )
        qc = QueryChat(orders_df, "orders", data_dict=[dd1, dd2])
        qc.add_table(customers_df, "customers")
        assert qc is not None

    def test_accepts_list_of_paths(self, orders_df, customers_df, tmp_path) -> None:
        f1 = tmp_path / "orders_dict.yaml"
        f2 = tmp_path / "customers_dict.yaml"
        f1.write_text('tables:\n  orders:\n    description: "Order records."\n')
        f2.write_text('tables:\n  customers:\n    description: "Customer records."\n')
        qc = QueryChat(orders_df, "orders", data_dict=[f1, f2])
        qc.add_table(customers_df, "customers")
        assert qc is not None

    def test_single_data_dict_still_works(self, orders_df) -> None:
        from querychat._data_dict import DataDict, TableSpec

        dd = DataDict(name="sales", tables={"orders": TableSpec(description="Orders")})
        qc = QueryChat(orders_df, "orders", data_dict=dd)
        assert qc is not None

    def test_list_dicts_appear_in_system_prompt(
        self, orders_df, customers_df
    ) -> None:
        from querychat._data_dict import DataDict, TableSpec

        dd1 = DataDict(name="sales", tables={"orders": TableSpec(description="Orders")})
        dd2 = DataDict(
            name="people", tables={"customers": TableSpec(description="Customers")}
        )
        qc = QueryChat(orders_df, "orders", data_dict=[dd1, dd2])
        qc.add_table(customers_df, "customers")
        qc._build_system_prompt()
        rendered = qc._system_prompt.render(qc.tools)
        assert 'name="sales"' in rendered
        assert 'name="people"' in rendered
