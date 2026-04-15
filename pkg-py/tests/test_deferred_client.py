"""Tests for deferred chat client initialization."""

import pandas as pd
import pytest
from chatlas import ChatOpenAI
from querychat._querychat_base import QueryChatBase


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
        """When data_source is None and client is not provided, client should be None."""
        qc = QueryChatBase(None, "users")
        assert qc._client is None
        assert qc.chat_client is None

    def test_init_with_explicit_client_and_none_data_source(self, monkeypatch):
        """When data_source is None but client is provided, client should be initialized."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(None, "users", client="openai")
        assert qc._client is not None
        assert qc.chat_client is not None

    def test_init_with_data_source_defers_client(self, sample_df):
        """When data_source is provided without client, client should be lazily initialized."""
        qc = QueryChatBase(sample_df, "users")
        assert qc._client is None
        assert qc.chat_client is None


class TestChatClientProperty:
    """Tests for the chat_client property setter."""

    def test_chat_client_setter(self, monkeypatch):
        """Setting chat_client should normalize and store the client."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(None, "users")
        assert qc.chat_client is None

        qc.chat_client = "openai"
        assert qc.chat_client is not None

    def test_chat_client_setter_with_chat_object(self, monkeypatch):
        """Setting chat_client with a Chat object should work."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(None, "users")
        assert qc.chat_client is None

        chat = ChatOpenAI()
        qc.chat_client = chat
        assert qc.chat_client is not None

    def test_chat_client_setter_updates_system_prompt(self, sample_df, monkeypatch):
        """Setting chat_client should update system_prompt if data_source is set."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(None, "users")
        qc.data_source = sample_df

        qc.chat_client = "openai"
        assert qc._client is not None
        assert qc._client.system_prompt is not None

    def test_chat_client_getter_returns_none_when_not_set(self):
        """chat_client property returns None when not set."""
        qc = QueryChatBase(None, "users")
        assert qc.chat_client is None


class TestClientMethodRequirements:
    """Tests that methods properly require client or data_source to be set."""

    def test_client_method_requires_data_source(self):
        """client() should raise if neither client nor data_source is set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.client()

    def test_console_requires_data_source(self):
        """console() should raise if neither client nor data_source is set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.console()

    def test_generate_greeting_requires_data_source(self):
        """generate_greeting() should raise if neither client nor data_source is set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="data_source must be set"):
            qc.generate_greeting()


class TestDeferredClientIntegration:
    """Integration tests for the full deferred client workflow."""

    def test_deferred_data_source_and_client(self, sample_df, monkeypatch):
        """Test setting both data_source and client after init."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        qc = QueryChatBase(None, "users")
        assert qc.data_source is None
        assert qc.chat_client is None

        qc.data_source = sample_df
        assert qc.data_source is not None

        qc.chat_client = "openai"
        assert qc.chat_client is not None

        client = qc.client()
        assert client is not None
        assert "users" in qc.system_prompt

    def test_deferred_client_then_data_source(self, sample_df, monkeypatch):
        """Test setting client before data_source."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        qc = QueryChatBase(None, "users")

        qc.chat_client = "openai"
        assert qc.chat_client is not None

        qc.data_source = sample_df
        assert qc.data_source is not None

        client = qc.client()
        assert client is not None

    def test_no_openai_key_error_when_deferred(self, monkeypatch):
        """When data_source is None, no OpenAI API key error should occur."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("QUERYCHAT_CLIENT", raising=False)

        qc = QueryChatBase(None, "users")
        assert qc._client is None
        assert qc.chat_client is None


class TestBackwardCompatibility:
    """Tests that existing patterns continue to work."""

    def test_immediate_pattern_unchanged(self, sample_df, monkeypatch):
        """Existing code with data_source continues to work (client lazily initialized)."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "test_table")

        assert qc.data_source is not None
        # Client is lazily initialized, so chat_client is None until first use
        assert qc.chat_client is None

        client = qc.client()
        assert client is not None
        # After first use, client is initialized
        assert qc.chat_client is not None

        prompt = qc.system_prompt
        assert "test_table" in prompt
