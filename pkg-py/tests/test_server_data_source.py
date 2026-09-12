"""Tests for QueryChat.server(data_source=...) parity with R (#300)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import querychat._shiny as shiny_mod


@pytest.fixture(autouse=True)
def set_dummy_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")


@pytest.fixture
def users_df():
    return pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]})


@pytest.fixture
def other_users_df():
    return pd.DataFrame({"id": [4, 5], "name": ["Dana", "Eli"]})


@pytest.fixture
def captured_mod_server(monkeypatch):
    """Patch mod_server and get_current_session; return list of captured kwargs."""
    calls = []

    def fake_mod_server(*args, **kwargs):
        calls.append(kwargs)
        return MagicMock()

    monkeypatch.setattr(shiny_mod, "mod_server", fake_mod_server)
    monkeypatch.setattr(shiny_mod, "get_current_session", lambda: MagicMock())
    return calls


class FakeSession(MagicMock):
    """A fake Shiny session whose on_ended callbacks can be fired manually."""

    def __init__(self):
        super().__init__()
        self._ended_callbacks: list = []
        self.on_ended = self._ended_callbacks.append

    def end(self):
        """Simulate the session ending (fires registered on_ended callbacks)."""
        for cb in self._ended_callbacks:
            cb()


@pytest.fixture
def fake_sessions(monkeypatch):
    """Patch mod_server/get_current_session; each server() call gets a new session."""
    sessions: list[FakeSession] = []

    def fake_mod_server(*args, **kwargs):
        return MagicMock()

    def next_session():
        session = FakeSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(shiny_mod, "mod_server", fake_mod_server)
    monkeypatch.setattr(shiny_mod, "get_current_session", next_session)
    return sessions


class TestServerDataSourceRegistersDeferredTable:
    def test_registers_deferred_table_by_constructor_name(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        assert qc.table_names() == ["users"]
        assert list(captured_mod_server[0]["data_sources"].keys()) == ["users"]

    def test_explicit_table_name_overrides_deferred_name(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df, table_name="people")

        assert qc.table_names() == ["people"]

    def test_falls_back_to_first_existing_table_when_no_name_given(
        self, users_df, other_users_df, captured_mod_server
    ):
        """
        Mirrors R: server(data_source=) with no deferred/explicit name
        replaces the first already-registered table.
        """
        qc = shiny_mod.QueryChat(users_df, "users")
        qc.server(data_source=other_users_df)

        assert qc.table_names() == ["users"]
        registered = captured_mod_server[0]["data_sources"]["users"]
        assert registered.get_data()["id"].tolist() == [4, 5]

    def test_missing_table_name_raises(self, users_df, captured_mod_server):
        qc = shiny_mod.QueryChat()
        with pytest.raises(ValueError, match="table_name"):
            qc.server(data_source=users_df)

    def test_empty_explicit_table_name_raises_instead_of_falling_back(
        self, users_df, captured_mod_server
    ):
        """An explicit table_name="" must be rejected, not treated as omitted."""
        qc = shiny_mod.QueryChat(None, table_name="users")
        with pytest.raises(ValueError, match="must begin with a letter"):
            qc.server(data_source=users_df, table_name="")

    def test_data_source_included_in_greeting(self, users_df, captured_mod_server):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        assert "users" in qc.greeter.tables

    def test_no_data_source_leaves_tables_unchanged(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(users_df, "users")
        qc.server()

        assert qc.table_names() == ["users"]


class TestServerDataSourceSurvivesSecondSession:
    def test_second_session_does_not_raise(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        qc.server(data_source=other_users_df)  # must not raise

        assert list(captured_mod_server[1]["data_sources"].keys()) == ["users"]

    def test_add_table_still_blocked_after_server_init(
        self, users_df, other_users_df, captured_mod_server
    ):
        """
        The public add_table() guard must remain intact; only the
        server(data_source=...) path bypasses it.
        """
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        with pytest.raises(RuntimeError, match="Cannot add tables while a server session"):
            qc.add_table(other_users_df, "other")


class TestServerDataSourceCleanupSafety:
    def test_second_session_does_not_clean_up_first_sessions_source(
        self, users_df, other_users_df, captured_mod_server
    ):
        """
        An earlier, still-running session's executor holds a live
        reference to the source a later session's registration replaces.
        """
        qc = shiny_mod.QueryChat(None, table_name="users")

        qc.server(data_source=users_df)
        first_source = qc._data_sources["users"]

        with patch.object(first_source, "cleanup") as mock_cleanup:
            qc.server(data_source=other_users_df)
            mock_cleanup.assert_not_called()

    def test_public_add_table_replace_still_cleans_up_old_source(
        self, users_df, other_users_df
    ):
        """
        Config-time replacement has a single owner, so cleanup-on-replace
        is unchanged on the public path.
        """
        qc = shiny_mod.QueryChat(users_df, "users")
        first_source = qc._data_sources["users"]

        with patch.object(first_source, "cleanup") as mock_cleanup:
            qc.add_table(other_users_df, "users", replace=True)
            mock_cleanup.assert_called_once()

    def test_second_session_does_not_clean_up_first_sessions_query_executor(
        self, users_df, other_users_df, captured_mod_server
    ):
        """
        An earlier, still-running session's chat has already captured the
        cached executor and may be querying through it.
        """
        qc = shiny_mod.QueryChat(None, table_name="users")

        qc.server(data_source=users_df)
        first_executor = qc._require_query_executor("test")

        with patch.object(first_executor, "cleanup") as mock_cleanup:
            qc.server(data_source=other_users_df)
            mock_cleanup.assert_not_called()

    def test_public_add_table_replace_still_cleans_up_old_query_executor(
        self, users_df, other_users_df
    ):
        """
        Config-time replacement has a single owner, so executor cleanup
        is unchanged on the public path.
        """
        qc = shiny_mod.QueryChat(users_df, "users")
        first_executor = qc._require_query_executor("test")

        with patch.object(first_executor, "cleanup") as mock_cleanup:
            qc.add_table(other_users_df, "users", replace=True)
            mock_cleanup.assert_called_once()

    def test_first_server_call_cleans_up_constructor_registered_source(
        self, users_df, other_users_df, captured_mod_server
    ):
        """No session can still be using it, so cleanup-on-replace holds."""
        qc = shiny_mod.QueryChat(users_df, "users")
        constructor_source = qc._data_sources["users"]

        with patch.object(constructor_source, "cleanup") as mock_cleanup:
            qc.server(data_source=other_users_df)
            mock_cleanup.assert_called_once()

    def test_second_session_skips_cleanup_even_when_first_cleaned_up(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(users_df, "users")

        qc.server(data_source=other_users_df)
        session1_source = qc._data_sources["users"]

        third_df = pd.DataFrame({"id": [7, 8, 9], "name": ["F", "G", "H"]})
        with patch.object(session1_source, "cleanup") as mock_cleanup:
            qc.server(data_source=third_df)
            mock_cleanup.assert_not_called()


class TestServerDataSourceSessionLifecycle:
    """
    The hazard behind cleanup-on-replace and the add/remove_table guards is
    *live* sessions, not past ones: a session that has ended can no longer
    be using a resource it registered.
    """

    def test_ended_sessions_source_is_cleaned_up_on_replace(
        self, users_df, other_users_df, fake_sessions
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)
        first_source = qc._data_sources["users"]

        fake_sessions[0].end()

        with patch.object(first_source, "cleanup") as mock_cleanup:
            qc.server(data_source=other_users_df)
            mock_cleanup.assert_called_once()

    def test_replaced_source_survives_while_any_session_is_live(
        self, users_df, other_users_df, fake_sessions
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)  # session 1
        qc.server(data_source=other_users_df)  # session 2 replaces s1's source
        second_source = qc._data_sources["users"]

        fake_sessions[0].end()  # s1 ends; s2 still live

        third_df = pd.DataFrame({"id": [7], "name": ["F"]})
        with patch.object(second_source, "cleanup") as mock_cleanup:
            qc.server(data_source=third_df)  # session 3 replaces s2's source
            mock_cleanup.assert_not_called()

    def test_add_table_allowed_once_all_sessions_have_ended(
        self, users_df, other_users_df, fake_sessions
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        fake_sessions[0].end()

        qc.add_table(other_users_df, "other")  # must not raise
        assert qc.table_names() == ["users", "other"]


class TestServerDataSourceGreetingSnapshot:
    def test_server_passes_greeting_tables_snapshot_to_mod_server(
        self, users_df, captured_mod_server
    ):
        """
        Greeting generation runs lazily, after a later session may have
        mutated the live greeter.tables -- hence the call-time snapshot.
        """
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        assert captured_mod_server[0]["greeting_tables"] == ["users"]


class TestServerDataSourceMixedWithConfigTimeAddTable:
    def test_unnamed_registration_replaces_config_time_table(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat()
        qc.add_table(users_df, "orders")

        qc.server(data_source=other_users_df)

        # Same table name, but the session's data replaces the config-time data
        sources = captured_mod_server[0]["data_sources"]
        assert list(sources.keys()) == ["orders"]
        assert sources["orders"].get_data()["id"].tolist() == [4, 5]

    def test_replacing_config_time_table_on_first_server_call_cleans_it_up(
        self, users_df, other_users_df, captured_mod_server
    ):
        """
        No session is running yet, so the replaced source has a single owner
        and cleanup-on-replace still holds (only later sessions skip it).
        """
        qc = shiny_mod.QueryChat()
        qc.add_table(users_df, "orders")
        config_source = qc._data_sources["orders"]

        with patch.object(config_source, "cleanup") as mock_cleanup:
            qc.server(data_source=other_users_df)
            mock_cleanup.assert_called_once()

    def test_explicit_table_name_adds_alongside_config_time_table(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat()
        qc.add_table(users_df, "orders")

        qc.server(data_source=other_users_df, table_name="returns")

        sources = captured_mod_server[0]["data_sources"]
        assert list(sources.keys()) == ["orders", "returns"]
        # The config-time table's own data is untouched
        assert sources["orders"].get_data()["id"].tolist() == [1, 2, 3]
        assert sources["returns"].get_data()["id"].tolist() == [4, 5]

    def test_later_session_snapshot_includes_earlier_sessions_table(
        self, users_df, other_users_df, captured_mod_server
    ):
        """The registry is shared and cumulative across sessions."""
        qc = shiny_mod.QueryChat()
        qc.add_table(users_df, "orders")

        # Session 1 adds its own table alongside the config-time one
        qc.server(data_source=other_users_df, table_name="returns")
        # Session 2 replaces "orders" only -- but still sees session 1's table
        third_df = pd.DataFrame({"id": [7, 8, 9]})
        qc.server(data_source=third_df, table_name="orders")

        sources = captured_mod_server[1]["data_sources"]
        assert list(sources.keys()) == ["orders", "returns"]
        assert sources["orders"].get_data()["id"].tolist() == [7, 8, 9]
        assert sources["returns"].get_data()["id"].tolist() == [4, 5]
