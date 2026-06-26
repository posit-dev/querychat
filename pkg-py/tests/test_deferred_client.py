"""Tests for deferred chat client initialization."""

import chatlas
import pandas as pd
import pytest
from chatlas import ChatOpenAI, Turn
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
        """When data_source is None and client is not provided, _base_client should be None."""
        qc = QueryChatBase(None, "users")
        assert qc._base_client is None

    def test_init_with_explicit_client_and_none_data_source(self, monkeypatch):
        """When data_source is None but client is provided, _base_client should be resolved."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(None, "users", client="openai")
        assert isinstance(qc._base_client, chatlas.Chat)

    def test_init_with_chat_object_stores_spec(self, monkeypatch):
        """When a Chat object is passed, it should be stored as-is."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        chat = ChatOpenAI()
        qc = QueryChatBase(None, "users", client=chat)
        assert qc._base_client is chat

    def test_init_with_data_source_no_client(self, sample_df):
        """When data_source is provided without client, _base_client should be None."""
        qc = QueryChatBase(sample_df, "users")
        assert qc._base_client is None

    def test_init_with_invalid_explicit_client_raises_immediately(self):
        """Invalid explicit client specs should fail at init (fail-fast)."""
        with pytest.raises(ValueError, match="is not a known chatlas provider"):
            QueryChatBase(None, "users", client="not_a_real_provider_xyz123")


class TestClientMethodRequirements:
    """Tests that methods properly require data_source to be set."""

    def test_client_method_requires_data_source(self):
        """client() should raise if data_source is not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="At least one data source"):
            qc.client()

    def test_console_requires_data_source(self):
        """console() should raise if data_source is not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="At least one data source"):
            qc.console()

    def test_generate_greeting_requires_data_source(self):
        """generate_greeting() should raise if data_source is not set."""
        qc = QueryChatBase(None, "users")

        with pytest.raises(RuntimeError, match="At least one data source"):
            qc.generate_greeting()


class TestDeferredClientIntegration:
    """Integration tests for the full deferred client workflow."""

    def test_deferred_data_source_uses_default_client(self, sample_df, monkeypatch):
        """Test setting the data source later still resolves the default client."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        qc = QueryChatBase(None, "users")
        assert len(qc.table_names()) == 0
        assert qc._base_client is None

        qc.add_table(sample_df, "users")

        client = qc.client()
        assert client is not None
        assert "users" in qc.system_prompt

    def test_deferred_explicit_client_at_init_then_data_source(
        self, sample_df, monkeypatch
    ):
        """Test an explicit deferred client passed at init still works later."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        qc = QueryChatBase(None, "users", client="openai")
        qc.add_table(sample_df, "users")

        client = qc.client()
        assert client is not None

    def test_no_openai_key_error_when_deferred(self, monkeypatch):
        """When data_source is None, no OpenAI API key error should occur."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("QUERYCHAT_CLIENT", raising=False)

        qc = QueryChatBase(None, "users")
        assert qc._base_client is None

    def test_invalid_explicit_client_raises_when_client_is_resolved(self):
        """Invalid explicit client specs should fail at init (fail-fast)."""
        with pytest.raises(ValueError, match="is not a known chatlas provider"):
            QueryChatBase(None, "users", client="not_a_real_provider_xyz123")


class TestBackwardCompatibility:
    """Tests that existing patterns continue to work."""

    def test_immediate_pattern_unchanged(self, sample_df, monkeypatch):
        """Existing code with data_source continues to work."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "test_table")

        assert len(qc.table_names()) > 0
        assert qc._base_client is None

        client = qc.client()
        assert client is not None

        prompt = qc.system_prompt
        assert "test_table" in prompt


@pytest.fixture
def other_df():
    return pd.DataFrame({"order_id": [1, 2], "amount": [100, 200]})


class TestPromptRebuildWarning:
    """Warns when system prompt is rebuilt after a client already has chat history."""

    def test_warns_when_base_client_has_history(self, sample_df, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        chat = ChatOpenAI()
        chat.set_turns([Turn(role="user", contents=["hello"])])

        qc = QueryChatBase(None, "users", client=chat)

        with pytest.warns(UserWarning, match="chat history"):
            qc.add_table(sample_df, "users")

    def test_warns_when_console_client_has_history(
        self, sample_df, other_df, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users")

        console_chat = ChatOpenAI()
        console_chat.set_turns([Turn(role="user", contents=["hello"])])
        qc._client_console = console_chat

        with pytest.warns(UserWarning, match="chat history"):
            qc.add_table(other_df, "orders")

    def test_no_warning_without_history(
        self, sample_df, other_df, recwarn, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users")
        qc.add_table(other_df, "orders")
        chat_history_warnings = [
            w for w in recwarn.list if "chat history" in str(w.message)
        ]
        assert len(chat_history_warnings) == 0
