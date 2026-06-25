"""Tests for deferred data source in Shiny QueryChat."""

import os
from unittest.mock import MagicMock

import chatlas
import pandas as pd
import pytest
from chatlas import ChatOpenAI
from querychat import QueryChat
from querychat._querychat_base import create_client as _create_client
from querychat.express import QueryChat as ExpressQueryChat
from shiny._namespaces import Root
from shiny.express._stub_session import ExpressStubSession
from shiny.session import session_context


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
def sample_df():
    """Create a sample pandas DataFrame for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )


class TestNoArgConstruction:
    """Tests for QueryChat() with no positional arguments."""

    def test_init_no_args(self):
        qc = QueryChat()
        assert qc.table_names() == []
        assert qc.id == "querychat"

    def test_init_no_args_then_add_table(self, sample_df):
        qc = QueryChat()
        qc.add_table(sample_df, "users")
        assert qc.table_names() == ["users"]


class TestShinyDeferredDataSource:
    """Tests for deferred data source in Shiny QueryChat."""

    def test_init_with_none(self):
        """Shiny QueryChat should accept None data_source."""
        qc = QueryChat(None, "users")
        assert len(qc.table_names()) == 0
        assert qc.id == "querychat_users"

    def test_ui_works_without_data_source(self):
        """ui() should work without data_source set."""
        qc = QueryChat(None, "users")
        ui = qc.ui()
        assert ui is not None

    def test_sidebar_works_without_data_source(self):
        """sidebar() should work without data_source set."""
        qc = QueryChat(None, "users")
        sidebar = qc.sidebar()
        assert sidebar is not None

    def test_app_requires_data_source(self):
        """app() should raise if data_source not set."""
        qc = QueryChat(None, "users")
        with pytest.raises(RuntimeError, match="At least one data source"):
            qc.app()

    def test_express_allows_deferred_data_source_during_stub_session(self):
        """Express should allow deferred initialization during the stub session."""
        with session_context(ExpressStubSession()):
            qc = ExpressQueryChat(None, "users")

        assert qc is not None

    def test_server_client_override_does_not_mutate_base_client(
        self, sample_df, monkeypatch
    ):
        """server(client=...) should stay lazy during the stub session."""
        init_client = ChatOpenAI(model="gpt-4.1")
        override_client = ChatOpenAI(model="gpt-4.1-mini")
        qc = QueryChat(None, "users", client=init_client)
        qc.add_table(sample_df, "users")
        recorded_specs = []
        real_create_client = _create_client

        def spy_create_client(client_spec):
            recorded_specs.append(client_spec)
            return real_create_client(client_spec)

        monkeypatch.setattr(
            "querychat._querychat_base.create_client", spy_create_client
        )

        with session_context(ExpressStubSession()):
            vals = qc.server(client=override_client)

        assert isinstance(vals.client, chatlas.Chat)
        assert len(recorded_specs) == 1
        assert isinstance(recorded_specs[0], chatlas.Chat)
        assert qc._base_client is init_client

    def test_multiple_server_overrides_do_not_leak_into_shared_state(self, sample_df):
        """Sequential overrides should not overwrite the instance-level base client."""
        init_client = ChatOpenAI(model="gpt-4.1")
        first_override = ChatOpenAI(model="gpt-4.1-mini")
        second_override = ChatOpenAI(model="gpt-4.1-nano")
        qc = QueryChat(None, "users", client=init_client)
        qc.add_table(sample_df, "users")

        with session_context(ExpressStubSession()):
            qc.server(client=first_override)

        # Reset server_initialized for sequential test
        qc._server_initialized = False

        with session_context(ExpressStubSession()):
            qc.server(client=second_override)

        assert qc._base_client is init_client


class TestExpressMultiTable:
    """Tests for multi-table support in QueryChatExpress."""

    @pytest.fixture
    def orders_df(self):
        return pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})

    @pytest.fixture
    def customers_df(self):
        return pd.DataFrame({"id": [101, 102], "name": ["Alice", "Bob"]})

    def test_add_table_does_not_raise_after_init_stub_session(
        self, orders_df, customers_df
    ):
        """add_table() must succeed after __init__ during stub session."""
        with session_context(ExpressStubSession()):
            qc = ExpressQueryChat(orders_df, "orders")
            # Without the fix, _server_initialized would be True here and
            # add_table() would raise RuntimeError.
            qc.add_table(customers_df, "customers")

        assert qc.table_names() == ["orders", "customers"]

    def test_server_not_initialized_after_init_stub_session(self, orders_df):
        """_server_initialized must remain False after __init__ in stub session."""
        with session_context(ExpressStubSession()):
            qc = ExpressQueryChat(orders_df, "orders")
            assert not qc._server_initialized

    def test_ensure_server_started_noop_during_stub_session(
        self, orders_df, monkeypatch
    ):
        """_ensure_server_started() must be a no-op during the stub session."""
        called = []

        def spy_mod_server(*args, **kwargs):
            called.append(True)

        monkeypatch.setattr("querychat._shiny.mod_server", spy_mod_server)

        with session_context(ExpressStubSession()):
            qc = ExpressQueryChat(orders_df, "orders")
            qc._ensure_server_started()

        assert not called, "mod_server should not be called during stub session"

    def test_ensure_server_started_starts_server_in_real_session(
        self, orders_df, monkeypatch
    ):
        """_ensure_server_started() starts the server exactly once in a real session."""
        called = []

        def fake_mod_server(*args, **kwargs):
            called.append((args, kwargs))
            return MagicMock()

        monkeypatch.setattr("querychat._shiny.mod_server", fake_mod_server)

        mock_session = MagicMock()
        mock_session.ns = Root
        with session_context(mock_session):
            qc = ExpressQueryChat(orders_df, "orders")
            assert not qc._server_initialized
            qc._ensure_server_started()

        assert len(called) == 1
        assert qc._server_initialized

    def test_ensure_server_started_idempotent(self, orders_df, monkeypatch):
        """_ensure_server_started() called twice starts server only once."""
        called = []

        def fake_mod_server(*args, **kwargs):
            called.append(True)
            return MagicMock()

        monkeypatch.setattr("querychat._shiny.mod_server", fake_mod_server)

        mock_session = MagicMock()
        mock_session.ns = Root
        with session_context(mock_session):
            qc = ExpressQueryChat(orders_df, "orders")
            qc._ensure_server_started()
            qc._ensure_server_started()

        assert len(called) == 1

    def test_add_table_after_init_then_server_started_in_real_session(
        self, orders_df, customers_df, monkeypatch
    ):
        """Full Express multi-table flow: init → add_table → ensure_server_started."""
        started_with_sources: list[list[str]] = []

        def fake_mod_server(*args, **kwargs):
            started_with_sources.append(list(kwargs["data_sources"].keys()))
            return MagicMock()

        monkeypatch.setattr("querychat._shiny.mod_server", fake_mod_server)

        mock_session = MagicMock()
        mock_session.ns = Root
        with session_context(mock_session):
            qc = ExpressQueryChat(orders_df, "orders")
            qc.add_table(customers_df, "customers")
            qc._ensure_server_started()

        assert started_with_sources == [["orders", "customers"]]

    def test_table_delegates_to_vals(self, orders_df, customers_df, monkeypatch):
        """table() should delegate to _vals.table() and return its result."""
        fake_accessor = MagicMock()
        fake_vals = MagicMock()
        fake_vals.table.return_value = fake_accessor

        monkeypatch.setattr("querychat._shiny.mod_server", lambda *a, **kw: fake_vals)

        mock_session = MagicMock()
        mock_session.ns = Root
        with session_context(mock_session):
            qc = ExpressQueryChat(orders_df, "orders")
            qc.add_table(customers_df, "customers")
            result = qc.table("orders")

        fake_vals.table.assert_called_once_with("orders")
        assert result is fake_accessor

    def test_table_unknown_name_propagates_error(
        self, orders_df, customers_df, monkeypatch
    ):
        """table() with an unknown name should propagate ValueError from ServerValues."""
        fake_vals = MagicMock()
        fake_vals.table.side_effect = ValueError("'foo' not found")

        monkeypatch.setattr("querychat._shiny.mod_server", lambda *a, **kw: fake_vals)

        mock_session = MagicMock()
        mock_session.ns = Root
        with session_context(mock_session):
            qc = ExpressQueryChat(orders_df, "orders")
            qc.add_table(customers_df, "customers")
            with pytest.raises(ValueError, match="not found"):
                qc.table("foo")

    def test_current_table_delegates_to_vals(
        self, orders_df, customers_df, monkeypatch
    ):
        """current_table() should delegate to _vals.current_table()."""
        fake_vals = MagicMock()
        fake_vals.current_table.return_value = "customers"

        monkeypatch.setattr("querychat._shiny.mod_server", lambda *a, **kw: fake_vals)

        mock_session = MagicMock()
        mock_session.ns = Root
        with session_context(mock_session):
            qc = ExpressQueryChat(orders_df, "orders")
            qc.add_table(customers_df, "customers")
            result = qc.current_table()

        fake_vals.current_table.assert_called_once()
        assert result == "customers"

    def test_current_table_returns_none_before_any_query(
        self, orders_df, customers_df, monkeypatch
    ):
        """current_table() returns None when no query has been run yet."""
        fake_vals = MagicMock()
        fake_vals.current_table.return_value = None

        monkeypatch.setattr("querychat._shiny.mod_server", lambda *a, **kw: fake_vals)

        mock_session = MagicMock()
        mock_session.ns = Root
        with session_context(mock_session):
            qc = ExpressQueryChat(orders_df, "orders")
            qc.add_table(customers_df, "customers")
            result = qc.current_table()

        assert result is None
