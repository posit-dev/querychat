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
        """
        An explicit but invalid table_name="" must be validated and rejected,
        not silently treated as omitted and fall back to the deferred/first
        table name.
        """
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
    """
    server(data_source=...) must not be blocked by an earlier session having
    already registered a table -- unlike the public add_table(), which still
    guards against changes after server initialization.
    """

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

        with pytest.raises(RuntimeError, match="Cannot add tables after server"):
            qc.add_table(other_users_df, "other")


class TestServerDataSourceCleanupSafety:
    def test_second_session_does_not_clean_up_first_sessions_source(
        self, users_df, other_users_df, captured_mod_server
    ):
        """
        A second session's server(data_source=...) call must not tear down
        the DataSource object an earlier, still-running session's own
        DataSourceExecutor holds a live reference to (e.g. closing a DuckDB
        connection or disposing a SQLAlchemy engine out from under it).
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
        Config-time add_table(replace=True) (before any session starts) has
        exactly one owner for the replaced table, so its existing
        cleanup-on-replace behavior must be unchanged.
        """
        qc = shiny_mod.QueryChat(users_df, "users")
        first_source = qc._data_sources["users"]

        with patch.object(first_source, "cleanup") as mock_cleanup:
            qc.add_table(other_users_df, "users", replace=True)
            mock_cleanup.assert_called_once()
