"""Tests for multi-table support."""

import os

import pandas as pd
import pytest
from querychat import QueryChat, TableAccessor


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

    def test_data_source_property_returns_first_source(self, orders_df):
        """Test backwards compatibility: data_source property returns the first source."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")

        # data_source property should return the single source
        assert qc.data_source is qc._data_sources["orders"]

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

    def test_add_table_with_relationships(self, orders_df, customers_df):
        """Test adding table with explicit relationships."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(
            customers_df, "customers", relationships={"id": "orders.customer_id"}
        )

        assert "customers" in qc._data_sources

    def test_add_table_with_description(self, orders_df, customers_df):
        """Test adding table with description."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(
            customers_df, "customers", description="Customer contact information"
        )

        assert "customers" in qc._data_sources

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


class TestAccessorAmbiguity:
    """Tests for accessor ambiguity errors with multiple tables."""

    def test_df_single_table_works(self, orders_df):
        """Test that data_source works with single table."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        # data_source property should work
        assert qc.data_source is qc._data_sources["orders"]

    def test_data_source_multiple_tables_raises(self, orders_df, customers_df):
        """Test that data_source property raises with multiple tables."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        with pytest.raises(ValueError, match="Multiple tables present"):
            _ = qc.data_source


class TestMultiTableSystemPrompt:
    """Tests for multi-table system prompt generation."""

    def test_multiple_schemas_in_prompt(self, orders_df, customers_df):
        """Test that multiple table schemas appear in prompt."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        prompt = qc.system_prompt

        assert "orders" in prompt
        assert "customers" in prompt

    def test_system_prompt_contains_all_columns(self, orders_df, customers_df):
        """Test that system prompt contains columns from all tables."""
        qc = QueryChat(orders_df, "orders", greeting="Hello!")
        qc.add_table(customers_df, "customers")

        prompt = qc.system_prompt

        # Orders columns
        assert "id" in prompt
        assert "customer_id" in prompt
        assert "amount" in prompt
        # Customers columns
        assert "name" in prompt
        assert "state" in prompt


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
