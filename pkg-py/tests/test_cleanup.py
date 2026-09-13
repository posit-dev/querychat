"""Tests for QueryChatBase.cleanup() resource lifecycle."""

from unittest.mock import MagicMock, patch

import chatlas
import pandas as pd
import pytest
import querychat._shiny as shiny_mod
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
    def test_string_spec_client_is_owned(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        assert qc._base_client_owned is True

    def test_user_supplied_client_is_not_owned(self, sample_df):
        qc = QueryChatBase(sample_df, "users", client=ChatOpenAI(api_key="sk-x"))
        assert qc._base_client_owned is False

    def test_deferred_default_client_is_owned(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users")
        assert qc._base_client is None
        qc.client()
        assert qc._base_client is not None
        assert qc._base_client_owned is True

    def test_cleanup_closes_owned_client(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        qc.cleanup()
        assert qc._base_client.provider._client.is_closed()

    def test_cleanup_does_not_close_user_supplied_client(self, sample_df):
        chat = ChatOpenAI(api_key="sk-x")
        qc = QueryChatBase(sample_df, "users", client=chat)
        qc.cleanup()
        assert not chat.provider._client.is_closed()

    def test_cleanup_closes_clones_via_shared_provider(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        clone = qc.client()
        qc.cleanup()
        assert clone.provider._client.is_closed()


class TestServerClientOverrides:
    """.server(client=...) overrides belong to the session, not the instance."""

    @pytest.fixture
    def ended_callbacks(self, monkeypatch):
        callbacks = []
        fake_session = MagicMock()
        fake_session.on_ended = callbacks.append
        monkeypatch.setattr(shiny_mod, "get_current_session", lambda: fake_session)
        monkeypatch.setattr(shiny_mod, "mod_server", lambda *args, **kwargs: None)
        return callbacks

    @pytest.fixture
    def resolved_clients(self, monkeypatch):
        import querychat._querychat_base as base_mod

        created: list[chatlas.Chat] = []
        real = base_mod.resolve_client

        def spy(spec):
            chat = real(spec)
            created.append(chat)
            return chat

        monkeypatch.setattr(base_mod, "resolve_client", spy)
        return created

    def test_spec_override_closed_on_session_end(
        self, monkeypatch, sample_df, ended_callbacks, resolved_clients
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = shiny_mod.QueryChat(sample_df, "users")
        qc.server(client="openai")

        (override,) = resolved_clients
        assert not override.provider._client.is_closed()
        for cb in ended_callbacks:
            cb()
        assert override.provider._client.is_closed()

    def test_user_supplied_override_not_closed_on_session_end(
        self, sample_df, ended_callbacks
    ):
        qc = shiny_mod.QueryChat(sample_df, "users", client=ChatOpenAI(api_key="sk-x"))
        chat = ChatOpenAI(api_key="sk-x")
        qc.server(client=chat)

        for cb in ended_callbacks:
            cb()
        qc.cleanup()
        assert not chat.provider._client.is_closed()

    def test_cleanup_does_not_close_live_session_override(
        self, monkeypatch, sample_df, ended_callbacks, resolved_clients
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = shiny_mod.QueryChat(sample_df, "users", client=ChatOpenAI(api_key="sk-x"))
        qc.server(client="openai")

        (override,) = resolved_clients
        qc.cleanup()
        assert not override.provider._client.is_closed()

    def test_session_override_does_not_leak_into_instance(
        self, monkeypatch, sample_df, ended_callbacks
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        base = ChatOpenAI(api_key="sk-x")
        qc = shiny_mod.QueryChat(sample_df, "users", client=base)
        qc.server(client="openai")

        assert qc._base_client is base
        assert qc._base_client_owned is False


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

    def test_cleanup_warns_on_client_close_failure(self, monkeypatch, sample_df):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        qc = QueryChatBase(sample_df, "users", client="openai")
        with (
            patch.object(qc._base_client, "close", side_effect=RuntimeError("boom")),
            pytest.warns(UserWarning, match="Failed to clean up chatlas client"),
        ):
            qc.cleanup()
