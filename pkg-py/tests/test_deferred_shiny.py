"""Tests for deferred data source in Shiny QueryChat."""

import os

import pandas as pd
import pytest
from chatlas import ChatOpenAI
from querychat import QueryChat
from querychat._querychat_base import create_client as _create_client
from querychat.express import QueryChat as ExpressQueryChat
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


class TestShinyDeferredDataSource:
    """Tests for deferred data source in Shiny QueryChat."""

    def test_init_with_none(self):
        """Shiny QueryChat should accept None data_source."""
        qc = QueryChat(None, "users")
        assert qc._data_source is None
        assert qc._table_name == "users"
        # ID should use table_name even with None data_source
        assert qc.id == "querychat_users"

    def test_ui_works_without_data_source(self):
        """ui() should work without data_source set."""
        qc = QueryChat(None, "users")
        # Should not raise
        ui = qc.ui()
        assert ui is not None

    def test_sidebar_works_without_data_source(self):
        """sidebar() should work without data_source set."""
        qc = QueryChat(None, "users")
        # Should not raise
        sidebar = qc.sidebar()
        assert sidebar is not None

    def test_app_requires_data_source(self):
        """app() should raise if data_source not set."""
        qc = QueryChat(None, "users")
        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.app()

    def test_express_requires_data_source_when_deferred(self):
        """Express should fail with a clear error when data_source is still deferred."""
        with (
            session_context(ExpressStubSession()),
            pytest.raises(RuntimeError, match="data_source must be set"),
        ):
            ExpressQueryChat(None, "users")

    def test_server_client_override_does_not_mutate_shared_client_spec(
        self, sample_df, monkeypatch
    ):
        """server(client=...) should keep the override session-local."""
        init_client = ChatOpenAI(model="gpt-4.1")
        override_client = ChatOpenAI(model="gpt-4.1-mini")
        qc = QueryChat(None, "users", client=init_client)
        recorded_specs = []
        real_create_client = _create_client

        def spy_create_client(client_spec):
            recorded_specs.append(client_spec)
            return real_create_client(client_spec)

        monkeypatch.setattr(
            "querychat._querychat_base.create_client", spy_create_client
        )

        with session_context(ExpressStubSession()):
            qc.server(data_source=sample_df, client=override_client)

        assert recorded_specs
        assert recorded_specs[-1] is override_client
        assert qc._client_spec is init_client

    def test_server_without_init_or_override_client_raises_early(self, sample_df):
        """Deferred Shiny setup should fail from server() when no client is available."""
        qc = QueryChat(None, "users")

        with (
            session_context(ExpressStubSession()),
            pytest.raises(RuntimeError, match="client must be set"),
        ):
            qc.server(data_source=sample_df)

    def test_server_rejects_explicit_none_client(self, sample_df):
        """server(client=None) is invalid because None is ambiguous in this API."""
        qc = QueryChat(None, "users", client=ChatOpenAI())

        with (
            session_context(ExpressStubSession()),
            pytest.raises(RuntimeError, match="client must be set"),
        ):
            qc.server(data_source=sample_df, client=None)

    def test_multiple_server_overrides_do_not_leak_into_shared_state(self, sample_df):
        """Sequential overrides should not overwrite the instance-level client spec."""
        init_client = ChatOpenAI(model="gpt-4.1")
        first_override = ChatOpenAI(model="gpt-4.1-mini")
        second_override = ChatOpenAI(model="gpt-4.1-nano")
        qc = QueryChat(None, "users", client=init_client)

        with session_context(ExpressStubSession()):
            qc.server(data_source=sample_df, client=first_override)

        with session_context(ExpressStubSession()):
            qc.server(data_source=sample_df, client=second_override)

        assert qc._client_spec is init_client
