"""Tests for deferred chat client initialization."""

import pandas as pd
import pytest
from chatlas import ChatOpenAI
from querychat._querychat_base import QueryChatBase
from querychat._utils import MISSING


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


class TestDeferredClientInit:
    """Tests for initializing QueryChatBase with deferred client."""

    def test_init_with_none_data_source_defers_client(self):
        """When data_source is None and client is not provided, _client_spec should be None."""
        qc = QueryChatBase(None, "users")
        assert qc._client_spec is None

    def test_init_with_explicit_client_and_none_data_source(self):
        """When data_source is None but client is provided, _client_spec should be stored."""
        qc = QueryChatBase(None, "users", client="openai")
        assert qc._client_spec == "openai"

    def test_init_with_chat_object_stores_spec(self, monkeypatch):
        """When a Chat object is passed, it should be stored as-is."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        chat = ChatOpenAI()
        qc = QueryChatBase(None, "users", client=chat)
        assert qc._client_spec is chat

    def test_init_with_data_source_no_client(self, sample_df):
        """When data_source is provided without client, _client_spec should be None."""
        qc = QueryChatBase(sample_df, "users")
        assert qc._client_spec is None

class TestClientMethodRequirements:
    """Tests that methods properly require data_source to be set."""

    def test_client_method_requires_data_source(self):
        """client() should raise if data_source is not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.client()

    def test_console_requires_data_source(self):
        """console() should raise if data_source is not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.console()

    def test_generate_greeting_requires_data_source(self):
        """generate_greeting() should raise if data_source is not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.generate_greeting()


class TestDeferredClientIntegration:
    """Integration tests for the full deferred client workflow."""

    def test_deferred_data_source_uses_default_client(self, sample_df, monkeypatch):
        """Test setting the data source later still resolves the default client."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        qc = QueryChatBase(None, "users")
        assert qc.data_source is None
        assert qc._client_spec is None

        qc.data_source = sample_df

        client = qc.client()
        assert client is not None
        assert "users" in qc.system_prompt

    def test_deferred_explicit_client_at_init_then_data_source(self, sample_df, monkeypatch):
        """Test an explicit deferred client passed at init still works later."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        qc = QueryChatBase(None, "users", client="openai")
        qc.data_source = sample_df

        client = qc.client()
        assert client is not None

    def test_no_openai_key_error_when_deferred(self, monkeypatch):
        """When data_source is None, no OpenAI API key error should occur."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("QUERYCHAT_CLIENT", raising=False)

        qc = QueryChatBase(None, "users")
        assert qc._client_spec is None


class TestBackwardCompatibility:
    """Tests that existing patterns continue to work."""

    def test_immediate_pattern_unchanged(self, sample_df, monkeypatch):
        """Existing code with data_source continues to work."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "test_table")

        assert qc.data_source is not None
        # _client_spec is None (will use env default at resolution time)
        assert qc._client_spec is None

        client = qc.client()
        assert client is not None

        prompt = qc.system_prompt
        assert "test_table" in prompt


class TestRequireClientSpec:
    """Tests for the server client resolution helper."""

    def test_require_client_spec_uses_init_client_when_server_client_missing(
        self,
        monkeypatch,
    ):
        """Init-time client should be reused when server client is not provided."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        chat = ChatOpenAI()
        qc = QueryChatBase(None, "users", client=chat)

        assert qc._require_client_spec("server", MISSING) is chat

    def test_require_client_spec_raises_when_no_client_available(self):
        """Missing client spec should raise a method-specific RuntimeError."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(
            RuntimeError,
            match=r"client must be set before calling server\(\)",
        ):
            qc._require_client_spec("server", MISSING)

    def test_require_client_spec_rejects_explicit_none(self, monkeypatch):
        """Passing client=None is rejected even if an init client exists."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(None, "users", client=ChatOpenAI())

        with pytest.raises(
            RuntimeError,
            match="client=None is not supported",
        ):
            qc._require_client_spec("server", None)
