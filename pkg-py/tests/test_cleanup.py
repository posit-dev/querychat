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

    def test_ownership_registration(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")

        # String spec: querychat-created, tracked at construction
        qc = QueryChatBase(sample_df, "users", client="openai")
        assert qc._owned_clients == [qc._base_client]
        # None (deferred default/env): tracked once resolved, not before
        assert QueryChatBase(sample_df, "users")._owned_clients == []
        # User-supplied instance: never tracked
        assert (
            QueryChatBase(sample_df, "users", client=ChatOpenAI())._owned_clients == []
        )

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

    def test_cleanup_does_not_close_user_supplied_client(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        chat = ChatOpenAI()
        qc = QueryChatBase(sample_df, "users", client=chat)
        qc.cleanup()
        assert not chat.provider._client.is_closed()

    def test_cleanup_closes_clones_via_shared_provider(self, monkeypatch, sample_df):
        """
        Session/console clones share the base provider (deepcopy by
        reference), so closing the owned base client covers them.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        clone = qc._create_client()
        assert clone.provider is qc._base_client.provider
        qc.cleanup()
        assert clone.provider._client.is_closed()


class TestServerClientOverrides:
    """
    Clients resolved for .server(client=...) overrides follow the same
    ownership rule: spec-resolved overrides are closed, user-supplied ones
    are not.
    """

    def test_owned_override_closed_when_base_is_user_supplied(
        self, monkeypatch, sample_df
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        user_chat = ChatOpenAI()
        qc = QueryChatBase(sample_df, "users", client=user_chat)
        override = qc._resolve_override_client("openai")
        qc.cleanup()
        assert override.provider._client.is_closed()
        assert not user_chat.provider._client.is_closed()

    def test_owned_override_closed_when_base_deferred(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users")
        override = qc._resolve_override_client("openai")
        assert qc._base_client is None
        qc.cleanup()
        assert override.provider._client.is_closed()

    def test_deferred_default_override_closed(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        monkeypatch.delenv("QUERYCHAT_CLIENT", raising=False)
        qc = QueryChatBase(sample_df, "users", client="openai")
        override = qc._resolve_override_client(None)
        qc.cleanup()
        assert override.provider._client.is_closed()

    def test_user_supplied_override_not_closed(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        override = ChatOpenAI()
        qc._resolve_override_client(override)
        qc.cleanup()
        assert not override.provider._client.is_closed()


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
