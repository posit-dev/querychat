"""Tests for per-table accessor API in non-Shiny frameworks."""

import os
from unittest.mock import MagicMock

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    old = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old is not None:
        os.environ["OPENAI_API_KEY"] = old
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def orders_df():
    return pd.DataFrame({"id": [1, 2, 3], "amount": [100.0, 200.0, 150.0]})


@pytest.fixture
def customers_df():
    return pd.DataFrame({"id": [101, 102], "name": ["Alice", "Bob"], "state": ["CA", "NY"]})


class TestStreamlitMultiTable:
    @pytest.fixture(autouse=True)
    def _skip(self):
        pytest.importorskip("streamlit")

    def _make_qc(self, orders_df, customers_df):
        from querychat.streamlit import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        return qc

    def test_table_returns_streamlit_table_accessor(self, orders_df, customers_df):
        from querychat.streamlit import StreamlitTableAccessor

        qc = self._make_qc(orders_df, customers_df)
        acc = qc.table("orders")
        assert isinstance(acc, StreamlitTableAccessor)

    def test_table_unknown_raises(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(ValueError, match="'foo' not found"):
            qc.table("foo")

    def test_table_df_returns_full_data_when_no_filter(self, orders_df, customers_df):
        from unittest.mock import patch

        qc = self._make_qc(orders_df, customers_df)
        fake_session = {}
        with patch("streamlit.session_state", fake_session):
            result = qc.table("customers").df()
        assert result["id"].tolist() == [101, 102]

    def test_table_df_applies_filter(self, orders_df, customers_df):
        from unittest.mock import patch

        qc = self._make_qc(orders_df, customers_df)
        fake_session = {}
        with patch("streamlit.session_state", fake_session):
            # Simulate the LLM having set a filter for customers
            state = qc._get_state()  # initialises session state
            state._table_states["customers"]["sql"] = (
                "SELECT * FROM customers WHERE state = 'CA'"
            )
            result = qc.table("customers").df()
        assert result["id"].tolist() == [101]

    def test_table_sql_and_title(self, orders_df, customers_df):
        from unittest.mock import patch

        qc = self._make_qc(orders_df, customers_df)
        fake_session = {}
        with patch("streamlit.session_state", fake_session):
            state = qc._get_state()
            state._table_states["orders"]["sql"] = "SELECT * FROM orders WHERE amount > 100"
            state._table_states["orders"]["title"] = "Big orders"
            assert qc.table("orders").sql() == "SELECT * FROM orders WHERE amount > 100"
            assert qc.table("orders").title() == "Big orders"
            assert qc.table("customers").sql() is None


class TestStateDictAccessorMixinMultiTable:
    """Tests for table= parameter on StateDictAccessorMixin."""

    def _make_accessor(self, orders_df, customers_df):
        from querychat import QueryChat
        from querychat._querychat_core import StateDictAccessorMixin

        qc = QueryChat(orders_df, "orders")
        qc.add_table(customers_df, "customers")

        class DummyAccessor(StateDictAccessorMixin):
            def __init__(self):
                self._data_sources = dict(qc._data_sources)
                self._query_executor = qc._require_query_executor("test")
                self.greeting = None

            def _require_initialized(self, _m):
                pass

            def _require_query_executor(self, _m):
                return self._query_executor

            def client(self, **_kw):
                return MagicMock()

        return DummyAccessor()

    def _state(self, active="orders", orders_sql=None, customers_sql=None):
        """Build a state dict with table_states."""
        return {
            "table": active,
            "sql": orders_sql if active == "orders" else customers_sql,
            "title": None,
            "error": None,
            "table_states": {
                "orders": {"sql": orders_sql, "title": None, "error": None},
                "customers": {"sql": customers_sql, "title": None, "error": None},
            },
            "turns": [],
        }

    def test_df_table_kwarg_returns_specific_table_data(self, orders_df, customers_df):
        acc = self._make_accessor(orders_df, customers_df)
        state = self._state(
            active="orders",
            orders_sql="SELECT * FROM orders WHERE amount > 100",
            customers_sql=None,
        )
        result = acc.df(state, table="customers")
        # customers has no filter → full dataset
        assert result["id"].tolist() == [101, 102]

    def test_df_table_kwarg_applies_filter(self, orders_df, customers_df):
        acc = self._make_accessor(orders_df, customers_df)
        state = self._state(
            active="orders",
            customers_sql="SELECT * FROM customers WHERE state = 'CA'",
        )
        result = acc.df(state, table="customers")
        assert result["id"].tolist() == [101]

    def test_sql_table_kwarg(self, orders_df, customers_df):
        acc = self._make_accessor(orders_df, customers_df)
        state = self._state(customers_sql="SELECT * FROM customers WHERE state = 'NY'")
        assert acc.sql(state, table="customers") == (
            "SELECT * FROM customers WHERE state = 'NY'"
        )
        assert acc.sql(state, table="orders") is None

    def test_title_table_kwarg(self, orders_df, customers_df):
        acc = self._make_accessor(orders_df, customers_df)
        state = {
            "table": "customers",
            "sql": None,
            "title": None,
            "error": None,
            "table_states": {
                "orders": {"sql": None, "title": "Big orders", "error": None},
                "customers": {"sql": None, "title": None, "error": None},
            },
            "turns": [],
        }
        assert acc.title(state, table="orders") == "Big orders"
        assert acc.title(state, table="customers") is None

    def test_backward_compat_no_table_states_key(self, orders_df, customers_df):
        """Old state dicts without table_states should still work for the active table."""
        acc = self._make_accessor(orders_df, customers_df)
        old_state = {
            "table": "orders",
            "sql": "SELECT * FROM orders WHERE amount > 100",
            "title": "Big orders",
            "error": None,
            "turns": [],
        }
        assert acc.sql(old_state, table="orders") == (
            "SELECT * FROM orders WHERE amount > 100"
        )
        assert acc.title(old_state, table="orders") == "Big orders"
        # Non-active table with no table_states → None
        assert acc.sql(old_state, table="customers") is None


class TestDashTableAccessor:
    """table() on Dash QueryChat returns StateDictTableAccessor."""

    @pytest.fixture(autouse=True)
    def _skip(self):
        pytest.importorskip("dash")

    def _make_qc(self, orders_df, customers_df):
        from querychat.dash import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        return qc

    def test_table_data_source_accessible(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        ds = qc.table("orders").data_source
        assert ds is qc._data_sources["orders"]

    def test_table_unknown_raises(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(ValueError, match="'foo' not found"):
            qc.table("foo")

    def test_table_df_raises_not_implemented(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(NotImplementedError, match=r"qc\.df\(state"):
            qc.table("orders").df()

    def test_table_sql_raises_not_implemented(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(NotImplementedError, match=r"qc\.sql\(state"):
            qc.table("orders").sql()

    def test_table_title_raises_not_implemented(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(NotImplementedError, match=r"qc\.title\(state"):
            qc.table("orders").title()


class TestGradioTableAccessor:
    """table() on Gradio QueryChat returns StateDictTableAccessor."""

    @pytest.fixture(autouse=True)
    def _skip(self):
        pytest.importorskip("gradio")

    def _make_qc(self, orders_df, customers_df):
        from querychat.gradio import QueryChat

        qc = QueryChat(orders_df, "orders", greeting="Hi")
        qc.add_table(customers_df, "customers")
        return qc

    def test_table_data_source_accessible(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        ds = qc.table("orders").data_source
        assert ds is qc._data_sources["orders"]

    def test_table_unknown_raises(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(ValueError, match="'foo' not found"):
            qc.table("foo")

    def test_table_df_raises_not_implemented(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(NotImplementedError, match=r"qc\.df\(state"):
            qc.table("orders").df()

    def test_table_sql_raises_not_implemented(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(NotImplementedError, match=r"qc\.sql\(state"):
            qc.table("orders").sql()

    def test_table_title_raises_not_implemented(self, orders_df, customers_df):
        qc = self._make_qc(orders_df, customers_df)
        with pytest.raises(NotImplementedError, match=r"qc\.title\(state"):
            qc.table("orders").title()
