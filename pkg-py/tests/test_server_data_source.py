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
def session_runs(monkeypatch):
    """Each server() call gets a fresh FakeSession; mod_server kwargs are captured."""
    sessions: list[FakeSession] = []
    calls: list[dict] = []

    def fake_mod_server(*args, **kwargs):
        calls.append(kwargs)
        return MagicMock()

    def next_session():
        session = FakeSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(shiny_mod, "mod_server", fake_mod_server)
    monkeypatch.setattr(shiny_mod, "get_current_session", next_session)
    return sessions, calls


class TestServerDataSourceRegistersDeferredTable:
    def test_registers_deferred_table_by_constructor_name(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        assert qc.table_names() == []
        assert captured_mod_server[0]["table_set"].table_names == ["users"]

    def test_explicit_table_name_overrides_deferred_name(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df, table_name="people")

        assert captured_mod_server[0]["table_set"].table_names == ["people"]

    def test_falls_back_to_first_existing_table_when_no_name_given(
        self, users_df, other_users_df, captured_mod_server
    ):
        """server(data_source=) with no deferred/explicit name shadows the first registered table for this session."""
        qc = shiny_mod.QueryChat(users_df, "users")
        qc.server(data_source=other_users_df)

        assert qc._data_sources["users"].get_data()["id"].tolist() == [1, 2, 3]
        registered = captured_mod_server[0]["table_set"].data_sources["users"]
        assert registered.get_data()["id"].tolist() == [4, 5]

    def test_missing_table_name_raises(self, users_df, captured_mod_server):
        qc = shiny_mod.QueryChat()
        with pytest.raises(ValueError, match="table_name"):
            qc.server(data_source=users_df)

    def test_invalid_deferred_table_name_raises_at_construction(self):
        """A bad deferred name must fail fast, not at .server() registration."""
        with pytest.raises(ValueError, match="must begin with a letter"):
            shiny_mod.QueryChat(None, table_name="bad-name")

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

        assert captured_mod_server[0]["greeting_tables"] == ["users"]

    def test_no_data_source_leaves_tables_unchanged(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(users_df, "users")
        qc.server()

        assert qc.table_names() == ["users"]


class TestServerDataSourceSessionIsolation:
    def test_instance_tables_unchanged_by_session_registration(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        assert qc.table_names() == []
        assert captured_mod_server[0]["table_set"].table_names == ["users"]

    def test_each_session_gets_its_own_source(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)
        qc.server(data_source=other_users_df)

        first = captured_mod_server[0]["table_set"].data_sources["users"]
        second = captured_mod_server[1]["table_set"].data_sources["users"]
        assert first is not second
        assert first.get_data()["id"].tolist() == [1, 2, 3]
        assert second.get_data()["id"].tolist() == [4, 5]

    def test_session_table_shadows_config_time_table(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(users_df, "users")
        config_source = qc._data_sources["users"]

        qc.server(data_source=other_users_df)

        assert qc._data_sources["users"] is config_source
        session_source = captured_mod_server[0]["table_set"].data_sources["users"]
        assert session_source is not config_source
        assert session_source.get_data()["id"].tolist() == [4, 5]

    def test_sessions_do_not_see_each_others_tables(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat()
        qc.add_table(users_df, "orders")

        qc.server(data_source=other_users_df, table_name="returns")
        qc.server(data_source=pd.DataFrame({"id": [7]}), table_name="orders")

        assert captured_mod_server[0]["table_set"].table_names == ["orders", "returns"]
        assert captured_mod_server[1]["table_set"].table_names == ["orders"]

    def test_greeting_tables_snapshot_is_per_session(
        self, users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)

        assert captured_mod_server[0]["greeting_tables"] == ["users"]
        assert qc.greeter.tables == []

    def test_greeter_build_client_forwards_table_set(
        self, users_df, other_users_df, captured_mod_server
    ):
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)
        qc.server(data_source=other_users_df)

        seen = []

        def factory(tables, prompt, base=None, *, table_set=None):
            seen.append(table_set)
            return MagicMock()

        qc.greeter._client_factory = factory
        first_set = captured_mod_server[0]["table_set"]
        qc.greeter.build_client(tables=["users"], table_set=first_set)
        assert seen == [first_set]


class TestServerDataSourceSessionCleanup:
    def test_ending_a_session_closes_only_its_own_source_and_executor(
        self, users_df, other_users_df, session_runs
    ):
        sessions, calls = session_runs
        qc = shiny_mod.QueryChat(None, table_name="users")
        qc.server(data_source=users_df)
        qc.server(data_source=other_users_df)
        set_a, set_b = calls[0]["table_set"], calls[1]["table_set"]
        src_a, src_b = set_a.data_sources["users"], set_b.data_sources["users"]

        with (
            patch.object(src_a, "cleanup") as cleanup_a,
            patch.object(src_b, "cleanup") as cleanup_b,
            patch.object(set_a, "cleanup_executor") as exec_a,
            patch.object(set_b, "cleanup_executor") as exec_b,
        ):
            sessions[1].end()
            cleanup_b.assert_called_once()
            exec_b.assert_called_once()
            cleanup_a.assert_not_called()
            exec_a.assert_not_called()

            sessions[0].end()
            cleanup_a.assert_called_once()
            exec_a.assert_called_once()

    def test_session_without_data_source_owns_nothing(self, users_df, session_runs):
        sessions, _calls = session_runs
        qc = shiny_mod.QueryChat(users_df, "users")
        qc.server()
        config_source = qc._data_sources["users"]

        assert sessions[0]._ended_callbacks == []

        with (
            patch.object(config_source, "cleanup") as cleanup,
            patch.object(qc._table_set, "cleanup_executor") as cleanup_executor,
        ):
            sessions[0].end()
            cleanup.assert_not_called()
            cleanup_executor.assert_not_called()

    def test_config_time_source_survives_until_cleanup(
        self, users_df, other_users_df, session_runs
    ):
        sessions, _calls = session_runs
        qc = shiny_mod.QueryChat(users_df, "users")
        config_source = qc._data_sources["users"]
        qc.server(data_source=other_users_df)

        with patch.object(config_source, "cleanup") as cleanup:
            sessions[0].end()
            cleanup.assert_not_called()
            qc.cleanup()
            cleanup.assert_called_once()

    def test_failed_registration_closes_its_source_and_leaves_instance_untouched(
        self, users_df, session_runs, monkeypatch
    ):
        import duckdb
        import polars as pl

        sessions, calls = session_runs
        qc = shiny_mod.QueryChat(users_df, "users")
        created = []
        real_normalize = shiny_mod.normalize_data_source

        def spy(data_source, table_name):
            source = real_normalize(data_source, table_name)
            created.append(source)
            return source

        monkeypatch.setattr(shiny_mod, "normalize_data_source", spy)

        with pytest.raises(ValueError, match="same DataFrame backend"):
            qc.server(data_source=pl.DataFrame({"id": [1]}), table_name="other")

        (session_source,) = created
        with pytest.raises(duckdb.ConnectionException):
            session_source.execute_query("SELECT 1")
        assert qc.table_names() == ["users"]
        assert sessions[0]._ended_callbacks == []

        qc.server()
        assert calls[-1]["table_set"].table_names == ["users"]

    def test_client_resolution_failure_still_cleans_up_session_source(
        self, users_df, session_runs, monkeypatch
    ):
        """
        A `.server(client=...)` override that fails to resolve must not leak
        the session's own normalized data source: on_ended cleanup must already
        be registered by the time client resolution can raise.
        """
        import duckdb

        sessions, _calls = session_runs
        qc = shiny_mod.QueryChat(None, table_name="users")
        created = []
        real_normalize = shiny_mod.normalize_data_source

        def spy(data_source, table_name):
            source = real_normalize(data_source, table_name)
            created.append(source)
            return source

        monkeypatch.setattr(shiny_mod, "normalize_data_source", spy)

        with pytest.raises(ValueError, match="not a known chatlas provider"):
            qc.server(data_source=users_df, client="not-a-real-provider")

        (session_source,) = created
        assert sessions[0]._ended_callbacks != []

        sessions[0].end()
        with pytest.raises(duckdb.ConnectionException):
            session_source.execute_query("SELECT 1")
