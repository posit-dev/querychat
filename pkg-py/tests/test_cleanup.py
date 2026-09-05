"""Tests for QueryChatBase.cleanup() resource lifecycle."""

from unittest.mock import patch

import chatlas
import pandas as pd
import pytest
from chatlas import ChatOpenAI
from querychat._querychat_base import QueryChatBase


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        },
    )


class TestClientOwnership:
    """querychat closes the chatlas client only if it created it."""

    def test_owns_client_flag(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        # String spec: querychat-created
        assert QueryChatBase(sample_df, "users", client="openai")._owns_client
        # None (deferred default/env): querychat-created
        assert QueryChatBase(sample_df, "users")._owns_client
        # User-supplied instance: not owned
        assert not QueryChatBase(
            sample_df, "users", client=ChatOpenAI()
        )._owns_client

    def test_cleanup_closes_owned_string_client(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        assert isinstance(qc._base_client, chatlas.Chat)
        qc.cleanup()
        assert qc._base_client.provider._client.is_closed()

    def test_cleanup_closes_deferred_default_client(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        monkeypatch.delenv("QUERYCHAT_CLIENT", raising=False)
        qc = QueryChatBase(sample_df, "users")
        assert qc._base_client is None
        # Trigger deferred resolution (env var / "openai" default)
        qc._create_client()
        assert isinstance(qc._base_client, chatlas.Chat)
        qc.cleanup()
        assert qc._base_client.provider._client.is_closed()

    def test_cleanup_does_not_close_user_supplied_client(
        self, monkeypatch, sample_df
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        chat = ChatOpenAI()
        qc = QueryChatBase(sample_df, "users", client=chat)
        qc.cleanup()
        assert not chat.provider._client.is_closed()

    def test_cleanup_closes_clones_via_shared_provider(
        self, monkeypatch, sample_df
    ):
        """Session/console clones share the base provider (deepcopy by
        reference), so closing the owned base client covers them."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        clone = qc._create_client()
        assert clone.provider is qc._base_client.provider
        qc.cleanup()
        assert clone.provider._client.is_closed()


class TestCleanupDataSources:
    """Existing executor/source cleanup behavior is preserved."""

    def test_cleanup_closes_data_source(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        source = qc._data_sources["users"]
        with patch.object(source, "cleanup") as mock_cleanup:
            qc.cleanup()
            mock_cleanup.assert_called_once()

    def test_cleanup_is_idempotent(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        qc.cleanup()
        qc.cleanup()  # should not raise
